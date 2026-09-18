"""ARB retry-stamp tests (cs-arb-tests, arXiv:2608.25403).

Stamp-only: classify failure entries so a parent/batch aggregator can decide
on a *new* dispatch. In-process re-spawn inside ``_run_single_child`` is not
safe (await_child stop-signals the child).
"""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock

from tools.delegate_tool import (
    _ARB_DEFAULT_RETRIES,
    _apply_arb_stamp,
    _arb_consume_retry,
    _arb_should_retry,
    _load_config,
    _run_single_child,
)


def _timeout_entry(**extra):
    entry = {
        "task_index": 0,
        "status": "timeout",
        "summary": None,
        "error": "Subagent timed out after 1s",
        "exit_reason": "timeout",
        "api_calls": 0,
    }
    entry.update(extra)
    return entry


def test_no_retry_on_timeout_stamp_and_loop():
    """Timeouts are stop-signalled: stamp non-retryable and do not retry."""
    entry = _apply_arb_stamp(_timeout_entry())
    assert entry["arb_retryable"] is False
    assert entry["arb_retries_remaining"] == 0
    assert _arb_should_retry(entry) is False

    # Consuming must not resurrect a timeout into a retry.
    _arb_consume_retry(entry)
    assert entry["arb_retries_remaining"] == 0
    assert _arb_should_retry(entry) is False


def test_run_single_child_timeout_stamps_without_retry(monkeypatch):
    """When a delegation times out, ARB stamp is set and run_conversation is not retried."""
    child = MagicMock()
    child.tool_progress_callback = None
    child._credential_pool = None
    child._subagent_id = None
    child.run_conversation = MagicMock(side_effect=AssertionError("must not be called; await_child is mocked"))

    timeout_entry = _timeout_entry()
    calls = {"await": 0}

    def fake_await(self):
        calls["await"] += 1
        return None, dict(timeout_entry), False

    monkeypatch.setattr("tools.delegate_tool_child_run._ChildRun.await_child", fake_await)
    monkeypatch.setattr("tools.delegate_tool._start_heartbeat", lambda *a, **k: MagicMock())
    monkeypatch.setattr("tools.delegate_tool._register_child", lambda *a, **k: None)
    monkeypatch.setattr("tools.delegate_tool._lease_child_credential", lambda *a, **k: (None, None))
    monkeypatch.setattr(
        "tools.delegate_tool_child_run._ChildRun.cleanup",
        lambda self, **k: None,
    )
    monkeypatch.setattr(
        "tools.delegate_tool_child_run._ChildRun.seed_workspace",
        lambda self: None,
    )

    parent = MagicMock()
    result = _run_single_child(task_index=0, goal="timeout arb", child=child, parent_agent=parent)

    assert calls["await"] == 1
    assert child.run_conversation.call_count == 0
    assert result["status"] == "timeout"
    assert result["arb_retryable"] is False
    assert result["arb_retries_remaining"] == 0
    assert _arb_should_retry(result) is False


def test_arb_retries_remaining_decrements_per_cycle():
    entry = _apply_arb_stamp(
        {"status": "error", "error": "rate limited", "failure_reason": "rate_limit"},
        result={"error": "rate limited", "failure_reason": "rate_limit", "failed": True},
    )
    assert entry["arb_retryable"] is True
    assert entry["arb_retries_remaining"] == _ARB_DEFAULT_RETRIES == 2

    _arb_consume_retry(entry)
    assert entry["arb_retries_remaining"] == 1
    assert entry["arb_retryable"] is True
    assert _arb_should_retry(entry) is True

    _arb_consume_retry(entry)
    assert entry["arb_retries_remaining"] == 0
    assert entry["arb_retryable"] is False
    assert _arb_should_retry(entry) is False


def test_arb_retries_remaining_zero_terminates_retry_loop():
    entry = {"status": "error", "arb_retryable": True, "arb_retries_remaining": 0}
    assert _arb_should_retry(entry) is False

    cycles = 0
    while _arb_should_retry(entry):
        cycles += 1
        _arb_consume_retry(entry)
        assert cycles < 10  # hard stop if the terminator regresses
    assert cycles == 0

    # Starting at 2, the loop runs exactly twice then stops.
    entry = _apply_arb_stamp(
        {"status": "error", "error": "timeout at provider", "failure_reason": "rate_limit"},
        result={"error": "x", "failure_reason": "rate_limit", "failed": True},
    )
    cycles = 0
    while _arb_should_retry(entry):
        cycles += 1
        _arb_consume_retry(entry)
    assert cycles == 2
    assert entry["arb_retries_remaining"] == 0
    assert _arb_should_retry(entry) is False


def test_auth_and_unknown_failures_are_not_retryable():
    auth = _apply_arb_stamp(
        {"status": "error", "error": "invalid api key", "failure_reason": "auth"},
        result={"error": "invalid api key", "failure_reason": "auth", "failed": True},
    )
    assert auth["arb_retryable"] is False
    assert auth["arb_retries_remaining"] == 0
    assert _arb_should_retry(auth) is False

    unknown = _apply_arb_stamp({"status": "error", "error": "something odd"})
    assert unknown["arb_retryable"] is False
    assert unknown["arb_retries_remaining"] == 0


def test_retry_policy_not_read_from_config():
    """``delegation.retry_policy`` is operator guidance, not a live runtime key.

    Why it stays commented out / unread:
    - ARB on this path is stamp-only. In-child retries after timeout/stop are UB.
    - ``_load_config`` returns the ``delegation`` section as-is but never consults
      ``retry_policy``; stamps use a hardcoded remaining=2.
    - The live retry knob elsewhere is ``agent.api_max_retries``, not this block.
    """
    src = inspect.getsource(_load_config)
    assert "retry_policy" not in src
    assert "retry_policy" not in inspect.getsource(_apply_arb_stamp)

    import tools.delegate_tool as dt
    assert dt._ARB_DEFAULT_RETRIES == 2
