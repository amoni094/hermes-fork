"""cot_phase_scorer.py — CoT reasoning-chain phase detector for jev-compaction.

Grounded in arXiv:2608.21265 "Memory Augmentation Unlocks Efficient Chain-of-Thought
Reasoning" (Aug 2026). Key finding: storing intermediate CoT conclusions externally
achieves 60% token cost reduction at equivalent accuracy vs keeping full chain in context.

Application to jev-compaction:
  Assistant messages that contain INTERMEDIATE reasoning chains (scratchpad content)
  should be scored more aggressively for demotion than assistant messages that contain
  FINAL conclusions or direct answers.

Heuristic detection (no LLM call required):
  A message is classified as 'cot_intermediate' if:
    - role == 'assistant'
    - Contains multiple reasoning phrases (Let me think / Let's analyze / Step 1: / etc.)
    - Content length > COT_MIN_CHARS (typically 500)
    - Does NOT end with a direct answer pattern (answer: / result: / conclusion:)
  Otherwise it is classified as 'cot_conclusion' or 'direct'.

Score adjustment:
  cot_intermediate: RR score multiplied by COT_DEMOTE_FACTOR (default 0.65)
    → pushes intermediate reasoning into the bottom tier more aggressively
  cot_conclusion: no adjustment (kept as-is)

Usage:
  from cot_phase_scorer import cot_adjust_rr_score, classify_cot_phase
  adjusted = cot_adjust_rr_score(msg, base_rr_score)

Demo mode:
  python3 cot_phase_scorer.py --demo   # exits 0

Integration with jev-compaction __init__.py:
  In _rr_score(), after computing the base score, call:
    from cot_phase_scorer import cot_adjust_rr_score
    score = cot_adjust_rr_score(msg, score)
"""
from __future__ import annotations

import math
import re
import sys
from typing import Any

# ── Configuration ──────────────────────────────────────────────────────────────

# Minimum character length to consider a message as a potential CoT chain
COT_MIN_CHARS = 400

# Factor applied to RR score for intermediate CoT messages (< 1.0 = more aggressive demotion)
COT_DEMOTE_FACTOR = 0.65

# Phrases that signal intermediate reasoning (at least this many must appear)
_COT_PHRASE_MIN = 2

# Phrases indicating intermediate reasoning steps
_COT_INTERMEDIATE_PHRASES: list[str] = [
    r"\blet me think\b",
    r"\blet me analyze\b",
    r"\blet me consider\b",
    r"\blet's think\b",
    r"\blet's analyze\b",
    r"\bfirst[,:]",
    r"\bstep \d+[:\.]",
    r"\bstep \d+\b",
    r"\b\d+\.\s+\w",         # numbered list steps
    r"\bon the one hand\b",
    r"\bon the other hand\b",
    r"\bhowever,",
    r"\bfurthermore,",
    r"\bto summarize\b",
    r"\btherefore,",
    r"\bthus,",
    r"\bconsidering\b",
    r"\breasonin[g]\b",
    r"\banalysis:\b",
    r"\bthinking:\b",
    r"\bscratchpad\b",
    r"\bchain.of.thought\b",
    r"\bcoT\b",
    r"^\s*<thinking>",       # explicit thinking blocks
    r"</thinking>",
]

# Patterns that signal a FINAL conclusion (presence overrides intermediate classification)
_COT_CONCLUSION_PATTERNS: list[str] = [
    r"\bfinal answer[:\.]",
    r"\bfinal answer is\b",      # F04 fix: catches "the final answer is: X"
    r"\bthe final answer\b",     # F04 fix: catches "the final answer"
    r"\bin summary[,:]",
    r"\bin conclusion[,:]",
    r"\bto conclude[,:]",
    r"\bthe answer is\b",
    r"\bmy answer is\b",
    r"\bthe result is\b",
    r"\bhere is the\b.{0,30}(result|answer|output|summary)",
    r"^(done|complete|finished)[\.!]\s*$",  # P4A-10: require whole-line match; re.MULTILINE ^ matches any line start
]

_COT_INTERMEDIATE_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in _COT_INTERMEDIATE_PHRASES]
# P4A-10 fix: compile conclusion patterns with MULTILINE so ^ and $ match line boundaries,
# but require the pattern to occupy a full line (added \s*$ anchor) to avoid false
# positives from mid-message "done." lines inside long reasoning chains.
_COT_CONCLUSION_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in _COT_CONCLUSION_PATTERNS]


# P7B-05 fix: single canonical implementation in compaction_utils.py.
try:
    from compaction_utils import extract_content_text as _extract_content_text  # type: ignore[import]
except ImportError:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.dirname(__file__))
    from compaction_utils import extract_content_text as _extract_content_text  # type: ignore[import]


def classify_cot_phase(msg: dict[str, Any]) -> str:
    """Classify an assistant message as 'cot_intermediate', 'cot_conclusion', or 'direct'.

    Returns:
        'cot_intermediate'  — long assistant message dominated by reasoning steps
        'cot_conclusion'    — message ends with a final answer marker
        'direct'            — short message or tool call (no adjustment)

    Only assistant messages can be 'cot_intermediate' or 'cot_conclusion'.
    All other roles return 'direct'.

    arXiv:2608.21265: intermediate reasoning conclusions written to an external store;
    the key insight is that the PROCESS of reasoning should not occupy the context
    window permanently — only the CONCLUSION needs to be retained.
    """
    if msg.get("role") != "assistant":
        return "direct"

    content = _extract_content_text(msg)

    # P11B-06 fix: apply length gate BEFORE conclusion check. A 4-word response like
    # "The answer is 42." matches broad conclusion patterns (_COT_CONCLUSION_RE includes
    # r"\bthe answer is\b") but is a direct reply, not a CoT conclusion. Short messages
    # should always be classified as 'direct' regardless of pattern matches. The comment
    # below (overrides intermediate, even in shorter text) was the pre-fix rationale and
    # is now removed — a genuine CoT conclusion is longer than COT_MIN_CHARS by definition.
    if len(content) < COT_MIN_CHARS:
        return "direct"

    # Check for conclusion markers (only reached when content >= COT_MIN_CHARS)
    for pattern in _COT_CONCLUSION_RE:
        if pattern.search(content):
            return "cot_conclusion"

    # Count intermediate reasoning phrase matches
    match_count = sum(1 for p in _COT_INTERMEDIATE_RE if p.search(content))
    if match_count >= _COT_PHRASE_MIN:
        return "cot_intermediate"

    # Additional structural heuristic: multiple paragraphs with logical connectives
    # A pure-CoT message tends to have > 5 paragraphs and >20% connective words
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if len(paragraphs) >= 4:
        # Count connective markers
        connectives = re.findall(
            r"\b(because|since|therefore|thus|hence|so|but|however|although|whereas|while)\b",
            content, re.IGNORECASE
        )
        words = len(content.split())
        connective_density = len(connectives) / max(words, 1)
        if connective_density > 0.025:  # >2.5% connective density
            return "cot_intermediate"

    return "direct"


def cot_adjust_rr_score(msg: dict[str, Any], base_rr_score: float) -> float:
    """Apply CoT phase adjustment to an RR score.

    arXiv:2608.21265 application: intermediate reasoning steps occupy context
    disproportionately to their future utility. Applying COT_DEMOTE_FACTOR pushes
    them into the bottom RR tier more aggressively, freeing budget for tool results
    and final conclusion messages.

    Args:
        msg: the message dict (role, content, ...)
        base_rr_score: the base RR score from _rr_score()

    Returns:
        Adjusted score: base_rr_score * COT_DEMOTE_FACTOR for cot_intermediate,
        base_rr_score unchanged for all other phases.
    """
    phase = classify_cot_phase(msg)
    if phase == "cot_intermediate":
        return base_rr_score * COT_DEMOTE_FACTOR
    return base_rr_score


# ── Demo ───────────────────────────────────────────────────────────────────────

def _demo() -> None:
    """Smoke test with synthetic messages. Exits 0 on success."""
    cases: list[tuple[dict[str, Any], str, str]] = [
        (
            {"role": "user", "content": "What is 2+2?"},
            "direct",
            "user messages are always direct",
        ),
        (
            {"role": "assistant", "content": "4"},
            "direct",
            "short assistant message is direct",
        ),
        (
            {
                "role": "assistant",
                "content": (
                    "Let me think about this step by step.\n\n"
                    "Step 1: First, I need to understand the problem.\n"
                    "The task requires analyzing multiple dimensions.\n\n"
                    "Step 2: Consider the constraints.\n"
                    "However, this is complicated by the fact that there are multiple options.\n\n"
                    "Step 3: Therefore, I will work through each case systematically.\n"
                    "Furthermore, this requires careful analysis because the problem has many parts.\n\n"
                    "Thus we proceed through the logical chain of reasoning to arrive at our conclusion.\n"
                    "On the one hand, option A looks good. On the other hand, option B also works.\n"
                    "Considering all of the above, the analysis suggests we should proceed carefully.\n"
                ),
            },
            "cot_intermediate",
            "long reasoning chain with multiple step markers",
        ),
        (
            {
                "role": "assistant",
                "content": (
                    "Let me think about this carefully.\n"
                    "Step 1: analyze the inputs in detail.\n"
                    "Step 2: compute intermediate values using the formula.\n"
                    "Step 3: synthesize the results by combining all findings.\n"
                    "Step 4: validate correctness against known edge cases.\n"
                    "Step 5: confirm consistency with the original constraints.\n"
                    "Step 6: review all prior steps to ensure nothing was missed.\n"
                    "After considering all options, in conclusion: the final answer is 42.\n"
                ),
            },
            "cot_conclusion",
            "has both reasoning AND explicit conclusion marker → conclusion wins (P12B-02: ≥400 chars)",
        ),
        (
            {
                "role": "tool",
                "content": "Step 1: I analyzed the data. Therefore, result: success.",
            },
            "direct",
            "tool role is always direct regardless of content",
        ),
    ]

    print("=== cot_phase_scorer.py --demo ===")
    all_pass = True
    for msg, expected_phase, description in cases:
        phase = classify_cot_phase(msg)
        status = "✓" if phase == expected_phase else "✗"
        if phase != expected_phase:
            all_pass = False
        print(f"  {status} [{phase:16s}] expected=[{expected_phase:16s}] {description}")

    # Test score adjustment
    intermediate_msg = {
        "role": "assistant",
        "content": (
            "Let me think step by step. First, analyze the problem. "
            "Step 1: check constraints. Step 2: evaluate options. "
            "Therefore, we have multiple pathways. However, the best approach requires "
            "careful consideration. Furthermore, the analysis reveals that option A "
            "dominates. Thus the conclusion follows from the reasoning chain above. "
            "On the other hand, we should also consider edge cases. Because of this, "
            "the solution is nuanced and requires additional steps to verify.\n\n"
            "Moving to the implementation phase, we note several key concerns.\n"
            "Considering all of the above, this is a complex multi-step reasoning process."
        ),
    }
    base = 0.75
    adjusted = cot_adjust_rr_score(intermediate_msg, base)
    expected_adjusted = base * COT_DEMOTE_FACTOR
    adj_ok = abs(adjusted - expected_adjusted) < 1e-9
    status = "✓" if adj_ok else "✗"
    if not adj_ok:
        all_pass = False
    print(f"  {status} Score adjustment: {base:.2f} → {adjusted:.3f} (expected {expected_adjusted:.3f})")

    direct_msg = {"role": "tool", "content": "result: ok"}
    adj2 = cot_adjust_rr_score(direct_msg, base)
    status2 = "✓" if adj2 == base else "✗"
    if adj2 != base:
        all_pass = False
    print(f"  {status2} Direct message score unchanged: {adj2} == {base}")

    print(f"\n{'PASS' if all_pass else 'FAIL'} — {'all checks passed' if all_pass else 'some checks failed'}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        print(__doc__)
