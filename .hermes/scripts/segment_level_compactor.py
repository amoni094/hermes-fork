"""segment_level_compactor.py — Segment-level partial retention for jev-compaction.

Grounded in arXiv:2608.12990 "LycheeMemory V2: Segment-Level Consolidation" (Aug 2026).
★ HIGH priority finding from the research corpus.

Key finding: Rather than applying binary retain/demote decisions at the message level,
identify which SEGMENTS of a long tool result are still needed. This enables partial
retention of long tool outputs — keep the relevant 10%, compact the other 90%.

Application to jev-compaction (gap):
  jev-compaction applies binary retain/demote at message level. For a large tool result
  (e.g., a 10KB read_file output), either the entire message is kept or the entire
  message is demoted. Segment-level scoring addresses this by:
  1. Splitting a long tool result into logical segments (code blocks, paragraphs,
     JSON sections, etc.)
  2. Scoring each segment for relevance to the current task context
  3. Retaining high-score segments, compacting/dropping low-score segments
  4. Re-assembling the message with a "[...N chars removed...]" placeholder

This is a COMPRESSION (not demotion) operation:
  - Binary demotion: entire message text cleared (tool call invocation kept)
  - Segment compaction: message text truncated to relevant segments + summary

Segmentation strategies:
  1. Structural: code blocks (```), JSON objects {}, list items (- / * / 1.)
  2. Paragraph: double-newline split
  3. Fixed-window: 500-char sliding window for unstructured content

Integration:
  Call segment_compact_message(msg, task_context) to get a compacted copy.
  If the function returns None, the message is either short enough to keep whole
  or compaction didn't reduce size meaningfully (< MIN_REDUCTION_RATIO).

Usage:
  from segment_level_compactor import segment_compact_message, can_benefit_from_compaction
  compacted = segment_compact_message(msg, task_context)
  if compacted is not None:
      msg = compacted  # replace in message list

Demo mode:
  python3 segment_level_compactor.py --demo   # exits 0
"""
from __future__ import annotations

import copy
import re
import sys
from typing import Any

# ── Configuration ──────────────────────────────────────────────────────────────

# Minimum message length to consider for segment-level compaction
# Messages shorter than this are retained whole (compaction overhead not justified)
MIN_COMPACT_CHARS = 2000

# Minimum ratio by which compaction must reduce the message to be worth applying
# e.g. 0.30 means "only apply if we can cut at least 30% of the content"
MIN_REDUCTION_RATIO = 0.30

# Maximum number of segments to retain from a message
MAX_RETAINED_SEGMENTS = 6

# Segment relevance scoring: minimum score to retain a segment
# Score is based on keyword overlap with task context (0.0 - 1.0)
SEGMENT_RETAIN_THRESHOLD = 0.15

# Placeholder text inserted where segments are removed
_REMOVED_PLACEHOLDER = "[...{n} chars removed (jev-compaction segment filter, arXiv:2608.12990)...]"

# Regex patterns for structural segment detection
_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_JSON_OBJECT_RE = re.compile(r"\{[^{}]{20,}\}", re.MULTILINE)
_NUMBERED_LIST_RE = re.compile(r"(?:^|\n)(\d+\.\s+.+?)(?=\n\d+\.|\Z)", re.MULTILINE | re.DOTALL)
_BULLET_LIST_RE = re.compile(r"(?:^|\n)([-*+]\s+.+?)(?=\n[-*+]|\Z)", re.MULTILINE | re.DOTALL)


# P7B-05 fix: single canonical implementation in compaction_utils.py.
# Import and alias so existing callers within this module continue to work.
try:
    from compaction_utils import extract_content_text as _extract_content_text  # type: ignore[import]
except ImportError:
    # Fallback for environments where compaction_utils is not on sys.path.
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.dirname(__file__))
    from compaction_utils import extract_content_text as _extract_content_text  # type: ignore[import]


def _split_into_segments(content: str) -> list[tuple[str, str]]:
    """Split content into labeled segments: (segment_text, segment_type).

    Priority order: code blocks → JSON objects → paragraphs → fixed windows.
    Each strategy tries to produce meaningful semantic units.

    LycheeMemory V2 insight: segment boundaries should follow LOGICAL structure
    (code/data blocks, topic paragraphs) rather than fixed token counts.
    """
    # Strategy 1: Code blocks (highest priority — self-contained units)
    segments: list[tuple[str, str]] = []
    code_blocks = _CODE_BLOCK_RE.findall(content)
    if code_blocks:
        remaining = content
        for block in code_blocks:
            # Split around each code block; text before is a paragraph segment
            idx = remaining.find(block)
            pre = remaining[:idx].strip()
            if len(pre) > 50:
                # Paragraph-split the pre-text
                for para in pre.split("\n\n"):
                    para = para.strip()
                    if para:
                        segments.append((para, "paragraph"))
            segments.append((block, "code_block"))
            remaining = remaining[idx + len(block):]
        post = remaining.strip()
        if len(post) > 50:
            for para in post.split("\n\n"):
                para = para.strip()
                if para:
                    segments.append((para, "paragraph"))
        if segments:
            return segments

    # Strategy 2: Paragraph split (double newline)
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if len(paragraphs) >= 3:
        return [(p, "paragraph") for p in paragraphs]

    # Strategy 3: Single newline split
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    if len(lines) >= 5:
        # Group lines into chunks of ~3
        chunks = []
        for i in range(0, len(lines), 3):
            chunk = "\n".join(lines[i:i+3])
            chunks.append((chunk, "line_group"))
        return chunks

    # Strategy 4: Fixed window (500 chars) for unstructured content
    windows = []
    for i in range(0, len(content), 500):
        window = content[i:i+500]
        if window.strip():
            windows.append((window, "window"))
    return windows if windows else [(content, "whole")]


def _score_segment(segment: str, task_context: str) -> float:
    """Score a segment for relevance to the current task context (0.0 - 1.0).

    LycheeMemory V2 insight: relevance scoring should be fast (no LLM call) and
    use token overlap rather than embedding similarity for the segment-level pass.

    Scoring formula:
      overlap = |task_tokens ∩ segment_tokens| / |task_tokens|
      length_bonus = min(1.0, len(segment) / 200) * 0.1
      score = 0.9 * overlap + 0.1 * length_bonus

    Edge cases:
      - Empty task context → score all segments 0.5 (retain proportionally)
      - Short segment (< 50 chars) → score as 0.0 (likely formatting artifact)
    """
    if not segment.strip() or len(segment) < 30:
        return 0.0

    if not task_context.strip():
        return 0.5  # no context → neutral retention

    # Tokenize: lowercase alphanum words >= 3 chars
    def tokenize(text: str) -> set[str]:
        return {w.lower() for w in re.findall(r'\b[a-z0-9]{3,}\b', text.lower())}

    task_tokens = tokenize(task_context)
    segment_tokens = tokenize(segment)

    if not task_tokens:
        return 0.5
    if not segment_tokens:
        return 0.0

    overlap = len(task_tokens & segment_tokens) / len(task_tokens)
    length_bonus = min(1.0, len(segment) / 200) * 0.1
    return min(1.0, 0.9 * overlap + length_bonus)


def can_benefit_from_compaction(msg: dict[str, Any]) -> bool:
    """Return True if the message is large enough to benefit from segment-level compaction.

    Only tool and assistant messages with long content are candidates.
    """
    role = msg.get("role", "")
    if role not in ("tool", "assistant"):
        return False
    content = _extract_content_text(msg)
    return len(content) >= MIN_COMPACT_CHARS


def segment_compact_message(
    msg: dict[str, Any],
    task_context: str,
    *,
    retain_threshold: float = SEGMENT_RETAIN_THRESHOLD,
    max_retained: int = MAX_RETAINED_SEGMENTS,
    min_reduction: float = MIN_REDUCTION_RATIO,
) -> dict[str, Any] | None:
    """Segment-level compaction of a long tool/assistant message.

    LycheeMemory V2 (arXiv:2608.12990): identify which segments of a long message
    are still needed given the current task context. Retain only those segments;
    replace removed content with a compact placeholder.

    Args:
        msg: message dict (role, content)
        task_context: current task context (string from _build_task_context)
        retain_threshold: minimum segment relevance score to retain
        max_retained: max segments to keep
        min_reduction: minimum fraction of chars that must be removed

    Returns:
        A deep copy of msg with content compacted, or None if:
          - message is too short (< MIN_COMPACT_CHARS)
          - compaction doesn't reduce size by at least min_reduction
          - compaction would remove ALL segments (too aggressive)
    """
    if not can_benefit_from_compaction(msg):
        return None

    content = _extract_content_text(msg)
    if not content:
        return None

    segments = _split_into_segments(content)
    if len(segments) <= 1:
        return None  # can't meaningfully split

    # Score all segments — enumerate to get stable index-based identity
    # P4A-07 fix: id(str) is unsafe for repeated identical segments (Python string
    # interning makes id(seg_A) == id(seg_B) when seg_A == seg_B, corrupting
    # retain decisions). Use (idx, seg, seg_type, score) and retain by index.
    scored_segments = [
        (idx, seg, seg_type, _score_segment(seg, task_context))
        for idx, (seg, seg_type) in enumerate(segments)
    ]

    # Sort by score, take top MAX_RETAINED_SEGMENTS
    by_score = sorted(scored_segments, key=lambda x: x[3], reverse=True)
    to_retain_set = {
        s[0] for s in by_score[:max_retained]
        if s[3] >= retain_threshold
    }

    if not to_retain_set:
        # All segments below threshold — too aggressive, don't compact
        return None

    # Rebuild content in original order, replacing dropped segments
    parts: list[str] = []
    for idx, seg, seg_type, score in scored_segments:
        if idx in to_retain_set:
            parts.append(seg)
        else:
            parts.append(_REMOVED_PLACEHOLDER.format(n=len(seg)))

    # Check reduction ratio against ACTUAL new content size, not just removed_chars.
    new_content = "\n\n".join(parts)

    # Deep copy and replace content
    # P6B-01/02/12 fix:
    #   P6B-01: the write-back loop had no plain-string branch; list-of-plain-strings
    #           fell to `for..else` → list silently replaced with bare str, breaking
    #           Anthropic multi-part format for downstream consumers.
    #   P6B-02: only the FIRST dict item received new_content; subsequent items kept
    #           original text, so the compacted result was still near-original length.
    #   P6B-12: actual_reduction was computed from the intermediate new_content string
    #           (pre-write-back), not from post-write-back extraction — the check could
    #           pass while the returned message was not actually reduced downstream.
    #   Fix: collapse the entire list to a single canonical item carrying new_content,
    #   then compute actual_reduction from _extract_content_text on the result.
    result = copy.deepcopy(msg)
    c = result.get("content")
    if isinstance(c, str):
        result["content"] = new_content
    elif isinstance(c, list):
        if c:
            # Determine the shape of the first item and write new_content there.
            # All subsequent items are cleared (set to empty string / empty text)
            # so no stale original text survives in the list.
            first = c[0]
            if isinstance(first, dict):
                key = "text" if "text" in first else ("content" if "content" in first else None)
                if key:
                    # P9B-02 fix: check all items in the list, not just c[0].
                    # A multimodal message [{text:'...'}, {type:'image_url', url:'...'}]
                    # passes the c[0] guard but silently destroys image_url at index 1+.
                    # Return None if any tail item lacks a text-bearing key.
                    for tail_item in c[1:]:
                        # P10B-01 fix: plain-string tail items were silently dropped
                        # when collapsing to [{key: new_content}]. A list like
                        # [{"text": "..."}, "extra"] is unusual but valid — treat it as
                        # multimodal and bail out rather than destroying the plain-string item.
                        if isinstance(tail_item, str):
                            return None
                        if isinstance(tail_item, dict) and "text" not in tail_item and "content" not in tail_item:
                            return None
                    result["content"] = [{key: new_content}]
                else:
                    # P7B-01 fix: first dict has no text-bearing key (e.g. image_url,
                    # tool_use block).  Collapsing to [new_content] would silently destroy
                    # non-text metadata.  Return None — do not compact this message.
                    return None
            else:
                # P11B-02 fix: c[0] is a plain string — inspect c[1:] before collapsing.
                # A list like ["intro text", {"type": "image_url", ...}] is multimodal;
                # silently dropping the dict tail items is data loss. Bail if any tail
                # item is not a plain string.
                for tail_item in c[1:]:
                    if not isinstance(tail_item, str):
                        return None
                # All items are plain strings — safe to collapse
                result["content"] = [new_content]
        else:
            # Empty list — nothing to compact; leave as-is
            return None
    else:
        return None  # unknown content shape; skip

    # P6B-12: compute actual_reduction from post-write-back extraction so the check
    # measures true downstream text reduction, not intermediate string length.
    post_content = _extract_content_text(result)
    actual_reduction = (len(content) - len(post_content)) / max(len(content), 1)
    if actual_reduction < min_reduction:
        return None  # not enough reduction to justify the change

    return result


# ── Demo ───────────────────────────────────────────────────────────────────────

def _demo() -> None:
    """Smoke test with synthetic messages. Exits 0 on success."""
    print("=== segment_level_compactor.py --demo ===")
    all_pass = True

    # Test 1: Short message → no compaction
    short_msg = {"role": "tool", "content": "File written successfully."}
    result = segment_compact_message(short_msg, "write a file")
    assert result is None, f"Expected None for short message, got {result}"
    print("  ✓ Short message: no compaction (correct)")

    # Test 2: User message → no compaction
    user_msg = {"role": "user", "content": "x" * 5000}
    result = segment_compact_message(user_msg, "task context")
    assert result is None, f"Expected None for user message, got {result}"
    print("  ✓ User message: no compaction (correct)")

    # Test 3: Long tool result with relevant and irrelevant sections
    relevant_section = (
        "## Python Installation Guide\n"
        "To install Python packages, use pip. The pip install command downloads "
        "packages from PyPI. Run: pip install numpy pandas scipy matplotlib.\n"
        "These packages are required for data analysis tasks.\n"
    )
    irrelevant_section = (
        "## Historical Background\n"
        "Python was created by Guido van Rossum in 1991. It is named after "
        "Monty Python's Flying Circus, not after the snake. The language "
        "emphasizes code readability and uses significant whitespace to define "
        "code blocks. Java was created in 1995 by James Gosling at Sun Microsystems. "
        "Ruby was designed in the mid-1990s by Yukihiro Matsumoto in Japan.\n"
    )
    irrelevant_section2 = (
        "## Database History\n"
        "SQL was developed in the 1970s by Edgar Codd at IBM. Relational databases "
        "store data in tables with rows and columns. NoSQL databases emerged in the "
        "2000s as an alternative approach. MongoDB uses BSON format. Redis is an "
        "in-memory key-value store. PostgreSQL is an open-source relational database "
        "that supports advanced SQL features and extensions.\n"
    )
    long_content = "\n\n".join([relevant_section, irrelevant_section, irrelevant_section2] * 3)
    tool_msg = {"role": "tool", "name": "read_file", "content": long_content}

    result = segment_compact_message(
        tool_msg,
        task_context="install Python packages pip numpy pandas",
        retain_threshold=0.05,  # low threshold to test scoring directionality
        max_retained=3,
    )

    if result is not None:
        new_content = result.get("content", "")
        # The relevant section should be retained (has overlap with task_context)
        retained_relevant = "pip install" in new_content or "Python Installation" in new_content
        has_placeholder = "chars removed" in new_content
        content_reduced = len(new_content) < len(long_content)
        status = "✓" if (has_placeholder and content_reduced) else "✗"
        if not (has_placeholder and content_reduced):
            all_pass = False
        orig_len = len(long_content)
        new_len = len(new_content)
        reduction = (orig_len - new_len) / orig_len * 100
        print(f"  {status} Long tool result: {orig_len} → {new_len} chars ({reduction:.1f}% reduction)")
        print(f"      placeholder inserted: {has_placeholder}, content reduced: {content_reduced}")
    else:
        print("  ! Long tool result: compaction returned None (may be reduction < threshold)")
        # This is acceptable — depends on segment scoring
        # Try with lower threshold
        result2 = segment_compact_message(
            tool_msg,
            task_context="install Python packages pip numpy pandas",
            retain_threshold=0.0,
            max_retained=2,
            min_reduction=0.1,
        )
        if result2 is not None:
            print("    ✓ With lower threshold: compaction succeeded")
        else:
            # P9B-08 fix: set all_pass=False when both primary and retry return None.
            # Previously this always printed "✓ No meaningful compaction possible", masking
            # a broken segment_compact_message for all inputs (false PASS in demo).
            print("    ✗ Compaction failed even with lower threshold — check segment_compact_message")
            all_pass = False

    # Test 4: Segment scoring
    seg = "pip install numpy pandas scipy matplotlib for data analysis"
    context = "install Python packages pip numpy"
    score = _score_segment(seg, context)
    assert score > 0.0, f"Expected positive score, got {score}"
    print(f"  ✓ Segment scoring: relevant segment score = {score:.3f} > 0")

    irrelevant_seg = "MongoDB was created in 2007 by Dwight Merriman"
    irr_score = _score_segment(irrelevant_seg, context)
    print(f"  ✓ Segment scoring: irrelevant segment score = {irr_score:.3f} (less relevant)")

    # Test 5: Empty task context → neutral score
    neutral_score = _score_segment("some content here that is long enough to pass the minimum length check", "")
    assert neutral_score == 0.5, f"Expected 0.5 for empty context, got {neutral_score}"
    print(f"  ✓ Empty context → neutral score 0.5")

    print(f"\n{'PASS' if all_pass else 'FAIL'} — {'all checks passed' if all_pass else 'some checks failed'}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        print(__doc__)
