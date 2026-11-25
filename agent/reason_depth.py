"""Reason-tier depth split: simple / deep / elite model selection.

Used after the 6-tier classifier has already chosen ``reason``. Feature is
config-driven in ``model_router`` (off unless ``reason_deep_model`` or
``reason_elite_model`` is set).
"""

from __future__ import annotations

import re
from typing import Optional

# Follow-up filter: cheap follow-up queries that look like reason turns to the
# 6-tier classifier but are NOT trajectory-hard reasoning.  Phrases that start
# or dominate a short query and indicate clarification / incremental steering
# rather than a new independent reasoning task.  These should NOT increment the
# trajectory latch — treat them as simple even if consecutive_reason_turns >= 2.
#
# Rule: query is a follow-up IFF len(words) <= 12 AND it starts with one of
# these patterns.  Longer queries (>12 words) are treated as substantive even
# if they start with "can" / "is there" etc., because the user is asking
# something new and complex.
_FOLLOWUP_START_RE = re.compile(
    r"^(also[,\s]|can (you|it|she|he|we|i)\b|is there\b|what about\b|"
    r"how (do|does|about|come)\b|just\b|and\b|ok[,\s]|okay[,\s]|"
    r"so\b|wait[,\s]|actually[,\s]|does (it|that|this)\b|"
    r"why (is|does|did|would|not)\b|when (is|does|will|should)\b|"
    r"where (is|does|can|should)\b|which (one|is|should|would)\b|"
    r"any (other|more|alternatives|suggestions)\b|"
    r"what (if|else|other|does|is the|are the|about)\b)",
    re.IGNORECASE,
)

# Signals that force gpt-5.5 (interpretive / multi-constraint reasoning)
_MULTI_CONSTRAINT_RE = re.compile(
    r"\b(reconcile|conflicting|ambiguous|without breaking|"
    r"while (keeping|preserving|maintaining)|"
    r"but (also|keep|don.t|without)|"
    r"multiple.{0,20}(files|classes|modules|constraints)|"
    r"across (all|multiple|several).{0,30}(files|components|modules))\b",
    re.IGNORECASE,
)

_MULTI_ACTION_RE = re.compile(
    r"\b(refactor|rename|restructure|reorganise|reorganize|overhaul)\b",
    re.IGNORECASE,
)

DEPTH_SIMPLE = "simple"
DEPTH_ANALYTICAL = "analytical"
DEPTH_DEEP = "deep"
DEPTH_ELITE = "elite"


def needs_deep_reason(
    query: str,
    turn_index: int = 0,
    prior_tier: Optional[str] = None,
    consecutive_reason_turns: int = 0,
) -> tuple[str, str]:
    """Return ``(depth, reason_string)``.

    depth is ``simple`` (deepseek-v4-pro), ``deep`` (gpt-5.5), or
    ``elite`` (sonnet-5-5 for trajectory). ``turn_index`` / ``prior_tier``
    are part of the public signature so callers can pass the same routing
    state as the classifier; trajectory uses ``consecutive_reason_turns``.
    """
    _ = (turn_index, prior_tier)
    q = query if isinstance(query, str) else str(query or "")
    words = q.split()

    # TRAJECTORY: 2+ consecutive reason turns = accumulating context state.
    # Guard: cheap follow-ups (short query starting with a clarification word)
    # do NOT qualify — they steer an existing thread rather than extend it.
    if consecutive_reason_turns >= 2:
        is_followup = len(words) <= 12 and bool(_FOLLOWUP_START_RE.match(q.strip()))
        if not is_followup:
            return DEPTH_ELITE, "trajectory_depth"

    # MULTI-CONSTRAINT: explicit reconciliation or conflicting requirements
    if _MULTI_CONSTRAINT_RE.search(q):
        return DEPTH_DEEP, "multi_constraint"

    # COMPLEX REFACTOR: rename/restructure + long query (likely cross-file)
    if _MULTI_ACTION_RE.search(q) and len(words) > 20:
        return DEPTH_DEEP, "complex_refactor"

    # LONG MULTI-CLAUSE: very long query with multiple joins
    if len(words) > 50:
        return DEPTH_DEEP, "complex_query"

    # ANALYTICAL: multi-step reasoning, constraint-solving, proof-like — gpt-5.4-mini
    # Signals: debug/trace/prove/logic keywords, or medium-length queries with specific operators
    if len(words) > 15 and re.search(
        r'\b(debug|trace|prove|proof|logic|constraint|deduce|infer|verify|analyse|analyze'
        r'|step.by.step|walk.through|explain.why|reason.through)\b',
        q, re.IGNORECASE
    ):
        return DEPTH_ANALYTICAL, "analytical_reasoning"

    return DEPTH_SIMPLE, "reason_simple"
