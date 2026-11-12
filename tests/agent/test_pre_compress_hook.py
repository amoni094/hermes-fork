"""``pre_compress`` fires at compression start; a raising plugin cannot change the attempt."""

import threading

import pytest

from hermes_cli import plugins as plugins_mod
from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest
from tests.agent.test_compaction_events import _Agent, _compressor
from agent.conversation_compression import _begin_compression_attempt
from agent.compaction_events import fire_pre_compress


@pytest.fixture
def ctx(monkeypatch):
    mgr = PluginManager()
    mgr._discovered = True
    monkeypatch.setattr(plugins_mod, "_plugin_manager", mgr)
    monkeypatch.setattr(plugins_mod, "_plugin_managers_by_home", {})
    return PluginContext(PluginManifest(name="pre-compress-observer", source="user"), mgr)


def test_pre_compress_is_timeout_bounded_and_keyed_by_session():
    from hermes_cli.plugins_dispatch import _HOOK_CALL_IDENTITY_FIELDS, _HOOK_TIMEOUT_BOUNDED_HOOKS

    assert "pre_compress" in _HOOK_TIMEOUT_BOUNDED_HOOKS
    assert _HOOK_CALL_IDENTITY_FIELDS["pre_compress"] == ("session_id",)


def test_fire_pre_compress_invokes_hook(ctx):
    fired = []

    def boom(**_kw):
        raise RuntimeError("plugin bug")

    ctx.register_hook("pre_compress", lambda **kw: fired.append(kw))
    ctx.register_hook("pre_compress", boom)
    fire_pre_compress(
        session_id="s1", turn_count=4, context_tokens=8192, trigger_reason="auto",
    )
    [kw] = fired
    assert (kw["session_id"], kw["turn_count"], kw["context_tokens"], kw["trigger_reason"]) == (
        "s1", 4, 8192, "auto",
    )


def test_pre_compress_fires_from_begin_compression_attempt(ctx):
    fired = []
    ctx.register_hook("pre_compress", lambda **kw: fired.append(kw))
    agent = _Agent(_compressor())
    _begin_compression_attempt(
        agent, force=False, defer_notification=False, trigger="pre_api", approx_tokens=80_000,
    )
    [kw] = fired
    assert kw["session_id"] == "session-events-test"
    assert kw["context_tokens"] == 80_000
    assert kw["trigger_reason"] == "pre_api"


def test_a_slow_callback_for_one_session_does_not_skip_another(ctx):
    entered, release, seen = threading.Event(), threading.Event(), []

    def slow(session_id, **_kw):
        seen.append(session_id)
        if session_id == "a":
            entered.set()
            release.wait(10)

    ctx.register_hook("pre_compress", slow)
    first = threading.Thread(target=ctx._manager.invoke_hook, args=("pre_compress",), kwargs={"session_id": "a"})
    first.start()
    assert entered.wait(10)
    try:
        ctx._manager.invoke_hook("pre_compress", session_id="b")
    finally:
        release.set()
        first.join(10)

    assert sorted(seen) == ["a", "b"]
