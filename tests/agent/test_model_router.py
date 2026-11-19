"""Hermetic tests for smart model routing (any configured provider)."""

import types

from agent import model_router
from agent.model_router import RoutingDecision


def _cfg(**routing):
    base = {
        "enabled": True,
        "default_tier": "standard",
        "tiers": {
            "light": "gpt-4o-mini",
            "standard": "",
            "heavy": {"model": "claude-opus-4-6", "provider": "anthropic"},
        },
    }
    base.update(routing)
    return {"smart_model_routing": base}


def test_is_enabled_default_off():
    assert model_router.is_enabled({}) is False
    assert model_router.is_enabled(_cfg(enabled=False)) is False
    assert model_router.is_enabled(_cfg()) is True


def test_no_nous_only_gate():
    assert not hasattr(model_router, "_is_nous_provider")
    assert not hasattr(model_router, "NOUS_PROVIDER")


def test_tier_target_string_and_dict():
    cfg = _cfg()
    assert model_router._tier_target("light", cfg) == ("gpt-4o-mini", "")
    assert model_router._tier_target("standard", cfg) == ("", "")
    assert model_router._tier_target("heavy", cfg) == ("claude-opus-4-6", "anthropic")
    assert model_router._tier_target("nope", cfg) == ("", "")


def test_route_disabled_is_noop():
    assert model_router.route(
        "anything", current_model="gpt-4o", current_provider="openai", config=_cfg(enabled=False),
    ) is None


def test_route_works_for_non_nous_provider(monkeypatch):
    monkeypatch.setattr(model_router, "classify_complexity", lambda *a, **k: "heavy")
    monkeypatch.setattr(
        model_router, "_resolve_tier_credentials",
        lambda model, provider: {"provider": provider, "api_key": "sk", "base_url": "https://api.anthropic.com", "api_mode": "anthropic_messages"},
    )
    decision = model_router.route(
        "hard refactor", current_model="gpt-4o", current_provider="openai", config=_cfg(),
    )
    assert isinstance(decision, RoutingDecision)
    assert decision.tier == "heavy"
    assert decision.model == "claude-opus-4-6"
    assert decision.provider == "anthropic"


def test_route_empty_tier_stays(monkeypatch):
    monkeypatch.setattr(model_router, "classify_complexity", lambda *a, **k: "standard")
    assert model_router.route(
        "normal task", current_model="gpt-4o", current_provider="openai", config=_cfg(),
    ) is None


def test_route_noop_when_tier_matches_current(monkeypatch):
    monkeypatch.setattr(model_router, "classify_complexity", lambda *a, **k: "light")
    assert model_router.route(
        "tiny edit", current_model="gpt-4o-mini", current_provider="openai", config=_cfg(),
    ) is None


def test_route_resolves_against_current_provider_when_tier_omits_it(monkeypatch):
    captured = {}

    def _fake_resolve(model, provider):
        captured["model"] = model
        captured["provider"] = provider
        return {"provider": provider, "api_key": "sk", "base_url": "https://api.openai.com/v1", "api_mode": ""}

    monkeypatch.setattr(model_router, "classify_complexity", lambda *a, **k: "light")
    monkeypatch.setattr(model_router, "_resolve_tier_credentials", _fake_resolve)
    decision = model_router.route(
        "tiny edit", current_model="gpt-4o", current_provider="openai", config=_cfg(),
    )
    assert decision is not None
    assert captured["provider"] == "openai"
    assert captured["model"] == "gpt-4o-mini"


def test_route_fails_open_when_credentials_unresolved(monkeypatch):
    monkeypatch.setattr(model_router, "classify_complexity", lambda *a, **k: "light")
    monkeypatch.setattr(model_router, "_resolve_tier_credentials", lambda *a, **k: None)
    assert model_router.route(
        "tiny edit", current_model="gpt-4o", current_provider="openai", config=_cfg(),
    ) is None


def test_classify_empty_message_returns_none():
    assert model_router.classify_complexity("   ") is None


def test_classify_fails_open_without_aux_client(monkeypatch):
    import agent.auxiliary_client as aux
    monkeypatch.setattr(aux, "get_text_auxiliary_client", lambda *a, **k: (None, None))
    assert model_router.classify_complexity("do something") is None


class _FakeAgent:
    def __init__(self):
        self.model = "gpt-4o"
        self.provider = "openai"
        self.quiet_mode = True
        self.switched = None

    def switch_model(self, **kwargs):
        self.switched = kwargs
        self.model = kwargs["new_model"]
        self.provider = kwargs["new_provider"]


def test_session_routing_skips_resumed_session():
    from agent import conversation_loop
    agent = _FakeAgent()
    conversation_loop._maybe_apply_session_routing(agent, "hi", [{"role": "user", "content": "x"}])
    assert agent.switched is None


def test_session_routing_switches(monkeypatch):
    from agent import conversation_loop
    agent = _FakeAgent()
    monkeypatch.setattr(
        model_router, "route",
        lambda *a, **k: RoutingDecision(
            tier="heavy", model="claude-opus-4-6", provider="anthropic",
            api_key="sk", base_url="https://api.anthropic.com", api_mode="anthropic_messages",
        ),
    )
    conversation_loop._maybe_apply_session_routing(agent, "hard task", None)
    assert agent.switched is not None
    assert agent.model == "claude-opus-4-6"
    assert agent.provider == "anthropic"
    # Verify every kwarg is forwarded to switch_model
    assert agent.switched == {
        "new_model": "claude-opus-4-6",
        "new_provider": "anthropic",
        "api_key": "sk",
        "base_url": "https://api.anthropic.com",
        "api_mode": "anthropic_messages",
    }


def test_session_routing_empty_history_is_first_turn(monkeypatch):
    """[] is a new session — routing should fire."""
    from agent import conversation_loop
    agent = _FakeAgent()
    monkeypatch.setattr(
        model_router, "route",
        lambda *a, **k: RoutingDecision(
            tier="light", model="gpt-4o-mini", provider="openai",
            api_key="sk", base_url="", api_mode="",
        ),
    )
    conversation_loop._maybe_apply_session_routing(agent, "quick lookup", [])
    assert agent.model == "gpt-4o-mini"


def test_session_routing_classifier_none_stays_put(monkeypatch):
    """When route() returns None the agent model must not change."""
    from agent import conversation_loop
    agent = _FakeAgent()
    monkeypatch.setattr(model_router, "route", lambda *a, **k: None)
    conversation_loop._maybe_apply_session_routing(agent, "some message", None)
    assert agent.switched is None
    assert agent.model == "gpt-4o"


def test_delegation_routing_respects_explicit_model():
    from tools import delegate_tool
    base = {"model": "pinned/model", "provider": "openai", "base_url": None, "api_key": None, "api_mode": None}
    parent = types.SimpleNamespace(model="gpt-4o", provider="openai")
    result = delegate_tool._route_task_creds(base, "anything", parent)
    assert result == base
    assert result is not base  # always returns a copy


def test_delegation_routing_sets_model_when_unpinned(monkeypatch):
    from tools import delegate_tool
    monkeypatch.setattr(
        model_router, "route",
        lambda *a, **k: RoutingDecision(
            tier="light", model="gpt-4o-mini", provider="openai",
            api_key="sk", base_url="https://api.openai.com/v1", api_mode="",
        ),
    )
    base = {"model": None, "provider": None, "base_url": None, "api_key": None, "api_mode": None}
    parent = types.SimpleNamespace(model="gpt-4o", provider="openai")
    out = delegate_tool._route_task_creds(base, "tiny task", parent)
    assert out["model"] == "gpt-4o-mini"
    assert out["provider"] == "openai"


def test_delegation_routing_noop_returns_base(monkeypatch):
    from tools import delegate_tool
    monkeypatch.setattr(model_router, "route", lambda *a, **k: None)
    base = {"model": None, "provider": None, "base_url": None, "api_key": None, "api_mode": None}
    parent = types.SimpleNamespace(model="gpt-4o", provider="openai")
    result = delegate_tool._route_task_creds(base, "task", parent)
    assert result == base
    assert result is not base  # always returns a copy


def test_defaults_off_with_classifier_slot():
    from hermes_cli.config_defaults import DEFAULT_CONFIG
    sm = DEFAULT_CONFIG["smart_model_routing"]
    assert sm["enabled"] is False
    assert set(sm["tiers"]) == {"light", "standard", "heavy"}
    assert DEFAULT_CONFIG["auxiliary"]["routing_classifier"]["timeout"] == 15
