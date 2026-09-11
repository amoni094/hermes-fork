"""Per-turn adaptive reasoning-effort override (floor-respecting, one-shot)."""

from types import SimpleNamespace

from agent.chat_completion_helpers import _reasoning_config_for_wire
from agent.reasoning_effort import EFFORT_LADDER


def _agent(cfg, **attrs):
    agent = SimpleNamespace(reasoning_config=cfg)
    for key, value in attrs.items():
        setattr(agent, key, value)
    return agent


def test_adaptive_effort_below_floor_is_clamped():
    agent = _agent({"enabled": True, "effort": "high"}, _adaptive_effort_override="low")
    cfg = _reasoning_config_for_wire(agent)
    assert cfg["effort"] == "high"


def test_adaptive_effort_above_floor_applies():
    agent = _agent({"enabled": True, "effort": "low"}, _adaptive_effort_override="high")
    cfg = _reasoning_config_for_wire(agent)
    assert cfg["effort"] == "high"


def test_adaptive_effort_skipped_when_disabled():
    agent = _agent({"enabled": False, "effort": "low"}, _adaptive_effort_override="high")
    cfg = _reasoning_config_for_wire(agent)
    assert cfg == {"enabled": False, "effort": "low"}
    assert agent._adaptive_effort_override is None

    agent = _agent({"enabled": True, "effort": "none"}, _adaptive_effort_override="high")
    cfg = _reasoning_config_for_wire(agent)
    assert cfg["effort"] == "none"


def test_adaptive_effort_cleared_after_wire():
    agent = _agent({"enabled": True, "effort": "low"}, _adaptive_effort_override="high")
    _reasoning_config_for_wire(agent)
    assert agent._adaptive_effort_override is None


def test_adaptive_effort_skipped_when_none():
    agent = _agent({"enabled": True, "effort": "medium"})
    cfg = _reasoning_config_for_wire(agent)
    assert cfg == {"enabled": True, "effort": "medium"}


def test_effort_ladder_ordering():
    assert EFFORT_LADDER.index("low") < EFFORT_LADDER.index("medium") < EFFORT_LADDER.index("high")
    agent = _agent({"enabled": True, "effort": "medium"}, _adaptive_effort_override="low")
    assert _reasoning_config_for_wire(agent)["effort"] == "medium"
    agent = _agent({"enabled": True, "effort": "medium"}, _adaptive_effort_override="high")
    assert _reasoning_config_for_wire(agent)["effort"] == "high"
    agent = _agent({"enabled": True, "effort": "medium"}, _adaptive_effort_override="medium")
    assert _reasoning_config_for_wire(agent)["effort"] == "medium"


def test_adaptive_does_not_disturb_ephemeral_off():
    agent = _agent(
        {"enabled": True, "effort": "high"},
        _ephemeral_reasoning_off=True,
        _adaptive_effort_override="max",
    )
    cfg = _reasoning_config_for_wire(agent)
    assert cfg == {"enabled": False, "effort": "none"}
    assert agent._adaptive_effort_override is None
    assert agent._ephemeral_reasoning_off is False


def test_apply_adaptive_effort_none_agent_is_safe():
    from hermes_cli.plugins import apply_adaptive_effort_to_agent

    ctx = SimpleNamespace(_adaptive_effort="high", _reasoning_resolver=None)
    apply_adaptive_effort_to_agent(ctx, None)


def test_apply_adaptive_effort_respects_floor_and_disable():
    from hermes_cli.plugins import apply_adaptive_effort_to_agent

    ctx = SimpleNamespace(_adaptive_effort="low", _reasoning_resolver=None)
    agent = _agent({"enabled": True, "effort": "high"})
    apply_adaptive_effort_to_agent(ctx, agent)
    assert agent._adaptive_effort_override == "high"

    ctx = SimpleNamespace(_adaptive_effort="high", _reasoning_resolver=None)
    agent = _agent({"enabled": True, "effort": "low"})
    apply_adaptive_effort_to_agent(ctx, agent)
    assert agent._adaptive_effort_override == "high"

    ctx = SimpleNamespace(_adaptive_effort="high", _reasoning_resolver=None)
    agent = _agent({"enabled": False, "effort": "low"})
    apply_adaptive_effort_to_agent(ctx, agent)
    assert getattr(agent, "_adaptive_effort_override", None) is None


def test_plugin_context_set_get_adaptive_effort():
    from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest

    ctx = PluginContext(PluginManifest(name="demo", key="demo", source="user"), PluginManager())
    assert ctx.get_adaptive_effort() is None
    ctx.set_adaptive_effort("high")
    assert ctx.get_adaptive_effort() == "high"
    ctx.set_adaptive_effort("ultra")
    assert ctx.get_adaptive_effort() == "high"
    ctx.set_adaptive_effort("not-a-level")
    assert ctx.get_adaptive_effort() == "high"
