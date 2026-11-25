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
    r"\b(refactor|restructure|reorganise|reorganize|overhaul)\b",
    re.IGNORECASE,
)
# rename is always cross-file regardless of query length
_RENAME_RE = re.compile(r"\brename\b", re.IGNORECASE)

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

    depth is ``simple`` (deepseek-v4-pro), ``analytical`` (grok-4.7),
    ``deep`` (gpt-5.6-sol), or ``elite`` (claude-opus-5 for trajectory).
    ``turn_index`` / ``prior_tier`` are part of the public signature so
    callers can pass the same routing state as the classifier; trajectory
    uses ``consecutive_reason_turns``.

    Tier-inherit: single-token acknowledgments ("y", "do it", "do all",
    "do N") carry forward the prior depth rather than re-routing.  This
    preserves the model context for approval turns in a long thread.
    """
    q = query if isinstance(query, str) else str(query or "")
    words = q.split()

    # TIER-INHERIT: single-token acknowledgments carry forward prior depth.
    # Covers: y/yes/n/no, "do it", "do all", "do N" (single digit/option),
    # "go ahead", "proceed", "confirmed", "ok", "sure", "yep", "nope".
    _ACK_RE = re.compile(
        r"^(y|yes|n|no|yep|nope|ok|okay|sure|confirmed|proceed|go ahead"
        r"|do (it|all|that|\d+)|done|correct|right|exactly|perfect|great"
        r"|sounds good|looks good|that works|ship it|lgtm)\.?$",
        re.IGNORECASE,
    )
    if prior_tier and len(words) <= 4 and _ACK_RE.match(q.strip()):
        # Map prior tier string back to depth — prior_tier is the depth label
        # or a tier name from the 6-tier classifier; normalise to depth names.
        _TIER_TO_DEPTH = {
            "elite": DEPTH_ELITE,
            "deep": DEPTH_DEEP,
            "analytical": DEPTH_ANALYTICAL,
            "simple": DEPTH_SIMPLE,
        }
        inherited = _TIER_TO_DEPTH.get(prior_tier)
        if inherited:
            return inherited, f"tier_inherit:{prior_tier}"

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

    # RENAME: always cross-file regardless of query length
    if _RENAME_RE.search(q):
        return DEPTH_DEEP, "complex_refactor"

    # LONG MULTI-CLAUSE: very long query with multiple joins
    if len(words) > 50:
        return DEPTH_DEEP, "complex_query"

    # ANALYTICAL: multi-step reasoning, constraint-solving, proof-like — grok-4.7
    # Signals: debug/trace/prove/logic keywords, or medium-length queries with specific operators
    # Also covers security hardening work (audit/assess/inspect/harden/review/examine)
    if len(words) > 15 and re.search(
        r'\b(debug|trace|prove|proof|logic|constraint|deduce|infer|verify|analyse|analyze'
        r'|step.by.step|walk.through|explain.why|reason.through'
        r'|audit|assess|inspect|harden|review|examine)\b',
        q, re.IGNORECASE
    ):
        return DEPTH_ANALYTICAL, "analytical_reasoning"

    return DEPTH_SIMPLE, "reason_simple"
