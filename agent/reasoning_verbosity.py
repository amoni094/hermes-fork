"""Reasoning verbosity: compact or suppress <think> history on simple turns.

Three modes for <think> / <thinking> block handling:

- ``full``: keep all thinking (default, complex tasks)
- ``compact``: strip thinking from stored history after a turn completes
- ``suppress``: skip thinking-only prefill (effort none/low); do not send
  thinking-only continuation turns to the model
"""
from __future__ import annotations

import re
from typing import Any, Iterator, List

_VALID_MODES = ("full", "compact", "suppress")
_HIGH_EFFORT = frozenset({"high", "xhigh", "max"})
_COMPACT_EFFORT = frozenset({"low", "medium"})
_SUPPRESS_EFFORT = frozenset({"none", "off", "disabled", "minimal", "low"})

# Named <think> / <thinking> blocks only. DOTALL so multi-line reasoning is removed.
_THINK_BLOCK_RE = re.compile(
    r"<\s*(think|thinking)\s*>.*?<\s*/\s*\1\s*>",
    re.DOTALL | re.IGNORECASE,
)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def _effort_of(agent: Any) -> str:
    cfg = getattr(agent, "reasoning_config", None)
    if not isinstance(cfg, dict):
        return "medium"
    if cfg.get("enabled") is False:
        return "none"
    return str(cfg.get("effort") or "medium").strip().lower()


def _strip_think_text(text: str) -> str:
    stripped = _THINK_BLOCK_RE.sub("", text)
    stripped = _MULTI_BLANK_RE.sub("\n\n", stripped)
    return stripped


def _strip_content(content: Any) -> Any:
    if isinstance(content, str):
        return _strip_think_text(content)
    if isinstance(content, list):
        out: List[Any] = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                new_part = dict(part)
                new_part["text"] = _strip_think_text(part["text"])
                out.append(new_part)
            elif isinstance(part, str):
                out.append(_strip_think_text(part))
            else:
                out.append(part)
        return out
    return content


def _is_completed_assistant(msg: Any) -> bool:
    """True for a finished assistant turn that is safe to compact.

    Never touches the current streaming / thinking-prefill stub.
    """
    if not isinstance(msg, dict) or msg.get("role") != "assistant":
        return False
    if msg.get("_thinking_prefill") or msg.get("_streaming") or msg.get("_incomplete"):
        return False
    if msg.get("finish_reason") == "incomplete":
        return False
    return True


def _history_lists(agent: Any) -> Iterator[list]:
    seen: set[int] = set()
    for attr in ("conversation_history", "_session_messages"):
        hist = getattr(agent, attr, None)
        if isinstance(hist, list) and id(hist) not in seen:
            seen.add(id(hist))
            yield hist


def compact_thinking_history(agent: Any) -> None:
    """Strip completed-turn <think> blocks from stored assistant messages.

    No-op unless verbosity is ``compact`` and current effort is low/medium.
    Idempotent. Never strips high/xhigh/max effort turns or in-flight streams.
    """
    if agent is None:
        return
    should = getattr(agent, "_should_compact_thinking", None)
    if not callable(should) or not should():
        return
    if _effort_of(agent) in _HIGH_EFFORT:
        return
    if _effort_of(agent) not in _COMPACT_EFFORT:
        return
    for hist in _history_lists(agent):
        for msg in hist:
            if not _is_completed_assistant(msg):
                continue
            if "content" in msg:
                msg["content"] = _strip_content(msg["content"])


class ReasoningVerbosityMixin:
    """Three verbosity modes for <think> block handling on AIAgent."""

    def _reset_reasoning_verbosity(self) -> None:
        self._reasoning_verbosity_mode = "full"
        self._suppress_thinking_prefill = False

    def set_reasoning_verbosity(self, mode: str) -> None:
        if mode not in _VALID_MODES:
            return
        self._reasoning_verbosity_mode = mode
        if mode == "suppress" and _effort_of(self) in _SUPPRESS_EFFORT | {"none"}:
            self._suppress_thinking_prefill = True
        else:
            self._suppress_thinking_prefill = False

    def get_reasoning_verbosity(self) -> str:
        mode = getattr(self, "_reasoning_verbosity_mode", "full")
        return mode if mode in _VALID_MODES else "full"

    def _should_compact_thinking(self) -> bool:
        if self.get_reasoning_verbosity() != "compact":
            return False
        return _effort_of(self) in _COMPACT_EFFORT

    def reset_session_state(self, *args: Any, **kwargs: Any) -> None:
        parent = getattr(super(), "reset_session_state", None)
        if callable(parent):
            parent(*args, **kwargs)
        self._reset_reasoning_verbosity()
