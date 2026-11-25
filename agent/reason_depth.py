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
# Design rules:
#   - "can/also/is there/what about/how do/ok/actually/does it/why/when/where/which/any/what"
#     suppress elite only up to their own per-pattern word caps (12 by default for
#     unambiguous clarifiers, 4–5 for high-FP starters like "and"/"just"/"so").
#   - "and"/"just"/"so" are capped tighter (<=5 words) because "and implement the
#     full OAuth2 flow with PKCE" (8w) is substantive.
#   - "could/would/please/continue/keep going/try again" added for thread-steering.
#   - "right?"/"ok?" etc. are ACKs handled by _ACK_RE; not duplicated here.
_FOLLOWUP_START_RE = re.compile(
    r"^(also[,\s]|can (you|it|she|he|we|i)\b|is there\b|what about\b|"
    r"how (do|does|about|come)\b|ok[,\s]|okay[,\s]|"
    r"so\b|wait[,\s]|actually[,\s]|does (it|that|this)\b|"
    r"why (is|does|did|would|not)\b|when (is|does|will|should)\b|"
    r"where (is|does|can|should)\b|which (one|is|should|would)\b|"
    r"any (other|more|alternatives|suggestions)\b|"
    r"what (if|else|other|does|is the|are the|about)\b|"
    r"could (you|we|it)\b|would (you|it)\b|please\b|"
    r"continue\b|keep going\b|try again\b)",
    re.IGNORECASE,
)
# High-FP starters get a tighter cap: they suppress elite only on very short queries.
# "and"/"just"/"so" at <=5 words are almost always steering, not new hard tasks.
_FOLLOWUP_TIGHT_RE = re.compile(
    r"^(just\b|and\b|so\b)",
    re.IGNORECASE,
)
_FOLLOWUP_TIGHT_MAX_WORDS = 5

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
# rename is always cross-file regardless of query length, BUT must reference a
# code object (symbol/file/class/function/method/module/variable/references/all).
# Bare "rename your tone" / "rename your output format" must not go deep.
# Negated renames ("don't rename", "without renaming") are excluded.
_RENAME_RE = re.compile(
    r"(?<!don't )(?<!do not )(?<!without )\brename\b",
    re.IGNORECASE,
)
_RENAME_CODE_OBJ_RE = re.compile(
    r"\b(symbol|file|class|function|method|module|variable|var|references|"
    r"all|every|the \w+|this \w+|import|export|type|interface|constant|const|"
    r"field|property|prop|enum|struct|trait|macro|crate|package|namespace)\b",
    re.IGNORECASE,
)

DEPTH_SIMPLE = "simple"
DEPTH_ANALYTICAL = "analytical"
DEPTH_DEEP = "deep"
DEPTH_ELITE = "elite"

# Tier-inherit: single-token acknowledgments that carry forward the prior depth.
# Covers y/yes/n/no, "do it", "do all", "do N", "go ahead", "lgtm", etc.
# Only fires when prior_tier is set AND len(words) <= 4.
_ACK_RE = re.compile(
    r"^(y|yes|n|no|yep|nope|ok|okay|sure|confirmed|proceed|go ahead"
    r"|do (it|all|that|\d{1,2})|done|correct|right|exactly|perfect|great"
    r"|sounds good|looks good|that works|ship it|lgtm)[?!.]?$",
    re.IGNORECASE,
)
_TIER_TO_DEPTH: dict[str, str] = {
    "elite": DEPTH_ELITE,
    "deep": DEPTH_DEEP,
    "analytical": DEPTH_ANALYTICAL,
    "simple": DEPTH_SIMPLE,
}


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

    if prior_tier and len(words) <= 4 and _ACK_RE.match(q.strip()):
        inherited = _TIER_TO_DEPTH.get(prior_tier)
        if inherited:
            return inherited, f"tier_inherit:{prior_tier}"

    # TRAJECTORY: 2+ consecutive reason turns = accumulating context state.
    # Guard: cheap follow-ups (short query starting with a clarification word)
    # do NOT qualify — they steer an existing thread rather than extend it.
    # Also guard single-character / bare-ack queries (y/n/ok) without a
    # prior_tier -- these should not escalate to elite on their own.
    if consecutive_reason_turns >= 2:
        is_followup = len(words) <= 12 and bool(_FOLLOWUP_START_RE.match(q.strip()))
        if not is_followup:
            is_followup = (
                len(words) <= _FOLLOWUP_TIGHT_MAX_WORDS
                and bool(_FOLLOWUP_TIGHT_RE.match(q.strip()))
            )
        is_bare_ack = len(words) <= 4 and bool(_ACK_RE.match(q.strip()))
        if not is_followup and not is_bare_ack:
            return DEPTH_ELITE, "trajectory_depth"

    # MULTI-CONSTRAINT: explicit reconciliation or conflicting requirements
    if _MULTI_CONSTRAINT_RE.search(q):
        return DEPTH_DEEP, "multi_constraint"

    # COMPLEX REFACTOR: rename/restructure + long query (likely cross-file)
    if _MULTI_ACTION_RE.search(q) and len(words) > 20:
        return DEPTH_DEEP, "complex_refactor"

    # RENAME: always cross-file when renaming a code object, regardless of query length
    if _RENAME_RE.search(q) and _RENAME_CODE_OBJ_RE.search(q):
        return DEPTH_DEEP, "complex_refactor"

    # LONG MULTI-CLAUSE: very long query with multiple joins
    if len(words) > 50:
        return DEPTH_DEEP, "complex_query"

    # ANALYTICAL: multi-step reasoning, constraint-solving, proof-like — grok-4.7
    # General signals (debug/trace/prove/etc) need a medium-length query (>15 words).
    # Security/hardening keywords (audit/harden/inspect/assess) fire at >5 words —
    # "audit the AppArmor profile for firefox" (6w) is already analytical work.
    # "review" and "examine" keep the >15 gate to avoid over-routing casual code reviews.
    if re.search(
        r'\b(audit|assess|inspect|harden)\b',
        q, re.IGNORECASE,
    ) and len(words) > 4:
        return DEPTH_ANALYTICAL, "analytical_reasoning"

    if len(words) > 15 and re.search(
        r'\b(debug|trace|prove|proof|logic|constraint|deduce|infer|verify|analyse|analyze'
        r'|step\.by\.step|walk\.through|explain\.why|reason\.through'
        r'|review|examine)\b',
        q, re.IGNORECASE,
    ):
        return DEPTH_ANALYTICAL, "analytical_reasoning"

    return DEPTH_SIMPLE, "reason_simple"
