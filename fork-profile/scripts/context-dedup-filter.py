"""Cross-subsystem context deduplication filter (Slepian-Wolf distributed coding).

Theory: Slepian & Wolf (1973) proved that two correlated sources X, Y encoded
independently can achieve the joint entropy H(X,Y) = H(X) + H(Y|X) without
encoder cooperation. The decoder receiving both can losslessly reconstruct both.

Applied to hermes-fork context injection:
  - Multiple injectors (skills, memory facts, user profile, ARCHITECTURE.md,
    tool results) each inject text independently into the context window.
  - If these texts are correlated (share bigrams, similar sentences), they
    waste context tokens on redundant content.
  - This filter computes pairwise bigram Jaccard between blocks from different
    subsystems and suppresses blocks that are dominated by already-included blocks.

The Slepian-Wolf insight: we don't need the injectors to coordinate — instead,
the filter plays the role of the joint decoder, achieving near-joint-entropy
compression after the fact.

Also applies Einstein & McDaniel (1990): prospective blocks (action reminders)
are NEVER suppressed regardless of overlap.

Usage:
  from context_dedup_filter import ContextDedupFilter
  filt = ContextDedupFilter(jaccard_threshold=0.6)
  kept, stats = filt.filter(blocks)  # blocks = list of {source, text, is_prospective?}

  OR CLI:
  python3 context-dedup-filter.py --self-test
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("context-dedup-filter")

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes" / "profiles" / "fork"))


# ---------------------------------------------------------------------------
# Text fingerprinting (same helpers as side-info-memory-filter for consistency)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_\-]{2,}", text.lower())


def _ngram_set(tokens: list[str], n: int = 2) -> set[str]:
    if len(tokens) < n:
        return set(tokens)
    return {" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}


def _jaccard(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _containment(block_ngrams: set, reference_ngrams: set) -> float:
    """How much of block is already covered by reference."""
    if not block_ngrams:
        return 0.0
    return len(block_ngrams & reference_ngrams) / len(block_ngrams)


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

class ContextDedupFilter:
    """Slepian-Wolf-inspired cross-block deduplication.

    Args:
        jaccard_threshold: Suppress a block if its Jaccard similarity to any
          already-kept block exceeds this threshold (default 0.6).
        containment_threshold: Suppress a block if its containment in the
          union of kept blocks exceeds this (default 0.75). Catches the case
          where one block is a strict subset of another.
        prioritise_sources: List of source names that get priority in greedy
          ordering (their blocks are evaluated first and are less likely to be
          suppressed). Default: ['user_profile', 'skills', 'memory'].
    """

    def __init__(
        self,
        jaccard_threshold: float = 0.6,
        containment_threshold: float = 0.75,
        prioritise_sources: list[str] | None = None,
    ):
        self.jaccard_threshold = jaccard_threshold
        self.containment_threshold = containment_threshold
        self.prioritise_sources = prioritise_sources or [
            "user_profile", "skills", "memory", "architecture"
        ]

    def _is_prospective(self, block: dict) -> bool:
        """Block is prospective if explicitly flagged or contains trigger phrases."""
        if block.get("is_prospective"):
            return True
        text = block.get("text", "").lower()
        triggers = ["remember to", "don't forget", "make sure to", "remind", "scheduled for"]
        return any(t in text for t in triggers)

    def _source_priority(self, block: dict) -> int:
        """Lower number = higher priority = evaluated first."""
        src = block.get("source", "")
        try:
            return self.prioritise_sources.index(src)
        except ValueError:
            return len(self.prioritise_sources)

    def filter(self, blocks: list[dict]) -> tuple[list[dict], dict]:
        """Filter blocks, returning (kept_blocks, stats).

        Each block dict must have:
          text: str — the content to inject
          source: str — which subsystem produced it (e.g. 'skills', 'memory')
          is_prospective: bool (optional) — never suppress if True

        Stats:
          total, kept, suppressed, prospective_override,
          total_chars_kept, total_chars_suppressed,
          avg_jaccard_suppressed, cross_source_pairs_checked
        """
        # Sort: prospective first, then by source priority, then by text length (longer = more info)
        ordered = sorted(
            blocks,
            key=lambda b: (
                0 if self._is_prospective(b) else 1,
                self._source_priority(b),
                -len(b.get("text", "")),
            )
        )

        kept: list[dict] = []
        suppressed: list[dict] = []
        prospective_override = 0
        jaccard_scores_suppressed: list[float] = []
        pairs_checked = 0

        # Union of ngrams for all kept blocks (grows as we keep blocks)
        kept_ngrams_union: set[str] = set()
        # Per-kept-block ngrams for Jaccard
        kept_ngrams_per: list[set[str]] = []

        for block in ordered:
            text = block.get("text", "")
            block_tokens = _tokenize(text)
            block_ngrams = _ngram_set(block_tokens, n=2)
            prospective = self._is_prospective(block)

            if not kept:
                # First block always kept
                kept.append(block)
                kept_ngrams_union |= block_ngrams
                kept_ngrams_per.append(block_ngrams)
                continue

            # Check Jaccard against each already-kept block
            max_jaccard = 0.0
            for kn in kept_ngrams_per:
                pairs_checked += 1
                j = _jaccard(block_ngrams, kn)
                if j > max_jaccard:
                    max_jaccard = j

            # Check containment in union of kept
            containment = _containment(block_ngrams, kept_ngrams_union)

            dominated = (
                max_jaccard >= self.jaccard_threshold or
                containment >= self.containment_threshold
            )
            # Anderson (1994) + Slepian-Wolf synthesis: inhibition_weight from lifecycle.db
            # modifies suppression threshold. High inhibition = weak/competitor memory = suppress
            # more aggressively (lower threshold). Low inhibition = strong, important = harder to suppress.
            # inhibition_weight is optional; defaults to 0 (no modification).
            try:
                iw = float(block.get("inhibition_weight") or 0.0)
            except (TypeError, ValueError):
                iw = 0.0
            if iw > 0.0 and not prospective:
                # Effective threshold: lower for high-inhibition blocks (easier to suppress)
                effective_jac_thresh = self.jaccard_threshold * max(0.5, 1.0 / (1.0 + iw))
                effective_cont_thresh = self.containment_threshold * max(0.5, 1.0 / (1.0 + iw))
                dominated = (
                    max_jaccard >= effective_jac_thresh or
                    containment >= effective_cont_thresh
                )

            if dominated and not prospective:
                suppressed.append(block)
                jaccard_scores_suppressed.append(max_jaccard)
            else:
                kept.append(block)
                kept_ngrams_union |= block_ngrams
                kept_ngrams_per.append(block_ngrams)
                if dominated and prospective:
                    prospective_override += 1

        chars_kept = sum(len(b.get("text", "")) for b in kept)
        chars_suppressed = sum(len(b.get("text", "")) for b in suppressed)

        stats = {
            "total": len(blocks),
            "kept": len(kept),
            "suppressed": len(suppressed),
            "prospective_override": prospective_override,
            "total_chars_kept": chars_kept,
            "total_chars_suppressed": chars_suppressed,
            "chars_saved_pct": round(100 * chars_suppressed / max(1, chars_kept + chars_suppressed), 1),
            "avg_jaccard_suppressed": (
                sum(jaccard_scores_suppressed) / len(jaccard_scores_suppressed)
                if jaccard_scores_suppressed else 0.0
            ),
            "cross_source_pairs_checked": pairs_checked,
            "jaccard_threshold": self.jaccard_threshold,
            "containment_threshold": self.containment_threshold,
        }
        return kept, stats


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    blocks = [
        {
            "source": "user_profile",
            "text": "The user is Alice. She prefers concise responses. She works on Python.",
        },
        {
            "source": "memory",
            "text": "Alice prefers concise answers. She is working on Python code.",
        },
        {
            "source": "skills",
            "text": "EDF scheduling: sort jobs by earliest deadline first. hermes-fork uses EDF urgency.",
        },
        {
            "source": "memory",
            "text": "Paris is the capital of France. The Eiffel Tower is in Paris.",
        },
        {
            "source": "tools",
            "text": "Remember to run privilege-audit.py before deployment.",
            "is_prospective": True,
        },
        {
            "source": "memory",
            "text": "The user is Alice. She prefers concise responses. Python is her main language.",
        },
    ]

    filt = ContextDedupFilter(jaccard_threshold=0.35, containment_threshold=0.55)
    kept, stats = filt.filter(blocks)

    # Block 1 (user_profile about Alice) should be kept
    # Block 1 (memory Alice concise) should be suppressed (high overlap with user_profile)
    # Block 4 (prospective reminder) should ALWAYS be kept
    assert stats["total"] == 6
    assert any("Eiffel Tower" in b["text"] for b in kept), "Novel fact (Paris) should be kept"
    assert any("privilege-audit" in b["text"] for b in kept), "Prospective block must be kept"
    assert stats["kept"] + stats["suppressed"] == 6
    assert stats["suppressed"] >= 1, "Should suppress at least 1 duplicate"

    print(f"self-test OK: kept={stats['kept']}, suppressed={stats['suppressed']}, "
          f"chars_saved={stats['chars_saved_pct']}%, "
          f"prospective_override={stats['prospective_override']}")
    print(f"  avg_jaccard_suppressed={stats['avg_jaccard_suppressed']:.3f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cross-subsystem context dedup filter")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--jaccard-threshold", type=float, default=0.6)
    parser.add_argument("--containment-threshold", type=float, default=0.75)
    args = parser.parse_args()

    if args.self_test:
        _self_test()
        sys.exit(0)

    # Read blocks from stdin as JSON array
    try:
        blocks = json.load(sys.stdin)
    except Exception as exc:
        print(f"Error reading JSON from stdin: {exc}", file=sys.stderr)
        sys.exit(2)

    filt = ContextDedupFilter(
        jaccard_threshold=args.jaccard_threshold,
        containment_threshold=args.containment_threshold,
    )
    kept, stats = filt.filter(blocks)
    print(json.dumps({"kept": kept, "stats": stats}, indent=2))
