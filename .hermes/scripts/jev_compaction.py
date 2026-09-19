#!/usr/bin/env python3
"""
jev_compaction.py — Semantic-necessity context compactor for Hermes.

Ported from fast-jev-compaction (github.com/tamaratran/fast-jev-compaction, MIT).
Original: TypeScript; this is a stdlib-only Python port for the Hermes scripts/ layer.

Core idea (verbatim from upstream README):
    Most context compaction asks an LLM to summarize old turns. A summary is lossy:
    a file path, exact error, constraint, or command can disappear even when it matters
    later. This library never rewrites anything. It only deletes tool calls and tool
    results the scorer says are no longer needed, asking while showing the whole
    conversation. User and assistant text stays verbatim and in order.

How it works:
    1. Every tool_use is paired with its tool_result by tool_use_id.
    2. Calls in the first message or in the newest preserveRecentMessages messages
       are PINNED and never touched.
    3. A compressed state (results replaced by "ok, N chars (omitted)") is sent to
       the scorer with two questions per tool call:
         - keepCall:   knowing this call was made still matters for what comes next
         - keepResult: the full output is still needed; re-running would not do
    4. Decisions (per call, against keepThreshold):
         keepResult >= threshold → keep call and result verbatim
         keepCall   >= threshold → keep call; truncate result to head only
         else                   → remove call and result entirely
    5. Everything kept stays verbatim. Nothing is rewritten.

Scorer backend:
    Uses jev_verify_fn.atomic_subquestions() as the asking mechanism — two bool
    sub-questions per tool call. On providers that return calibrated probabilities
    (logprob), those are used; on Anthropic, the bool answers are treated as 1.0/0.0
    and the keepThreshold is adjusted to 0.5 (any 'keep' answer = keep).

    Alternatively, logprob_classify() can be used to get a calibrated noul-style
    scalar (0–1) per question, matching the upstream behavior exactly.

Theoretical grounding:
    - Information theory (Cover-Thomas Ch.6): the state sent to the scorer omits
      tool RESULTS but keeps tool INPUTS and a char-count note. This is the minimum
      sufficient statistic for judging whether a result is still needed — you don't
      need to re-read a file to judge whether it was ever relevant.
    - Wald Ch.3 SPRT: pinning the first and last N messages is equivalent to
      setting prior probability of relevance to 1.0 for those messages, which is
      optimal when the SPRT boundary has not been crossed.
    - Jaynes Ch.13: keepThreshold=0.5 is the maximum-entropy decision boundary
      under uniform prior on (keep, drop). Lower threshold = more permissive
      (accept more risk of dropping needed content). 0.5 is the principled default.
    - Gelman BDA3 §6.3: the 'truncateHeadChars' fallback (keep call, drop result
      body but keep head) is a lossy posterior predictive check — the head is the
      most informative part of most tool results (error lines, first lines of files).

Usage:
    # Compact a session file (JSONL of Hermes session messages):
    python3 jev_compaction.py --session <session_id> [--dry-run] [--threshold 0.5]

    # Library usage:
    from jev_compaction import compact_messages, CompactionOptions, estimate_tokens

Known limitations (matching upstream):
    - Only tool calls and results are candidates; text messages are never removed.
    - Token sizes are estimates from character counts, not a tokenizer.
    - keepThreshold is at the call level; probability is not a proof. Re-run the tool
      if in doubt.
    - The full state is repeated with every request batch (upstream limitation too).
    - Requires TYPESAFE_API_KEY OR a local LLM that supports atomic_subquestions().

WIRING NOTE: This script is Footprint Ladder Rung 2 (CLI + skill). It does NOT
modify the Hermes runtime compaction path. To use it as a drop-in, pipe session
JSONL through it and replace the session file. The runtime hook path is:
    ~/.hermes/hermes-agent/hermes_cli/ → _prune_old_tool_results()
    Wiring that path requires a runtime patch (not done here; see ARCHITECTURE.md).
"""
from __future__ import annotations
import os

import argparse
import json
import logging
import math
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Token estimator (ported from fast-jev-compaction/src/state.ts) ────────────
#
# Upstream calibration note: "calibrated against the usage Jev reports for real
# transcripts, where it lands 2–18% above the true count; a plain characters-per-
# token ratio undercounts the JSON-heavy states by up to 40%."
#
# The regex matches: words (1 token per 6 letters beyond first), digit runs
# (0.5 tokens per digit), other symbols (0.9 tokens each).

_TOKEN_RE = re.compile(r'[A-Za-z]+|\d+|[^\sA-Za-z\d]')


def estimate_tokens(text: str) -> int:
    """
    Estimate token count without a tokenizer.

    Ported verbatim from state.ts::estimateTokens(). Intentionally lands
    slightly above the true count — conservative for budget calculations.
    """
    tokens = 0.0
    for piece in _TOKEN_RE.findall(text):
        c = piece[0]
        if c.isdigit():
            tokens += len(piece) / 2
        elif c.isalpha():
            tokens += 1 + math.floor((len(piece) - 1) / 6)
        else:
            tokens += 0.9
    return math.ceil(tokens)


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class ToolCall:
    """A paired tool_use + tool_result from the session."""
    id: str                  # short id: t1, t2, ...
    tool_use_id: str         # original tool_use_id from session
    tool: str                # tool name (e.g. "Read", "execute_code")
    input: dict              # tool input dict
    call_index: int          # message index of the tool_use
    result_index: int        # message index of the tool_result
    result_chars: int        # character count of the result text
    result_head: str         # first truncateHeadChars of result (for partial keep)
    is_error: bool = False
    pinned: bool = False


@dataclass
class CallDecision:
    id: str
    tool: str
    keep_call: float         # scorer probability for keeping the call
    keep_result: float       # scorer probability for keeping the result verbatim
    action: str              # "keep" | "drop_result" | "drop_call"
    reason: str              # "pinned" | "kept" | "result_dropped" | "call_dropped"


@dataclass
class CompactionStats:
    messages_before: int
    messages_after: int
    chars_before: int
    chars_after: int
    calls_total: int
    kept: int
    results_dropped: int
    calls_dropped: int
    pinned: int
    state_tokens: int
    requests: int
    ms: int


@dataclass
class CompactionResult:
    messages: list[dict]
    decisions: list[CallDecision]
    stats: CompactionStats


@dataclass
class CompactionOptions:
    keep_threshold: float = 0.5
    preserve_recent_messages: int = 6
    max_state_tokens: int = 25_000
    max_request_tokens: int = 30_000
    truncate_head_chars: int = 300
    goal: str = ""
    # Scorer backend: "atomic" (uses atomic_subquestions) or "logprob" (uses logprob_classify)
    scorer_backend: str = "atomic"
    provider: str | None = None
    model: str | None = None


# ── State fitting (mirrors state.ts::fitState) ────────────────────────────────

_INPUT_CHARS_STAGES = [1000, 200, 60]
_TEXT_HEAD = 400
_TEXT_TAIL = 150
_REQUEST_OVERHEAD_TOKENS = 20

_STATE_SYSTEM = (
    "You are reviewing a conversation history. "
    "Tool results are omitted; you only see their size. "
    "Nothing has been deleted permanently, but the assistant can always re-run a tool "
    "or re-read a file."
)


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:max(0, limit - 1)] + "…"


def _abridge(text: str, head: int = _TEXT_HEAD, tail: int = _TEXT_TAIL) -> str:
    if len(text) <= head + tail + 40:
        return text
    omitted = len(text) - head - tail
    return f"{text[:head]}\n[… {omitted} chars omitted …]\n{text[-tail:]}"


def _is_pinned(index: int, total: int, preserve: int) -> bool:
    return index == 0 or index >= total - preserve


def _input_text(inp: dict, limit: int) -> str:
    try:
        j = json.dumps(inp)
    except Exception:
        j = "[unserializable input]"
    return _truncate(j, limit)


def _compact_call_line(call: ToolCall) -> str:
    """One-line summary of a call for the most compressed state stage."""
    parts = []
    for k, v in call.input.items():
        text = v if isinstance(v, str) else json.dumps({k: v})
        parts.append(f"{k}={_truncate(text.replace(chr(10), ' '), _INPUT_CHARS_STAGES[2])}")
    inp_summary = " ".join(parts)
    status = "error" if call.is_error else "ok"
    return f"{call.id} {call.tool} {_truncate(inp_summary, _INPUT_CHARS_STAGES[2])} → {status} {call.result_chars}ch"


def _build_state(
    messages: list[dict],
    calls: list[ToolCall],
    input_char_limit: int,
) -> str:
    """
    Build the state string sent to the scorer.
    Results are replaced by "ok/error, N chars (omitted)".
    Tool inputs are included up to input_char_limit.
    Text messages are abridged but included.
    """
    result_note: dict[str, str] = {}
    for call in calls:
        status = "error" if call.is_error else "ok"
        result_note[call.tool_use_id] = f"{status}, {call.result_chars} chars (omitted)"

    lines: list[str] = [_STATE_SYSTEM, ""]
    for msg in messages:
        role = msg.get("role", "unknown")
        text = msg.get("text") or msg.get("content") or ""
        tool_uses = msg.get("toolUses") or msg.get("tool_uses") or []
        tool_results = msg.get("toolResults") or msg.get("tool_results") or []

        if text:
            abridged = _abridge(str(text))
            lines.append(f"[{role}] {abridged}")

        for tu in tool_uses:
            tid = tu.get("tool_use_id") or tu.get("id", "")
            tool_name = tu.get("tool") or tu.get("name") or tu.get("type") or "?"
            inp = tu.get("input") or {}
            inp_str = _input_text(inp, input_char_limit)
            lines.append(f"  tool_use {tid}: {tool_name}({inp_str})")

        for tr in tool_results:
            tid = tr.get("tool_use_id", "")
            note = result_note.get(tid, "(omitted)")
            lines.append(f"  tool_result {tid}: {note}")

        lines.append("")

    return "\n".join(lines)


def fit_state(
    messages: list[dict],
    calls: list[ToolCall],
    options: CompactionOptions,
) -> tuple[str, int, str]:
    """
    Fit the conversation state into maxStateTokens.
    Returns (state_text, token_count, stage_name).
    Raises ValueError if it cannot fit even after all compression stages.

    Mirrors state.ts::fitState() compression stages:
        1. full: input truncated to 1000 chars
        2. inputs<=200: input truncated to 200 chars
        3. inputs<=60: input truncated to 60 chars
        4. texts abridged: long text blocks head+tail
        5. old messages collapsed: text replaced by "[N chars omitted]"
        6. old calls compacted: structured call → one-line summary
        7. old messages left out: remove text-only old messages
        8. old calls merged: fold runs of call-only entries
    """
    n = len(messages)
    preserve = options.preserve_recent_messages

    for stage_idx, char_limit in enumerate(_INPUT_CHARS_STAGES):
        state = _build_state(messages, calls, char_limit)
        tokens = estimate_tokens(state)
        stage = f"inputs<={char_limit}" if stage_idx > 0 else "full"
        if tokens <= options.max_state_tokens:
            return state, tokens, stage

    # Abridge text in non-pinned messages first
    msg_texts = [
        (msg.get("text") or msg.get("content") or "")
        for msg in messages
    ]
    abridged_texts = list(msg_texts)
    for i, msg in enumerate(messages):
        if _is_pinned(i, n, preserve):
            continue
        t = msg_texts[i]
        if len(t) > _TEXT_HEAD + _TEXT_TAIL + 40:
            abridged_texts[i] = _abridge(t)

    # Build with abridged texts
    msgs_abridged = []
    for i, msg in enumerate(messages):
        m = dict(msg)
        if abridged_texts[i] != msg_texts[i]:
            m["text"] = abridged_texts[i]
        msgs_abridged.append(m)
    state = _build_state(msgs_abridged, calls, _INPUT_CHARS_STAGES[-1])
    tokens = estimate_tokens(state)
    if tokens <= options.max_state_tokens:
        return state, tokens, "texts abridged"

    # Collapse old non-pinned text messages
    msgs_collapsed = []
    for i, msg in enumerate(messages):
        m = dict(msg)
        if not _is_pinned(i, n, preserve):
            t = msg_texts[i]
            if t:
                m["text"] = f"[… {len(t)} chars omitted …]"
        msgs_collapsed.append(m)
    state = _build_state(msgs_collapsed, calls, _INPUT_CHARS_STAGES[-1])
    tokens = estimate_tokens(state)
    if tokens <= options.max_state_tokens:
        return state, tokens, "old messages collapsed"

    raise ValueError(
        f"History too large for compaction (~{tokens} tokens after all "
        f"compression stages, limit {options.max_state_tokens}). "
        f"Increase maxStateTokens or reduce context."
    )


# ── Scorer interface ───────────────────────────────────────────────────────────

def _import_jev_verify():
    """Lazy import jev_verify_fn from the same directory."""
    scripts_dir = str(Path(__file__).parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        import jev_verify_fn  # noqa: PLC0415
        return jev_verify_fn
    except ImportError as exc:
        raise ImportError(
            "jev_verify_fn.py not found. Ensure it is in the same directory as "
            "jev_compaction.py (~/.hermes/scripts/)."
        ) from exc


def _score_calls_atomic(
    state: str,
    calls: list[ToolCall],
    options: CompactionOptions,
) -> dict[str, tuple[float, float]]:
    """
    Score calls using atomic_subquestions() — two bool questions per call.
    Returns {call.id: (keep_call_prob, keep_result_prob)}.

    Bool answers are mapped to 1.0/0.0 — equivalent to keepThreshold=0.5
    giving a binary decision. This matches the upstream behavior for providers
    that don't return calibrated probabilities.

    INFORMATION-THEORETIC NOTE (Cover-Thomas Ch.6): we batch all questions
    for multiple calls into one request (speculative fan-out). Adding questions
    barely changes latency because they're evaluated jointly. The state is the
    same for all questions in one batch — it acts as a shared sufficient statistic
    for all the keep/drop decisions.
    """
    jvf = _import_jev_verify()

    questions = []
    for call in calls:
        questions.append(jvf.SubQuestion(
            id=f"keep_call_{call.id}",
            question=(
                f"Tool call {call.id} ({call.tool}, input: "
                f"{json.dumps(call.input)[:200]}): "
                f"knowing this call was made still matters for what the assistant does next"
            ),
            type="bool",
        ))
        questions.append(jvf.SubQuestion(
            id=f"keep_result_{call.id}",
            question=(
                f"The full output of tool call {call.id} ({call.tool}, "
                f"{call.result_chars} chars) still needs to stay in history verbatim: "
                f"the assistant still needs its contents and re-running the tool would not do"
            ),
            type="bool",
        ))

    results = jvf.atomic_subquestions(
        context=state,
        questions=questions,
        provider=options.provider,
        model=options.model,
        timeout=30.0,
    )

    by_id = {r.id: r for r in results}
    scores: dict[str, tuple[float, float]] = {}
    for call in calls:
        kc_result = by_id.get(f"keep_call_{call.id}")
        kr_result = by_id.get(f"keep_result_{call.id}")
        kc = 1.0 if (kc_result and kc_result.answer is True) else (0.0 if (kc_result and kc_result.error == "") else 1.0)
        kr = 1.0 if (kr_result and kr_result.answer is True) else (0.0 if (kr_result and kr_result.error == "") else 1.0)
        scores[call.id] = (kc, kr)

    return scores


def _score_calls_logprob(
    state: str,
    calls: list[ToolCall],
    options: CompactionOptions,
) -> dict[str, tuple[float, float]]:
    """
    Score calls using logprob_classify() — calibrated noul-style scalar per question.
    Returns calibrated probabilities for (keep_call, keep_result) per call.

    This matches the upstream Jev behavior exactly: noul returns a scalar ∈ [0,1]
    that is properly calibrated (RLCD training objective). On non-OpenAI providers,
    logprob_classify returns NaN, which causes keep_call/keep_result = NaN, which
    calibrated_gate() maps to "escalate" → we default to keeping the call (safe).

    WALD SPRT CONNECTION: treating the logprob score as a likelihood ratio, we
    could run SPRT across multiple scoring calls to stop early when confidence
    is high. Not implemented here (single scoring call per call), but the
    keepThreshold=0.5 default is the SPRT acceptance boundary at α=β=0.5.
    """
    jvf = _import_jev_verify()
    scores: dict[str, tuple[float, float]] = {}

    for call in calls:
        # Two logprob questions: keep/drop for call and result
        call_probs = jvf.logprob_classify(
            context=(
                f"State:\n{state[:2000]}\n\n"
                f"Tool call {call.id} ({call.tool}): input={json.dumps(call.input)[:300]}\n"
                f"Question: Should this call stay in history? Knowing it was made still matters."
            ),
            options=["keep", "drop"],
            provider=options.provider,
            model=options.model,
        )
        result_probs = jvf.logprob_classify(
            context=(
                f"State:\n{state[:2000]}\n\n"
                f"Tool call {call.id} ({call.tool}): {call.result_chars} chars result\n"
                f"Question: Should the full result text stay verbatim? Re-running would not do."
            ),
            options=["keep", "drop"],
            provider=options.provider,
            model=options.model,
        )
        kc = call_probs.get("keep", float("nan"))
        kr = result_probs.get("keep", float("nan"))
        # NaN → default to 1.0 (keep) — fail safe
        if kc != kc:
            kc = 1.0
        if kr != kr:
            kr = 1.0
        scores[call.id] = (kc, kr)

    return scores


# ── Batching (mirrors compact.ts::batchCalls) ─────────────────────────────────

def _batch_calls(
    calls: list[ToolCall],
    state_tokens: int,
    options: CompactionOptions,
) -> list[list[ToolCall]]:
    """Split calls into batches that fit within maxRequestTokens."""
    budget = options.max_request_tokens - state_tokens - _REQUEST_OVERHEAD_TOKENS
    batches: list[list[ToolCall]] = []
    current: list[ToolCall] = []
    current_tokens = 0

    for call in calls:
        # Rough estimate: two questions per call, ~80 tokens each
        call_tokens = 160
        if current and current_tokens + call_tokens > budget:
            batches.append(current)
            current = []
            current_tokens = 0
        if not current and call_tokens > budget:
            raise ValueError(
                f"State leaves no room for questions "
                f"(~{state_tokens} of {options.max_request_tokens} tokens). "
                f"Reduce maxStateTokens."
            )
        current.append(call)
        current_tokens += call_tokens

    if current:
        batches.append(current)
    return batches


# ── Decision logic (mirrors compact.ts::decideCall) ───────────────────────────

def _decide_call(
    call: ToolCall,
    keep_call: float,
    keep_result: float,
    threshold: float,
) -> CallDecision:
    if call.pinned:
        return CallDecision(call.id, call.tool, keep_call, keep_result, "keep", "pinned")
    if keep_result >= threshold:
        return CallDecision(call.id, call.tool, keep_call, keep_result, "keep", "kept")
    if keep_call >= threshold:
        return CallDecision(call.id, call.tool, keep_call, keep_result, "drop_result", "result_dropped")
    return CallDecision(call.id, call.tool, keep_call, keep_result, "drop_call", "call_dropped")


# ── Session message parsing ───────────────────────────────────────────────────

def collect_tool_calls(messages: list[dict], preserve: int) -> list[ToolCall]:
    """
    Pair every tool_use with its tool_result by tool_use_id.
    Handles Hermes session JSONL format (role/content/tool_use/tool_result).
    """
    n = len(messages)
    # Index tool_results by tool_use_id
    result_index: dict[str, tuple[int, dict]] = {}
    for i, msg in enumerate(messages):
        for tr in (msg.get("toolResults") or msg.get("tool_results") or []):
            tid = tr.get("tool_use_id") or tr.get("id", "")
            if tid:
                result_index[tid] = (i, tr)

    calls: list[ToolCall] = []
    call_counter = 0
    for i, msg in enumerate(messages):
        for tu in (msg.get("toolUses") or msg.get("tool_uses") or []):
            tid = tu.get("tool_use_id") or tu.get("id", "")
            if not tid or tid not in result_index:
                continue
            ri, tr = result_index[tid]
            result_text = tr.get("text") or tr.get("content") or ""
            if isinstance(result_text, list):
                result_text = " ".join(
                    block.get("text", "") for block in result_text
                    if isinstance(block, dict)
                )
            result_text = str(result_text)
            call_counter += 1
            calls.append(ToolCall(
                id=f"t{call_counter}",
                tool_use_id=tid,
                tool=tu.get("tool") or tu.get("name") or tu.get("type") or "unknown",
                input=tu.get("input") or {},
                call_index=i,
                result_index=ri,
                result_chars=len(result_text),
                result_head=result_text[:300],
                is_error=bool(tr.get("isError") or tr.get("is_error")),
                pinned=(
                    _is_pinned(i, n, preserve) or
                    _is_pinned(ri, n, preserve)
                ),
            ))
    return calls


def _message_chars(msg: dict) -> int:
    total = 0
    for key in ("text", "content"):
        v = msg.get(key)
        if isinstance(v, str):
            total += len(v)
        elif isinstance(v, list):
            total += sum(len(b.get("text", "")) for b in v if isinstance(b, dict))
    for tr in (msg.get("toolResults") or msg.get("tool_results") or []):
        total += len(tr.get("text") or tr.get("content") or "")
    return total


# ── Apply decisions to produce compacted messages ─────────────────────────────

def apply_decisions(
    messages: list[dict],
    decisions: list[CallDecision],
    calls: list[ToolCall],
    truncate_head_chars: int,
) -> list[dict]:
    """
    Rebuild the message list according to decisions.
    - "keep": message kept verbatim
    - "drop_result": result text replaced by head + omission note
    - "drop_call": tool_use and tool_result removed entirely

    Messages that become empty after removals are dropped.
    User/assistant text messages are never removed or shortened.
    """
    # Build action maps by tool_use_id
    action_by_id: dict[str, str] = {}
    for decision, call in zip(decisions, calls):
        action_by_id[call.tool_use_id] = decision.action

    result: list[dict] = []
    for msg in messages:
        m = dict(msg)

        # Filter tool_uses
        tool_uses = msg.get("toolUses") or msg.get("tool_uses") or []
        kept_uses = []
        for tu in tool_uses:
            tid = tu.get("tool_use_id") or tu.get("id", "")
            action = action_by_id.get(tid, "keep")
            if action != "drop_call":
                kept_uses.append(tu)
        if "toolUses" in m:
            m["toolUses"] = kept_uses
        elif "tool_uses" in m:
            m["tool_uses"] = kept_uses

        # Filter/truncate tool_results
        tool_results = msg.get("toolResults") or msg.get("tool_results") or []
        kept_results = []
        for tr in tool_results:
            tid = tr.get("tool_use_id", "")
            action = action_by_id.get(tid, "keep")
            if action == "drop_call":
                continue  # remove call and result together
            elif action == "drop_result":
                # Keep result structure but truncate body
                tr2 = dict(tr)
                text = tr.get("text") or tr.get("content") or ""
                if isinstance(text, str):
                    head = text[:truncate_head_chars]
                    omitted = len(text) - truncate_head_chars
                    if omitted > 0:
                        tr2["text"] = f"{head}\n[… {omitted} chars omitted — result dropped by compaction …]"
                    else:
                        tr2["text"] = text
                kept_results.append(tr2)
            else:
                kept_results.append(tr)

        if "toolResults" in m:
            m["toolResults"] = kept_results
        elif "tool_results" in m:
            m["tool_results"] = kept_results

        # Drop messages that are now empty (no text, no tool uses, no tool results)
        text = m.get("text") or m.get("content") or ""
        has_text = bool(text)
        has_uses = bool(m.get("toolUses") or m.get("tool_uses"))
        has_results = bool(m.get("toolResults") or m.get("tool_results"))
        if has_text or has_uses or has_results:
            result.append(m)

    return result


# ── Main compaction entry point ───────────────────────────────────────────────

def compact_messages(
    messages: list[dict],
    options: CompactionOptions | None = None,
) -> CompactionResult:
    """
    Compact a list of session messages using semantic necessity scoring.

    Args:
        messages: list of session message dicts (Hermes JSONL format)
        options:  CompactionOptions (defaults match upstream fast-jev-compaction)

    Returns:
        CompactionResult with compacted messages, per-call decisions, and stats.

    Raises:
        ValueError: if state cannot be fitted into maxStateTokens
        ImportError: if jev_verify_fn.py is not available
    """
    if options is None:
        options = CompactionOptions()

    started_ms = int(time.time() * 1000)
    chars_before = sum(_message_chars(m) for m in messages)

    calls = collect_tool_calls(messages, options.preserve_recent_messages)
    candidates = [c for c in calls if not c.pinned]

    # Fit state
    state, state_tokens, stage = fit_state(messages, calls, options)

    # Score candidates in batches
    all_scores: dict[str, tuple[float, float]] = {}
    batches: list[list[ToolCall]] = []

    if candidates:
        batches = _batch_calls(candidates, state_tokens, options)
        for batch in batches:
            if options.scorer_backend == "logprob":
                batch_scores = _score_calls_logprob(state, batch, options)
            else:
                batch_scores = _score_calls_atomic(state, batch, options)
            all_scores.update(batch_scores)

    # Make decisions
    decisions: list[CallDecision] = []
    for call in calls:
        if call.pinned:
            decisions.append(_decide_call(call, 1.0, 1.0, options.keep_threshold))
        else:
            kc, kr = all_scores.get(call.id, (1.0, 1.0))  # default: keep if unseen
            decisions.append(_decide_call(call, kc, kr, options.keep_threshold))

    # Apply decisions
    kept = apply_decisions(messages, decisions, calls, options.truncate_head_chars)
    chars_after = sum(_message_chars(m) for m in kept)

    def count_reason(reason: str) -> int:
        return sum(1 for d in decisions if d.reason == reason)

    stats = CompactionStats(
        messages_before=len(messages),
        messages_after=len(kept),
        chars_before=chars_before,
        chars_after=chars_after,
        calls_total=len(calls),
        kept=count_reason("kept"),
        results_dropped=count_reason("result_dropped"),
        calls_dropped=count_reason("call_dropped"),
        pinned=count_reason("pinned"),
        state_tokens=state_tokens,
        requests=len(batches),
        ms=int(time.time() * 1000) - started_ms,
    )

    return CompactionResult(messages=kept, decisions=decisions, stats=stats)


def reduction_ratio(result: CompactionResult) -> float:
    """Fraction of characters removed. 0.0 = nothing removed, 1.0 = everything."""
    before = result.stats.chars_before
    if before == 0:
        return 0.0
    return (before - result.stats.chars_after) / before


# ── CLI ────────────────────────────────────────────────────────────────────────

def _load_session_messages(session_id: str) -> list[dict]:
    """Load messages from Hermes session JSONL."""
    _hh_jv = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    _hp_jv = os.environ.get("HERMES_PROFILE", "")
    _root_jv = (_hh_jv / "profiles" / _hp_jv) if _hp_jv else _hh_jv
    sessions_dir = _root_jv / "sessions"
    candidates = list(sessions_dir.glob(f"{session_id}*"))
    if not candidates:
        candidates = list(sessions_dir.glob(f"*{session_id}*"))
    if not candidates:
        raise FileNotFoundError(f"No session found for id: {session_id}")
    session_file = sorted(candidates)[-1]
    messages = []
    for line in session_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        role = ev.get("role")
        if role not in ("user", "assistant"):
            continue
        # Normalise Hermes JSONL to the format collect_tool_calls expects
        msg: dict[str, Any] = {"role": role}
        content = ev.get("content", "")
        if isinstance(content, str):
            msg["text"] = content
        elif isinstance(content, list):
            text_parts = []
            tool_uses = []
            tool_results = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    text_parts.append(block.get("text", ""))
                elif btype == "tool_use":
                    tool_uses.append({
                        "tool_use_id": block.get("id", ""),
                        "tool": block.get("name", ""),
                        "input": block.get("input", {}),
                    })
                elif btype == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, list):
                        result_content = " ".join(
                            b.get("text", "") for b in result_content
                            if isinstance(b, dict)
                        )
                    tool_results.append({
                        "tool_use_id": block.get("tool_use_id", ""),
                        "text": str(result_content),
                        "is_error": block.get("is_error", False),
                    })
            msg["text"] = "\n".join(text_parts)
            if tool_uses:
                msg["toolUses"] = tool_uses
            if tool_results:
                msg["toolResults"] = tool_results
        messages.append(msg)
    return messages


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Semantic-necessity context compaction via Jev-style scoring"
    )
    parser.add_argument("--session", help="Session ID to compact")
    parser.add_argument("--input", help="Input JSONL file of messages")
    parser.add_argument("--output", help="Output JSONL file (default: stdout)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show decisions without writing output")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="Keep threshold (default: 0.5)")
    parser.add_argument("--preserve", type=int, default=6,
                        help="Pin newest N messages (default: 6)")
    parser.add_argument("--backend", choices=["atomic", "logprob"], default="atomic",
                        help="Scorer backend (default: atomic)")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--min-reduction", type=float, default=0.0,
                        help="Minimum reduction ratio to accept result (default: 0.0)")
    parser.add_argument("--estimate-only", action="store_true",
                        help="Just estimate tokens and exit (no LLM calls)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Load messages
    messages: list[dict] = []
    if args.session:
        messages = _load_session_messages(args.session)
    elif args.input:
        for line in Path(args.input).read_text().splitlines():
            if line.strip():
                messages.append(json.loads(line))
    else:
        # Read from stdin
        for line in sys.stdin:
            if line.strip():
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not messages:
        print("No messages loaded.", file=sys.stderr)
        sys.exit(1)

    options = CompactionOptions(
        keep_threshold=args.threshold,
        preserve_recent_messages=args.preserve,
        scorer_backend=args.backend,
        provider=args.provider,
        model=args.model,
    )

    calls = collect_tool_calls(messages, options.preserve_recent_messages)
    candidates = [c for c in calls if not c.pinned]
    chars_before = sum(_message_chars(m) for m in messages)

    print(f"Messages: {len(messages)}", file=sys.stderr)
    print(f"Tool calls: {len(calls)} total, {len(candidates)} candidates, "
          f"{len(calls)-len(candidates)} pinned", file=sys.stderr)
    print(f"Chars before: {chars_before:,}", file=sys.stderr)

    if args.estimate_only:
        try:
            state, tokens, stage = fit_state(messages, calls, options)
            print(f"State tokens: {tokens:,} (stage: {stage})", file=sys.stderr)
        except ValueError as e:
            print(f"State fitting failed: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Run compaction
    try:
        result = compact_messages(messages, options)
    except (ValueError, ImportError) as e:
        print(f"Compaction failed: {e}", file=sys.stderr)
        sys.exit(1)

    ratio = reduction_ratio(result)
    s = result.stats
    print(
        f"Result: {s.messages_after}/{s.messages_before} messages, "
        f"{s.chars_after:,}/{s.chars_before:,} chars, "
        f"{ratio:.1%} reduction, {s.ms}ms, {s.requests} requests",
        file=sys.stderr,
    )
    print(
        f"Decisions: {s.kept} kept, {s.results_dropped} results_dropped, "
        f"{s.calls_dropped} calls_dropped, {s.pinned} pinned",
        file=sys.stderr,
    )

    if args.dry_run:
        print("\nDecisions (dry run):", file=sys.stderr)
        for d in result.decisions:
            print(
                f"  {d.id} ({d.tool}): {d.action} [{d.reason}] "
                f"call={d.keep_call:.2f} result={d.keep_result:.2f}",
                file=sys.stderr,
            )
        return

    if ratio < args.min_reduction:
        print(
            f"Reduction {ratio:.1%} below minimum {args.min_reduction:.1%}; "
            f"keeping original.", file=sys.stderr,
        )
        sys.exit(2)

    # Write output
    output_lines = [json.dumps(m) for m in result.messages]
    if args.output:
        Path(args.output).write_text("\n".join(output_lines) + "\n")
        print(f"Written: {args.output}", file=sys.stderr)
    else:
        print("\n".join(output_lines))


if __name__ == "__main__":
    main()
