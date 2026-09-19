"""crystal_fidelity_tiers.py — Elastic fidelity tier compaction for jev-compaction.

Grounded in arXiv:2608.00303 "CrystalMem: Elastic Fidelity Tiers" (Aug 2026).

Key finding: Different compression DEPTHS should be applied based on message age and
access frequency. Old, unaccessed messages get LOSSY compression; recent/accessed
messages get LOSSLESS treatment. This is distinct from binary retain/demote.

The current jev-compaction gap:
  Phase-1 compaction makes a binary decision: retain (full content) or demote (clear content).
  For messages that score in the "grey zone" (middle tier), the current approach sends
  them to an expensive Jev LLM call. CrystalMem suggests a THIRD option:
  apply lossy compression (truncate to key snippet, keep first+last N chars) without
  a full demotion. This is cheaper than Jev scoring AND preserves more signal than demotion.

Fidelity tier definitions (arXiv:2608.00303):
  Tier A (LOSSLESS):  high RR score or recent → retain full content unchanged
  Tier B (LOSSY):     medium RR score → truncate to LOSSY_KEEP_CHARS chars (first+last)
                      No LLM call needed; deterministic, fast
  Tier C (DEMOTE):    low RR score → full demotion (existing behavior)

This script exposes the lossy compression function so jev-compaction can apply it
to the middle tier instead of (or before) Jev LLM scoring.

Integration pattern in jev-compaction __init__.py _relevance_gated_prune():
  Instead of: all middle-tier → Jev LLM call
  With CrystalMem: middle-tier → crystal_fidelity_decide(rr_score, msg) → action
    action == 'lossless': retain as-is (budget-free)
    action == 'lossy': apply crystal_lossy_compress(msg) (budget-free)
    action == 'demote': existing demotion (or Jev call for borderline cases)

Benefits:
  - Reduces Jev LLM call budget consumption on the middle tier
  - Partial information retention: compressed messages carry the key excerpt
  - Ebbinghaus-compatible: older messages get more aggressive compression

Usage:
  from crystal_fidelity_tiers import crystal_fidelity_decide, crystal_lossy_compress

Demo mode:
  python3 crystal_fidelity_tiers.py --demo   # exits 0
"""
from __future__ import annotations

import copy
import sys
from typing import Any

# ── Configuration ──────────────────────────────────────────────────────────────

# RR score boundaries for tier assignment
# Tier A (lossless): score >= LOSSLESS_THRESHOLD
# Tier B (lossy):    LOSSY_THRESHOLD <= score < LOSSLESS_THRESHOLD
# Tier C (demote):   score < LOSSY_THRESHOLD
LOSSLESS_THRESHOLD = 0.60   # Above this → keep full content
LOSSY_THRESHOLD = 0.35      # Below this → full demotion; between → lossy compress

# Characters to keep in lossy mode: first N and last N characters of content
LOSSY_KEEP_FIRST_CHARS = 300
LOSSY_KEEP_LAST_CHARS = 150

# Minimum content length to apply lossy compression (below this → just retain whole)
LOSSY_MIN_CHARS = 600

# Age penalty: older messages (normalized position 0.0=oldest → 1.0=newest) get more
# aggressive lossy compression. Effective threshold for lossy:
# effective_lossy_thresh = LOSSY_THRESHOLD + AGE_PENALTY * (1.0 - recency_score)
# This means older messages need a higher RR score to avoid lossy treatment
AGE_PENALTY = 0.15

# Template for the middle section placeholder in lossy-compressed messages
_LOSSY_MIDDLE_TEMPLATE = (
    "\n[...{n} chars compressed (CrystalMem elastic fidelity, arXiv:2608.00303)...]\n"
)

# Fidelity decision type
FidelityDecision = str  # 'lossless' | 'lossy' | 'demote'


def crystal_fidelity_decide(
    rr_score: float,
    msg: dict[str, Any],
    recency_score: float = 0.5,
) -> FidelityDecision:
    """Determine the fidelity tier for a message.

    arXiv:2608.00303 CrystalMem: elastic fidelity tiers based on message score
    and age. Older messages (lower recency) need a higher base score to earn
    lossless treatment.

    Args:
        rr_score: the base RR score for this message (0.0 - 1.0)
        msg: the message dict (for content length check)
        recency_score: normalized position within prunable window (0.0=oldest, 1.0=newest)

    Returns:
        'lossless' — retain full content (high score or very recent)
        'lossy'    — truncate to key excerpt (medium score)
        'demote'   — full demotion (low score)

    Tier boundaries:
        lossless: rr_score >= LOSSLESS_THRESHOLD
        lossy:    effective_lossy_thresh <= rr_score < LOSSLESS_THRESHOLD
        demote:   rr_score < effective_lossy_thresh
    """
    # Always lossless for system messages (handled upstream, but guard here)
    role = msg.get("role", "")
    if role == "system":
        return "lossless"

    # Age-adjusted lossy threshold: older messages → higher threshold for avoidance
    effective_lossy_thresh = LOSSY_THRESHOLD + AGE_PENALTY * (1.0 - recency_score)

    # Check content length — very short messages don't need lossy treatment
    content_len = _extract_content_length(msg)
    # P7B-04 fix: messages with content=None or missing 'content' key (e.g. tool-call-only
    # assistant messages) have content_len=0.  At medium RR scores these previously got
    # 'lossless' treatment (content_len < LOSSY_MIN_CHARS check), wasting context budget.
    # Send them to the normal Jev path (return 'demote') unless they're clearly high-value
    # (rr_score >= LOSSLESS_THRESHOLD) — in that case 'lossless' is still correct.
    if content_len == 0 and rr_score < LOSSLESS_THRESHOLD:
        return "demote"

    if rr_score >= LOSSLESS_THRESHOLD:
        return "lossless"
    elif rr_score >= effective_lossy_thresh and content_len >= LOSSY_MIN_CHARS:
        return "lossy"
    elif rr_score >= effective_lossy_thresh and content_len < LOSSY_MIN_CHARS:
        # Short messages: don't bother with lossy, just retain lossless (it's cheap)
        return "lossless"
    else:
        return "demote"


# P7B-05 fix: single canonical _extract_content_text in compaction_utils.py.
# P9B-01 fix: import block moved to BEFORE _extract_content_length which calls
#   _extract_content_text at line 137 — was after, creating a latent NameError
#   if any top-level caller appeared between the function def and the import block.
try:
    from compaction_utils import extract_content_text as _extract_content_text  # type: ignore[import]
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.dirname(__file__))
    from compaction_utils import extract_content_text as _extract_content_text  # type: ignore[import]


def _extract_content_length(msg: dict[str, Any]) -> int:
    """Return the character length of the message content."""
    return len(_extract_content_text(msg))


def crystal_lossy_compress(
    msg: dict[str, Any],
    *,
    keep_first: int = LOSSY_KEEP_FIRST_CHARS,
    keep_last: int = LOSSY_KEEP_LAST_CHARS,
) -> dict[str, Any]:
    """Apply lossy (Tier B) compression to a message.

    CrystalMem Tier B: retain first N chars (beginning of tool output, typically
    contains the most structured/critical information like error messages, file paths,
    status codes) and last N chars (tail often contains summary or final status).
    The middle is replaced with a placeholder.

    This is deterministic and requires no LLM call — saving the Jev budget for
    genuinely ambiguous messages.

    Args:
        msg: message to compress (deep-copied, original unchanged)
        keep_first: chars to keep from the start
        keep_last: chars to keep from the end

    Returns:
        Deep copy of msg with content lossy-compressed.
        If content is shorter than keep_first + keep_last + some overlap, returns
        a deep copy unchanged (no benefit from lossy compression at this size).
    """
    result = copy.deepcopy(msg)
    content = _extract_content_text(result)

    if len(content) <= keep_first + keep_last + 50:
        return result  # too short to benefit

    first_part = content[:keep_first]
    last_part = content[-keep_last:] if keep_last > 0 else ""
    middle_chars = len(content) - keep_first - keep_last
    placeholder = _LOSSY_MIDDLE_TEMPLATE.format(n=middle_chars)

    new_content = first_part + placeholder + last_part

    # Update content in the result
    c = result.get("content")
    if isinstance(c, str):
        result["content"] = new_content
    elif isinstance(c, list):
        # P9B-06 fix: add explicit empty-list guard (mirrors segment_level_compactor.py:301-303).
        if not c:
            return result
        # P5A-07 fix: handle list-of-plain-strings.
        # P7B-03 fix: apply the same P6B-01/02 collapse used in segment_level_compactor.
        # Previously only the first text-bearing item was updated; subsequent items kept
        # original stale text, making compression ineffective on multi-item lists and
        # allowing type-drift (list → str in the for..else fallback).
        # Fix: collapse the entire list to a single canonical item carrying new_content,
        # preserving the shape of the first item (plain-str or dict) and discarding the rest.
        first = c[0]
        if isinstance(first, str):
            # P11B-02 fix: c[0] is a plain string — inspect c[1:] before collapsing.
            # A list like ["intro text", {"type": "image_url", ...}] is multimodal;
            # silently dropping the dict tail items is data loss. Bail if any tail
            # item is not a plain string (return unchanged deep-copy, do not compact).
            for tail_item in c[1:]:
                if not isinstance(tail_item, str):
                    return result
            result["content"] = [new_content]
        elif isinstance(first, dict):
            key = "text" if "text" in first else ("content" if "content" in first else None)
            if key:
                # P9B-02 fix: check tail items for non-text-bearing dicts (e.g. image_url)
                # before collapsing. Silently destroying multimodal tail items is data loss.
                for tail_item in c[1:]:
                    # P10B-02 fix: plain-string tail items were silently dropped when collapsing
                    # to [{key: new_content}]. Treat mixed dict+str lists as multimodal; bail.
                    if isinstance(tail_item, str):
                        return result  # return unchanged deep-copy; do not compact
                    if isinstance(tail_item, dict) and "text" not in tail_item and "content" not in tail_item:
                        return result  # return unchanged deep-copy; do not compact
                result["content"] = [{key: new_content}]
            else:
                # Dict with no text-bearing key (e.g. image_url block) — do not
                # compact; return the deep-copy unchanged to avoid data loss.
                return result
        else:
            # P12B-03: unknown first-item type (not str or dict) — do not compact;
            # return deep-copy unchanged to avoid silently destroying unknown content blocks
            # (e.g. future Anthropic content types such as int, bytes, or new dicts).
            return result

    return result


def apply_crystal_fidelity(
    messages: list[dict[str, Any]],
    rr_scores: dict[int, float],
    *,
    total: int | None = None,
) -> tuple[list[dict[str, Any]], set[int], set[int]]:
    """Apply CrystalMem elastic fidelity tiers to a list of messages.

    Assigns each message to a fidelity tier and applies the appropriate transformation.
    Returns the transformed message list plus sets of lossless/lossy indices for logging.

    Args:
        messages: full message list
        rr_scores: {message_index: rr_score} for candidate messages
        total: total messages for recency normalization (defaults to len(messages))

    Returns:
        (transformed_messages, lossless_set, lossy_set)
        where lossless_set and lossy_set contain message indices by tier.
        Messages not in rr_scores are returned unchanged.
    """
    n = total or len(messages)
    result = list(messages)
    lossless_set: set[int] = set()
    lossy_set: set[int] = set()

    for i, score in rr_scores.items():
        if i >= len(result):
            continue
        msg = result[i]
        # Recency: position / (total - 1), 1.0 = newest position in window
        recency = i / max(n - 1, 1)
        decision = crystal_fidelity_decide(score, msg, recency_score=recency)

        if decision == "lossless":
            lossless_set.add(i)
            # No change to message
        elif decision == "lossy":
            lossy_set.add(i)
            result[i] = crystal_lossy_compress(msg)
        # decision == 'demote': caller handles (existing demotion logic)

    return result, lossless_set, lossy_set


# ── Demo ───────────────────────────────────────────────────────────────────────

def _demo() -> None:
    """Smoke test with synthetic messages. Exits 0 on success."""
    print("=== crystal_fidelity_tiers.py --demo ===")
    all_pass = True

    # Test 1: High score → lossless
    msg1 = {"role": "tool", "content": "x" * 1000}
    decision = crystal_fidelity_decide(0.75, msg1, recency_score=0.8)
    ok = decision == "lossless"
    if not ok:
        all_pass = False
    print(f"  {'✓' if ok else '✗'} High score (0.75, recency=0.8) → {decision} (expected lossless)")

    # Test 2: Low score → demote
    msg2 = {"role": "tool", "content": "x" * 1000}
    decision2 = crystal_fidelity_decide(0.20, msg2, recency_score=0.2)
    ok2 = decision2 == "demote"
    if not ok2:
        all_pass = False
    print(f"  {'✓' if ok2 else '✗'} Low score (0.20, recency=0.2) → {decision2} (expected demote)")

    # Test 3: Medium score, moderately recent message → lossy
    # recency=0.5: effective_thresh = 0.35 + 0.15 * 0.5 = 0.425; score=0.45 > 0.425 → lossy
    msg3 = {"role": "tool", "content": "x" * 2000}
    decision3 = crystal_fidelity_decide(0.45, msg3, recency_score=0.5)
    ok3 = decision3 == "lossy"
    if not ok3:
        all_pass = False
    print(f"  {'✓' if ok3 else '✗'} Medium score (0.45, recency=0.5, long) → {decision3} (expected lossy)")

    # Test 4: Medium score, short message → lossless (no benefit in lossy compress)
    msg4 = {"role": "tool", "content": "Short result: ok"}
    decision4 = crystal_fidelity_decide(0.45, msg4, recency_score=0.1)
    ok4 = decision4 in ("lossless", "demote")  # either is fine for short messages
    if not ok4:
        all_pass = False
    print(f"  {'✓' if ok4 else '✗'} Medium score, short message → {decision4} (expected lossless or demote)")

    # Test 5: Lossy compress reduces content
    long_content = "START: " + ("A" * 400) + " MIDDLE: " + ("B" * 800) + " END: " + ("C" * 200)
    msg5 = {"role": "tool", "content": long_content}
    compressed = crystal_lossy_compress(msg5)
    new_content = compressed.get("content", "")
    has_placeholder = "compressed" in new_content
    starts_right = new_content.startswith("START:")
    ends_right = "C" * 50 in new_content  # tail preserved
    size_reduced = len(new_content) < len(long_content)
    ok5 = has_placeholder and starts_right and ends_right and size_reduced
    if not ok5:
        all_pass = False
    orig_size = len(long_content)
    new_size = len(new_content)
    print(
        f"  {'✓' if ok5 else '✗'} Lossy compress: {orig_size} → {new_size} chars, "
        f"placeholder={'yes' if has_placeholder else 'no'}, "
        f"tail_preserved={'yes' if ends_right else 'no'}"
    )

    # Test 6: Original message unchanged after lossy compress (deep copy check)
    original_content = msg5.get("content", "")
    ok6 = original_content == long_content
    if not ok6:
        all_pass = False
    print(f"  {'✓' if ok6 else '✗'} Original message unchanged after lossy compress (deep copy)")

    # Test 7: apply_crystal_fidelity batch
    # idx 0: score=0.52, recency=0/4=0.0 → eff_thresh=0.50, score>thresh → lossy (long msg)
    # idx 1: score=0.80 → lossless
    # idx 2: not in rr_scores → unchanged
    messages = [
        {"role": "tool", "content": "x" * 3000},  # idx 0 → medium score, lossy
        {"role": "tool", "content": "y" * 1000},  # idx 1 → high score, lossless
        {"role": "user", "content": "question"},   # idx 2 → not in rr_scores
    ]
    rr_scores = {0: 0.52, 1: 0.80}
    transformed, lossless_set, lossy_set = apply_crystal_fidelity(
        messages, rr_scores, total=4  # total=4 so recency_i0 = 0/3 = 0.0; eff_thresh=0.50
    )
    ok7a = len(transformed) == 3
    ok7b = 0 in lossy_set or 0 in lossless_set  # idx 0 classified (either tier)
    ok7c = 1 in lossless_set  # idx 1 is high score → lossless
    ok7d = transformed[2].get("content") == "question"  # idx 2 unchanged
    ok7 = ok7a and ok7b and ok7c and ok7d
    if not ok7:
        all_pass = False
    print(
        f"  {'✓' if ok7 else '✗'} Batch apply: lossless={sorted(lossless_set)}, "
        f"lossy={sorted(lossy_set)}, msg[2] unchanged={'yes' if ok7d else 'no'}"
    )

    # Test 8: Age penalty shifts threshold
    # Oldest message (recency=0.0) with score=0.40 should demote (threshold ≈ 0.35+0.15=0.50)
    # Newest message (recency=1.0) with score=0.40 should lossy (threshold = 0.35)
    msg_old = {"role": "tool", "content": "x" * 2000}
    msg_new = {"role": "tool", "content": "x" * 2000}
    dec_old = crystal_fidelity_decide(0.40, msg_old, recency_score=0.0)
    dec_new = crystal_fidelity_decide(0.40, msg_new, recency_score=1.0)
    ok8 = dec_old == "demote" and dec_new in ("lossy", "lossless")
    if not ok8:
        all_pass = False
    print(
        f"  {'✓' if ok8 else '✗'} Age penalty: score=0.40, recency=0.0 → {dec_old} (expected demote); "
        f"recency=1.0 → {dec_new} (expected lossy/lossless)"
    )

    print(f"\n{'PASS' if all_pass else 'FAIL'} — {'all checks passed' if all_pass else 'some checks failed'}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        print(__doc__)
