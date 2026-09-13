"""Turn-complexity → adaptive reasoning effort (lambda-tuner pre_llm_call)."""
from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from plugins.plugin_loader import load_plugin_module

PLUGIN_DIR = Path(__file__).resolve().parents[2] / "plugins" / "user" / "lambda-tuner"


def _load_plugin():
    return load_plugin_module(
        "user.lambda_tuner",
        PLUGIN_DIR,
        parents=(),
        logger=logging.getLogger("test-lambda-effort"),
        synthetic_namespace="user",
    )


class _FakeCtx:
    def __init__(self) -> None:
        self.hooks: dict[str, list] = {}
        self.efforts: list[str] = []
        self.modes: list[str] = []
        self._session_id = None
        self._manager = SimpleNamespace(_hooks={}, _agent=None)

    def register_hook(self, name, fn):
        self.hooks.setdefault(name, []).append(fn)
        self._manager._hooks.setdefault(name, []).append(fn)

    def set_adaptive_effort(self, effort):
        self.efforts.append(effort)
        self._recommended_effort = effort

    def set_reasoning_mode(self, mode):
        self.modes.append(mode)

    def emit_episode(self, *args, **kwargs):
        return None

    def suggest_skill_update(self, *args, **kwargs):
        return None

    def get_skill_suggestions(self):
        return []


@pytest.fixture
def plugin():
    mod = _load_plugin()
    assert mod is not None
    for bucket in (
        getattr(mod, "_fired", None),
        getattr(mod, "_session_messages", None),
        getattr(mod, "_intent_applied", None),
        getattr(mod, "_complexity_buffers", None),
    ):
        if bucket is not None:
            bucket.clear()
    yield mod
    for bucket in (
        getattr(mod, "_fired", None),
        getattr(mod, "_session_messages", None),
        getattr(mod, "_intent_applied", None),
        getattr(mod, "_complexity_buffers", None),
    ):
        if bucket is not None:
            bucket.clear()


def _register(plugin) -> tuple[_FakeCtx, object]:
    ctx = _FakeCtx()
    plugin.register(ctx)
    hook = ctx.hooks["pre_llm_call"][0]
    return ctx, hook


def test_greeter_maps_to_low(plugin, monkeypatch):
    monkeypatch.setattr(plugin.DEFAULT_SCORER, "score", lambda text: 0.9)
    ctx, hook = _register(plugin)
    hook(session_id="greet-1", user_message="thanks")
    assert ctx.efforts[-1] == "low"
    assert plugin.predicates.is_greeter_turn("thanks")
    assert plugin.predicates.is_greeter_turn("go ahead")
    assert not plugin.predicates.is_greeter_turn("implement the parser")


def test_high_complexity_maps_to_xhigh_research(plugin, monkeypatch):
    monkeypatch.setattr(plugin.DEFAULT_SCORER, "score", lambda text: 0.62)
    ctx, hook = _register(plugin)
    hook(
        session_id="research-1",
        user_message="find papers on arxiv about literature review of transformers",
    )
    assert ctx.efforts[-1] == "xhigh"


def test_ema_smoothing_prevents_thrash(plugin, monkeypatch):
    def fake_score(text: str) -> float:
        return 0.05 if "SPIKE" in text else 0.65

    monkeypatch.setattr(plugin.DEFAULT_SCORER, "score", fake_score)
    ctx, hook = _register(plugin)
    sid = "ema-1"
    hook(session_id=sid, user_message="please analyze this multi-step constraint then continue")
    hook(session_id=sid, user_message="next please compare both approaches then summarize")
    assert ctx.efforts[-1] == "high"
    hook(session_id=sid, user_message="SPIKE down to a short note")
    assert ctx.efforts[-1] == "medium"


def test_code_session_no_bias(plugin, monkeypatch):
    monkeypatch.setattr(plugin.DEFAULT_SCORER, "score", lambda text: 0.62)
    ctx, hook = _register(plugin)
    hook(session_id="code-1", user_message="fix the bug in the failing test")
    assert ctx.efforts[-1] == "high"


def test_predicates_turn_complexity_score(plugin, monkeypatch):
    monkeypatch.setattr(plugin.DEFAULT_SCORER, "score", lambda text: 0.42)
    ctx, hook = _register(plugin)
    hook(session_id="pred-1", user_message="what is the capital of France?")
    assert plugin.predicates.turn_complexity_score(ctx) == pytest.approx(0.42)
    assert plugin.predicates.recommended_effort(ctx) == "medium"


class _FakeCompressor:
    """Named profiles reset knobs; dict overlays must be reapplied after that."""

    def __init__(self) -> None:
        self.protect_last_n = 20
        self.proactive_prune_tokens = 0
        self.applied: list = []
        self._last_ratio = None
        self._last_complexity_score = None
        self.last_compression_ratio = None
        self.last_complexity_score = None

    def set_compression_profile(self, profile, **kwargs):
        self.applied.append(profile)
        if profile == "code":
            self.protect_last_n = 28
            self.proactive_prune_tokens = 28_000
        elif profile == "research":
            self.protect_last_n = 22
            self.proactive_prune_tokens = 40_000
        elif profile == "mixed":
            self.protect_last_n = 20
            self.proactive_prune_tokens = 32_000
        elif isinstance(profile, dict):
            if "protect_last_n" in profile:
                self.protect_last_n = int(profile["protect_last_n"])
            if "proactive_prune_tokens" in profile:
                self.proactive_prune_tokens = int(profile["proactive_prune_tokens"])


def test_high_complexity_overlay_survives_next_turn(plugin, monkeypatch):
    """Counterfactual: without overlay reapply, turn 2 resets protect_last_n to 28."""
    monkeypatch.setattr(plugin.DEFAULT_SCORER, "score", lambda text: 0.85)
    ctx, hook = _register(plugin)
    compressor = _FakeCompressor()
    agent = SimpleNamespace(context_compressor=compressor)
    hook(
        session_id="ov-1",
        user_message="fix the bug in the failing test then implement the parser",
        agent=agent,
    )
    assert compressor.protect_last_n == min(28 + 5, 40)
    hook(
        session_id="ov-1",
        user_message="write a new function for the handler",
        agent=agent,
    )
    assert compressor.protect_last_n == min(28 + 5, 40)


def test_disabled_prune_stays_disabled_on_low_complexity(plugin, monkeypatch):
    """Totality: prune_tokens=0 must not be turned on by the low-complexity overlay."""
    monkeypatch.setattr(plugin.DEFAULT_SCORER, "score", lambda text: 0.1)

    class _NoProfileCompressor(_FakeCompressor):
        def set_compression_profile(self, profile, **kwargs):
            self.applied.append(profile)
            if isinstance(profile, dict) and "proactive_prune_tokens" in profile:
                self.proactive_prune_tokens = int(profile["proactive_prune_tokens"])

    ctx, hook = _register(plugin)
    compressor = _NoProfileCompressor()
    compressor.proactive_prune_tokens = 0
    agent = SimpleNamespace(context_compressor=compressor)
    hook(
        session_id="prune-0",
        user_message="fix the bug in the failing test",
        agent=agent,
    )
    assert compressor.proactive_prune_tokens == 0
