"""Conflict resolution for multi-plugin reasoning-effort recommendations."""

from __future__ import annotations

from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest
from hermes_cli.reasoning_resolver import ReasoningConflictResolver


def _ctx(name: str = "demo", manager: PluginManager | None = None) -> PluginContext:
    mgr = manager or PluginManager()
    return PluginContext(PluginManifest(name=name, key=name, source="user"), mgr)


def test_highest_priority_wins():
    r = ReasoningConflictResolver()
    r.add_recommendation("other", "high", confidence=1.0, priority=0)
    r.add_recommendation("lambda-tuner", "low", confidence=1.0, priority=10)
    assert r.resolve("low") == "low"


def test_tie_broken_by_highest_effort():
    r = ReasoningConflictResolver()
    r.add_recommendation("a", "low", confidence=0.9, priority=5)
    r.add_recommendation("b", "high", confidence=0.9, priority=5)
    assert r.resolve("low") == "high"


def test_low_confidence_filtered():
    r = ReasoningConflictResolver()
    r.add_recommendation("noisy", "high", confidence=0.49, priority=10)
    r.add_recommendation("steady", "medium", confidence=0.5, priority=0)
    assert r.resolve("low") == "medium"


def test_floor_respected():
    r = ReasoningConflictResolver()
    r.add_recommendation("plugin", "low", confidence=1.0, priority=10)
    assert r.resolve("medium") == "medium"
    assert r.resolve("high") == "high"


def test_clear_resets_state():
    r = ReasoningConflictResolver()
    r.add_recommendation("plugin", "high", confidence=1.0, priority=10)
    assert r.resolve("low") == "high"
    r.clear()
    assert r.resolve("low") == "low"
    assert r.recommendation_log() == []


def test_mode_to_effort_bridge():
    ctx = _ctx("mode-plugin")
    ctx.set_reasoning_mode("fast")
    ctx.set_reasoning_mode("deep")
    log = ctx.get_reasoning_recommendation_log()
    efforts = [row["effort"] for row in log]
    assert "low" in efforts
    assert "high" in efforts
    assert all(row["priority"] == 5 for row in log)
    assert all(row["confidence"] == 0.7 for row in log)
    assert ctx.apply_adaptive_effort_to_agent(configured_floor="low") == "high"


def test_recommendation_log():
    ctx = _ctx("winner")
    other = _ctx("loser", manager=ctx._manager)
    ctx.set_adaptive_effort("medium", confidence=1.0, priority=10)
    other.set_adaptive_effort("high", confidence=1.0, priority=0)
    winner = ctx.apply_adaptive_effort_to_agent(configured_floor="low")
    assert winner == "medium"
    log = ctx.get_reasoning_recommendation_log()
    assert {row["plugin"] for row in log} == {"winner", "loser"}
    won = [row for row in log if row["won"]]
    lost = [row for row in log if not row["won"]]
    assert len(won) == 1
    assert won[0]["plugin"] == "winner"
    assert won[0]["effort"] == "medium"
    assert len(lost) == 1
    assert lost[0]["plugin"] == "loser"
