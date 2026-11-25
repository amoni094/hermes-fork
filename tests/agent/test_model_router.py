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
        self.user_config = {}
        self._last_routing_tier = None
        self._last_turn_routing_error = False
        self.ephemeral_system_prompt = None

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
    assert sm["classifier"] == "llm"
    assert sm["per_turn"] is False
    assert set(sm["tiers"]) == {"light", "standard", "heavy"}
    assert DEFAULT_CONFIG["auxiliary"]["routing_classifier"]["timeout"] == 15


def test_applies_this_turn():
    assert model_router.applies_this_turn(None) is True
    assert model_router.applies_this_turn([]) is True
    assert model_router.applies_this_turn([{"role": "user"}]) is False
    assert model_router.applies_this_turn(
        [{"role": "user"}], {"smart_model_routing": {"per_turn": True}}
    ) is True
    assert model_router.applies_this_turn(
        [{"role": "user"}], {"smart_model_routing": {"classifier": "rules"}}
    ) is True
    assert model_router.applies_this_turn(
        [{"role": "user"}], {"smart_model_routing": {"classifier": "llm"}}
    ) is False


def test_rules_classifier_mode(monkeypatch):
    monkeypatch.setattr(model_router, "_classify_rules", lambda text, *a, **k: "fast")
    assert model_router.classify_complexity("restart vpn", _cfg(classifier="rules")) == "fast"


def test_llm_mode_skips_rules(monkeypatch):
    called = []
    monkeypatch.setattr(model_router, "_classify_rules", lambda text, *a, **k: called.append(text) or "fast")
    import agent.auxiliary_client as aux
    monkeypatch.setattr(aux, "get_text_auxiliary_client", lambda *a, **k: (None, None))
    assert model_router.classify_complexity("do something", _cfg()) is None
    assert called == []


def test_low_confidence_rules_escalates_to_reason(monkeypatch):
    class _Mod:
        def classify(self, payload):
            return {"tier": "fast", "confidence": 0.4, "reason": "x"}
    monkeypatch.setattr(model_router, "_load_rules_classifier", lambda: _Mod())
    assert model_router._classify_rules("x") == "reason"


def test_fast_falls_back_to_light_target():
    assert model_router._tier_target("fast", _cfg()) == ("gpt-4o-mini", "")


def test_session_routing_per_turn_fires_on_history(monkeypatch):
    from agent import conversation_loop
    agent = _FakeAgent()
    agent.user_config = {"smart_model_routing": {"per_turn": True}}
    monkeypatch.setattr(
        model_router, "route",
        lambda *a, **k: RoutingDecision(
            tier="light", model="gpt-4o-mini", provider="openai",
            api_key="sk", base_url="https://api.openai.com/v1", api_mode="",
        ),
    )
    conversation_loop._maybe_apply_session_routing(
        agent, "hi", [{"role": "user", "content": "x"}]
    )
    assert agent.model == "gpt-4o-mini"


def test_classify_rules_passes_turn_index_and_prior_tier(monkeypatch):
    seen = {}

    class _Mod:
        def classify(self, payload):
            seen.update(payload)
            return {"tier": "fast", "confidence": 0.9, "reason": "x"}

    monkeypatch.setattr(model_router, "_load_rules_classifier", lambda: _Mod())
    assert model_router._classify_rules("ok", turn_index=2, prior_tier="fast") == "fast"
    assert seen["turn_index"] == 2
    assert seen["prior_tier"] == "fast"


def test_classify_rules_first_turn_drops_prior_tier(monkeypatch):
    seen = {}

    class _Mod:
        def classify(self, payload):
            seen.update(payload)
            return {"tier": "reason", "confidence": 0.9, "reason": "x"}

    monkeypatch.setattr(model_router, "_load_rules_classifier", lambda: _Mod())
    assert model_router._classify_rules("ok", turn_index=0, prior_tier="fast") == "reason"
    assert seen["turn_index"] == 0
    assert seen["prior_tier"] is None


def test_session_routing_passes_turn_index_and_prior_tier(monkeypatch):
    from agent import conversation_loop
    captured = {}

    def fake_route(*a, **k):
        captured.update(k)

    agent = _FakeAgent()
    agent._last_routing_tier = "fast"
    agent.user_config = {"smart_model_routing": {"per_turn": True}}
    monkeypatch.setattr(model_router, "route", fake_route)
    conversation_loop._maybe_apply_session_routing(
        agent,
        "what about the other one",
        [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}],
    )
    assert captured["turn_index"] == 1
    assert captured["prior_tier"] == "fast"


def test_session_routing_error_turn_clears_prior_tier(monkeypatch):
    from agent import conversation_loop
    captured = {}

    def fake_route(*a, **k):
        captured.update(k)

    agent = _FakeAgent()
    agent._last_routing_tier = "fast"
    agent._last_turn_routing_error = True
    agent.user_config = {"smart_model_routing": {"per_turn": True}}
    monkeypatch.setattr(model_router, "route", fake_route)
    conversation_loop._maybe_apply_session_routing(
        agent, "try again", [{"role": "user", "content": "x"}]
    )
    assert captured["turn_index"] == 1
    assert captured["prior_tier"] is None


def test_clear_routing_tier_on_error():
    from agent import conversation_loop
    agent = _FakeAgent()
    agent._last_routing_tier = "fast"
    conversation_loop._clear_routing_tier_on_error(agent, {"error": "boom", "completed": False})
    assert agent._last_routing_tier is None
    assert agent._last_turn_routing_error is True


def test_note_escalated_tier_overwrites_prior():
    agent = _FakeAgent()
    agent._last_routing_tier = "fast"
    model_router.note_escalated_tier(agent, "reason")
    assert agent._last_routing_tier == "reason"


def test_routing_turn_index_counts_user_messages():
    from agent import conversation_loop
    assert conversation_loop._routing_turn_index(None) == 0
    assert conversation_loop._routing_turn_index([]) == 0
    assert conversation_loop._routing_turn_index([{"role": "user", "content": "a"}]) == 1
    assert conversation_loop._routing_turn_index([
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
    ]) == 2


def test_reason_deep_trajectory():
    from agent.reason_depth import needs_deep_reason
    depth, reason = needs_deep_reason(
        "fix this bug", turn_index=3, consecutive_reason_turns=2,
    )
    assert depth == "elite" and "trajectory" in reason


def test_reason_followup_does_not_elite_can():
    """Short 'can you' follow-up should NOT promote to elite even at consecutive>=2."""
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason(
        "can she open pdf files?",
        consecutive_reason_turns=3,
    )
    assert depth != "elite"


def test_reason_followup_does_not_elite_also():
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason(
        "also what about the caching layer?",
        consecutive_reason_turns=2,
    )
    assert depth != "elite"


def test_reason_followup_does_not_elite_is_there():
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason(
        "is there another free pdf app instead of edge?",
        consecutive_reason_turns=2,
    )
    assert depth != "elite"


def test_reason_followup_long_query_still_elites():
    """A query that starts with 'can' but is >12 words IS substantive -> elite."""
    from agent.reason_depth import needs_deep_reason
    depth, reason = needs_deep_reason(
        "can you explain how the memory consolidation and retrieval pipeline "
        "interacts with the graphiti knowledge graph during compaction?",
        consecutive_reason_turns=2,
    )
    assert depth == "elite" and "trajectory" in reason


def test_reason_followup_what_about_short():
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason(
        "what about the wifi password?",
        consecutive_reason_turns=2,
    )
    assert depth != "elite"


def test_reason_rename_always_deep():
    """rename + code object is always cross-file — no word-count gate."""
    from agent.reason_depth import needs_deep_reason
    depth, reason = needs_deep_reason("rename all references to X in the plugin")
    assert depth == "deep" and "refactor" in reason


def test_reason_rename_short_also_deep():
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason("rename the config key")
    assert depth == "deep"


def test_reason_rename_non_code_not_deep():
    """rename without a code object should NOT go deep."""
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason("rename your tone")
    assert depth == "simple"


def test_reason_rename_non_code_output_not_deep():
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason("rename your output format")
    assert depth == "simple"


def test_reason_audit_analytical():
    """audit keyword -> analytical at >5 words (short gate, not >15)."""
    from agent.reason_depth import needs_deep_reason
    depth, reason = needs_deep_reason(
        "audit the AppArmor profile for firefox",
    )
    assert depth == "analytical" and "analytical" in reason


def test_reason_harden_short_analytical():
    """harden at >=5 words fires analytical."""
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason("harden the firefox sandbox profile")
    assert depth == "analytical"


def test_reason_audit_long_analytical():
    """Long audit query also hits analytical."""
    from agent.reason_depth import needs_deep_reason
    depth, reason = needs_deep_reason(
        "audit the AppArmor profile for firefox and check for over-permissions "
        "that might allow filesystem access outside the browser sandbox",
    )
    assert depth == "analytical" and "analytical" in reason


def test_reason_tier_inherit_elite():
    """'y' with prior_tier=elite inherits elite."""
    from agent.reason_depth import needs_deep_reason
    depth, reason = needs_deep_reason("y", prior_tier="elite")
    assert depth == "elite" and "inherit" in reason


def test_reason_tier_inherit_deep():
    from agent.reason_depth import needs_deep_reason
    depth, reason = needs_deep_reason("do it", prior_tier="deep")
    assert depth == "deep" and "inherit" in reason


def test_reason_tier_inherit_do_all():
    from agent.reason_depth import needs_deep_reason
    depth, reason = needs_deep_reason("do all", prior_tier="analytical")
    assert depth == "analytical" and "inherit" in reason


def test_reason_tier_inherit_do_n():
    from agent.reason_depth import needs_deep_reason
    depth, reason = needs_deep_reason("do 3", prior_tier="elite")
    assert depth == "elite" and "inherit" in reason


def test_reason_tier_inherit_no_prior():
    """Without prior_tier, 'y' falls through to simple (not elite)."""
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason("y")
    assert depth == "simple"


def test_reason_bare_ack_no_prior_consecutive():
    """'y' with consecutive_reason_turns=2 but no prior_tier must NOT hit elite."""
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason("y", consecutive_reason_turns=2)
    assert depth == "simple"


def test_reason_tier_inherit_long_query_no_inherit():
    """A substantive query starting with 'yes' should NOT inherit."""
    from agent.reason_depth import needs_deep_reason
    _depth, _reason = needs_deep_reason(
        "yes but also make sure it handles the edge case where the config file is missing",
        prior_tier="elite",
    )
    # > 4 words, should not inherit — route on content
    assert "inherit" not in _reason


def test_reason_followup_just_short_suppressed():
    """'just' at <=5 words suppresses elite via tight cap."""
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason("just do it now", consecutive_reason_turns=2)
    assert depth != "elite"


def test_reason_followup_just_long_not_suppressed():
    """'just rewrite the entire auth module' (6w) > tight cap -> should elite."""
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason(
        "just rewrite the entire auth module", consecutive_reason_turns=2
    )
    assert depth == "elite"


def test_reason_followup_and_short_suppressed():
    """'and do it' at <=5 words is a tight-cap follow-up."""
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason("and do it", consecutive_reason_turns=2)
    assert depth != "elite"


def test_reason_followup_and_long_not_suppressed():
    """'and implement the full OAuth2 flow with PKCE' (8w) > tight cap -> elite."""
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason(
        "and implement the full OAuth2 flow with PKCE", consecutive_reason_turns=2
    )
    assert depth == "elite"


def test_reason_ack_punctuated_inherits():
    """'right?' and 'ok?' with punctuation should inherit prior tier."""
    from agent.reason_depth import needs_deep_reason
    for ack in ("right?", "ok?", "yes!", "lgtm."):
        depth, reason = needs_deep_reason(ack, prior_tier="elite")
        assert depth == "elite" and "inherit" in reason, f"Failed for {ack!r}"


def test_reason_ack_do_n_capped():
    """'do 99' (>2 digits) should NOT inherit (digit cap at 1-2)."""
    from agent.reason_depth import needs_deep_reason
    _depth, _reason = needs_deep_reason("do 999", prior_tier="elite")
    # digit cap: \d{1,2} only, so 'do 999' falls through to normal routing
    assert "inherit" not in _reason


def test_reason_deep_multi_constraint():
    from agent.reason_depth import needs_deep_reason
    depth, reason = needs_deep_reason(
        "reconcile the config and state files without breaking the existing tests",
    )
    assert depth == "deep" and "constraint" in reason


def test_reason_simple_factual():
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason("is memory working as it should be?", turn_index=0)
    assert depth == "simple"


def test_reason_simple_short_continuation():
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason(
        "is it synced with local?",
        turn_index=1,
        prior_tier="reason",
        consecutive_reason_turns=1,
    )
    assert depth == "simple"


def test_reason_deep_complex_refactor():
    from agent.reason_depth import needs_deep_reason
    depth, _reason = needs_deep_reason(
        "refactor the entire authentication module to use the new session manager "
        "while keeping backward compatibility with existing tests",
        turn_index=0,
    )
    assert depth == "deep"


def _reason_split_cfg():
    return {
        "smart_model_routing": {
            "enabled": True,
            "classifier": "llm",
            "tiers": {
                "reason": {"model": "gpt-5.5", "provider": "openai"},
                "fast": {"model": "gpt-4o-mini", "provider": "openai"},
            },
            "reason_model": "deepseek/deepseek-v4-pro",
            "reason_deep_model": "openai/gpt-5.5",
            "reason_elite_model": "anthropic/claude-sonnet-5-5",
        }
    }


def _fake_creds(model, provider):
    return {
        "provider": provider,
        "api_key": "sk-test",
        "base_url": "https://example.invalid",
        "api_mode": "chat_completions",
    }


def test_route_reason_simple_uses_reason_model(monkeypatch):
    monkeypatch.setattr(model_router, "classify_complexity", lambda *a, **k: "reason")
    monkeypatch.setattr(model_router, "_resolve_tier_credentials", _fake_creds)
    d = model_router.route(
        "is memory working as it should be?",
        current_model="gpt-4o-mini",
        current_provider="openai",
        config=_reason_split_cfg(),
    )
    assert d is not None
    assert d.model == "deepseek-v4-pro"
    assert d.provider == "deepseek"
    assert model_router.LAST_RULES_DETAIL.get("reason_depth") == "simple"


def test_route_reason_deep_uses_gpt55(monkeypatch):
    monkeypatch.setattr(model_router, "classify_complexity", lambda *a, **k: "reason")
    monkeypatch.setattr(model_router, "_resolve_tier_credentials", _fake_creds)
    d = model_router.route(
        "reconcile the config and state files without breaking the existing tests",
        current_model="gpt-4o-mini",
        current_provider="openai",
        config=_reason_split_cfg(),
    )
    assert d is not None
    assert d.model == "gpt-5.5"
    assert d.provider == "openai"
    assert model_router.LAST_RULES_DETAIL.get("reason_depth") == "deep"


def test_route_reason_elite_on_trajectory(monkeypatch):
    monkeypatch.setattr(model_router, "classify_complexity", lambda *a, **k: "reason")
    monkeypatch.setattr(model_router, "_resolve_tier_credentials", _fake_creds)
    d = model_router.route(
        "fix this bug",
        current_model="gpt-4o-mini",
        current_provider="openai",
        config=_reason_split_cfg(),
        consecutive_reason_turns=2,
    )
    assert d is not None
    assert d.model == "claude-sonnet-5-5"
    assert d.provider == "anthropic"
    assert model_router.LAST_RULES_DETAIL.get("reason_depth") == "elite"


def test_route_reason_split_off_without_deep_model(monkeypatch):
    monkeypatch.setattr(model_router, "classify_complexity", lambda *a, **k: "reason")
    monkeypatch.setattr(model_router, "_resolve_tier_credentials", _fake_creds)
    cfg = {
        "smart_model_routing": {
            "enabled": True,
            "classifier": "llm",
            "tiers": {"reason": {"model": "gpt-5.5", "provider": "openai"}},
            "reason_model": "deepseek/deepseek-v4-pro",
        }
    }
    d = model_router.route(
        "reconcile the config and state files without breaking the existing tests",
        current_model="gpt-4o-mini",
        current_provider="openai",
        config=cfg,
    )
    assert d is not None
    assert d.model == "gpt-5.5"
    assert model_router.LAST_RULES_DETAIL.get("reason_depth") is None


def test_note_escalated_tier_sets_consecutive_reason_turns():
    agent = _FakeAgent()
    agent._last_routing_tier = "fast"
    model_router.note_escalated_tier(agent, "reason")
    assert agent._last_routing_tier == "reason"
    assert agent._consecutive_reason_turns == 1


def test_clear_routing_tier_on_error_resets_consecutive():
    from agent import conversation_loop
    agent = _FakeAgent()
    agent._last_routing_tier = "reason"
    agent._consecutive_reason_turns = 3
    conversation_loop._clear_routing_tier_on_error(agent, {"error": "boom", "completed": False})
    assert agent._last_routing_tier is None
    assert agent._consecutive_reason_turns == 0


def test_upgrade_inherited_reason_prior_tier_reason_does_not_elite():
    """upgrade_inherited_reason_model with prior_tier='reason' (the 6-tier name)
    must not activate inherit (because 'reason' is not a depth label).
    With consecutive=2 and query='y', the bare-ack guard should suppress elite.
    """
    agent = _FakeAgent()
    # _last_reason_depth is not set — simulates first turn of a reason sequence
    _model, depth, _ = model_router.upgrade_inherited_reason_model(
        agent,
        query="y",
        config=_reason_split_cfg(),
        consecutive_reason_turns=2,
        prior_tier="reason",
    )
    # 'y' is a bare ACK -> should not elite even with consecutive=2
    assert depth != "elite"


def test_upgrade_inherited_reason_last_depth_elite_inherits():
    """When agent._last_reason_depth='elite', 'y' inherits elite."""
    agent = _FakeAgent()
    agent._last_reason_depth = "elite"  # stored from prior turn
    _model, depth, _ = model_router.upgrade_inherited_reason_model(
        agent,
        query="y",
        config=_reason_split_cfg(),
        consecutive_reason_turns=2,
        prior_tier="reason",  # the old 6-tier name — should be overridden by _last_reason_depth
    )
    assert depth == "elite"


def test_route_reason_analytical_only_config_enables_split(monkeypatch):
    """_reason_split_enabled must return True when only reason_analytical_model is set."""
    monkeypatch.setattr(model_router, "classify_complexity", lambda *a, **k: "reason")
    monkeypatch.setattr(model_router, "_resolve_tier_credentials", _fake_creds)
    cfg = {
        "smart_model_routing": {
            "enabled": True,
            "tiers": {"reason": {"model": "deepseek-v4-pro", "provider": "deepseek"}},
            "reason_model": "deepseek/deepseek-v4-pro",
            "reason_analytical_model": {"model": "grok-4.7", "provider": "xai"},
            # intentionally NO reason_deep_model or reason_elite_model
        }
    }
    d = model_router.route(
        "audit the AppArmor profile for firefox and check for over-permissions",
        current_model="gpt-4o-mini",
        current_provider="openai",
        config=cfg,
    )
    assert d is not None
    assert model_router.LAST_RULES_DETAIL.get("reason_depth") == "analytical"


def test_upgrade_inherited_applies_opus5_strict_prompt(monkeypatch):
    """Live elite turns on opus-5 get the token-strict ephemeral system prompt."""
    monkeypatch.setattr(model_router, "_resolve_tier_credentials", _fake_creds)
    agent = _FakeAgent()
    agent._last_reason_depth = "elite"
    cfg = _reason_split_cfg()
    cfg["smart_model_routing"]["reason_elite_model"] = "anthropic/claude-opus-5"
    _model, depth, _ = model_router.upgrade_inherited_reason_model(
        agent,
        query="y",
        config=cfg,
        consecutive_reason_turns=2,
        prior_tier="reason",
    )
    assert depth == "elite"
    assert "opus-5" in agent.model
    assert agent.ephemeral_system_prompt
    assert "REPLY VALIDATED=OK" in agent.ephemeral_system_prompt
