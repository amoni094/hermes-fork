"""Reasoning verbosity mixin: compact/suppress thinking history."""
from __future__ import annotations

from agent.reasoning_verbosity import (
    ReasoningVerbosityMixin,
    compact_thinking_history,
)


class _Agent(ReasoningVerbosityMixin):
    def __init__(self, effort: str = "low", history: list | None = None):
        self._reset_reasoning_verbosity()
        self.reasoning_config = {"enabled": True, "effort": effort}
        self.conversation_history = list(history or [])
        self._session_messages = self.conversation_history


def _think_msg(text: str = "hello", thinking: str = "secret chain") -> dict:
    return {
        "role": "assistant",
        "content": f"<think>{thinking}</think>\n{text}",
    }


def test_compact_strips_think_blocks_for_low_effort():
    agent = _Agent(effort="low", history=[_think_msg(), {"role": "user", "content": "hi"}])
    agent.set_reasoning_verbosity("compact")
    assert agent._should_compact_thinking() is True
    compact_thinking_history(agent)
    content = agent.conversation_history[0]["content"]
    assert "<think>" not in content
    assert "secret chain" not in content
    assert "hello" in content


def test_compact_keeps_think_blocks_for_high_effort():
    agent = _Agent(effort="high", history=[_think_msg()])
    agent.set_reasoning_verbosity("compact")
    assert agent._should_compact_thinking() is False
    compact_thinking_history(agent)
    content = agent.conversation_history[0]["content"]
    assert "<think>secret chain</think>" in content
    assert "hello" in content


def test_suppress_mode_set():
    agent = _Agent(effort="low")
    agent.set_reasoning_verbosity("suppress")
    assert agent.get_reasoning_verbosity() == "suppress"
    assert agent._suppress_thinking_prefill is True
    assert agent._should_compact_thinking() is False

    none_agent = _Agent(effort="none")
    none_agent.set_reasoning_verbosity("suppress")
    assert none_agent._suppress_thinking_prefill is True


def test_full_mode_no_strip():
    agent = _Agent(effort="low", history=[_think_msg()])
    agent.set_reasoning_verbosity("full")
    assert agent.get_reasoning_verbosity() == "full"
    assert agent._should_compact_thinking() is False
    compact_thinking_history(agent)
    assert "<think>secret chain</think>" in agent.conversation_history[0]["content"]


def test_idempotent_compact():
    agent = _Agent(effort="medium", history=[_think_msg(), _think_msg("bye", "other")])
    agent.set_reasoning_verbosity("compact")
    compact_thinking_history(agent)
    first = [dict(m) for m in agent.conversation_history]
    compact_thinking_history(agent)
    compact_thinking_history(agent)
    assert agent.conversation_history[0]["content"] == first[0]["content"]
    assert agent.conversation_history[1]["content"] == first[1]["content"]
    assert "<think>" not in agent.conversation_history[0]["content"]
    assert "<thinking>" not in agent.conversation_history[0]["content"]


def test_verbosity_reset_on_new_session():
    agent = _Agent(effort="low")
    agent.set_reasoning_verbosity("compact")
    assert agent.get_reasoning_verbosity() == "compact"
    agent.reset_session_state()
    assert agent.get_reasoning_verbosity() == "full"
    assert agent._suppress_thinking_prefill is False
    assert agent._should_compact_thinking() is False
