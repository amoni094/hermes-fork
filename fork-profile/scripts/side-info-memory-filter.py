"""Side-information-aware memory injection filter.

Theory — Wyner-Ziv (1976) & Slepian-Wolf (1973):

Wyner-Ziv: A source X can be compressed at rate R = H(X|Y) even when the
encoder does not observe side information Y — as long as the decoder has Y.
The fundamental insight: redundancy conditioned on the decoder's context is
wasted rate.

Slepian-Wolf: Two correlated sources X, Y encoded independently can achieve
the joint entropy H(X,Y) without encoder cooperation, as long as the decoder
sees both. Corollary: when two memory subsystems inject facts independently,
their joint injection wastes R_overlap = I(X;Y) bits vs. coordinated injection.

Applied to hermes-fork memory injection:
  - The "encoder" is the memory subsystem injecting facts into context.
  - The "decoder" is the LLM receiving the full context window.
  - The "side information Y" is the session context already present (skills
    loaded, tool results, conversation history, user profile, ARCHITECTURE.md).
  - Facts that are highly redundant with existing context should be suppressed
    or compressed, saving context tokens without information loss.

Einstein & McDaniel (1990): Prospective memory — remembering to do something
at a future time — is preserved in aging even when retrospective memory
degrades. Applied here: facts flagged as "prospective" (action-triggering
reminders like scheduled tasks) are NEVER suppressed regardless of redundancy,
because their value is their trigger function, not their information content.

This module:
  1. Scores facts by estimated redundancy with the current session context
  2. Suppresses high-redundancy facts above a configurable threshold
  3. NEVER suppresses prospective facts (prospective=True in fact metadata)
  4. Logs suppression decisions to omni/side-info-filter-log.jsonl

Usage:
  from side_info_memory_filter import SideInfoMemoryFilter
  filt = SideInfoMemoryFilter(session_context="<current session text>")
  injected = filt.filter(facts_list)

  OR as CLI:
  python3 side-info-memory-filter.py --self-test
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("side-info-memory-filter")

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes" / "profiles" / "fork"))
FILTER_LOG = HERMES_HOME / "omni" / "side-info-filter-log.jsonl"


# ---------------------------------------------------------------------------
# Token-level n-gram fingerprint (approximate H(X|Y) estimator)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r"[a-z0-9_\-]{2,}", text.lower())


def _ngram_set(tokens: list[str], n: int = 2) -> set[str]:
    """Return set of n-grams from token list."""
    if len(tokens) < n:
        return set(tokens)
    return {" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}


def _jaccard_overlap(set_a: set, set_b: set) -> float:
    """Jaccard similarity: |A ∩ B| / |A ∪ B|. Returns 0 for empty sets."""
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _containment(fact_ngrams: set, context_ngrams: set) -> float:
    """Containment: |F ∩ C| / |F|. How much of the fact is already in context."""
    if not fact_ngrams:
        return 0.0
    return len(fact_ngrams & context_ngrams) / len(fact_ngrams)


def redundancy_score(fact_text: str, context_text: str) -> float:
    """Estimate how redundant `fact_text` is given `context_text`.

    Returns a value in [0, 1]:
      0.0 = completely novel (inject it)
      1.0 = fully redundant with context (safe to suppress)

    Uses bigram containment as a proxy for conditional entropy H(X|Y).
    A fact is redundant if most of its bigrams are already in the context.
    Weighted: containment (0.7) + exact phrase match bonus (0.3).
    """
    fact_tokens = _tokenize(fact_text)
    context_tokens = _tokenize(context_text)

    fact_ngrams = _ngram_set(fact_tokens, n=2)
    context_ngrams = _ngram_set(context_tokens, n=2)

    containment = _containment(fact_ngrams, context_ngrams)

    # Exact substring bonus: a fact that appears verbatim is fully redundant
    phrase_bonus = 0.3 if fact_text.strip().lower() in context_text.lower() else 0.0

    return min(1.0, containment * 0.7 + phrase_bonus)


# ---------------------------------------------------------------------------
# Slepian-Wolf mutual information estimator
# ---------------------------------------------------------------------------

def _mutual_information_token_overlap(facts: list[str]) -> float:
    """Estimate I(X;Y) = token overlap between fact pairs as a fraction of vocabulary.

    A crude proxy: if two facts share many bigrams, they carry redundant
    information (high I(X;Y)) and joint injection wastes tokens.
    Returns average pairwise Jaccard over all fact pairs as fraction of 1.
    """
    if len(facts) < 2:
        return 0.0
    ngram_sets = [_ngram_set(_tokenize(f), n=2) for f in facts]
    pairs = 0
    total_jaccard = 0.0
    for i in range(len(ngram_sets)):
        for j in range(i + 1, len(ngram_sets)):
            total_jaccard += _jaccard_overlap(ngram_sets[i], ngram_sets[j])
            pairs += 1
    return total_jaccard / pairs if pairs > 0 else 0.0


# ---------------------------------------------------------------------------
# Main filter class
# ---------------------------------------------------------------------------

class SideInfoMemoryFilter:
    """Wyner-Ziv-inspired fact injection filter.

    Suppresses facts whose redundancy with the current session context
    exceeds the threshold. Prospective facts (action triggers) are never
    suppressed (Einstein & McDaniel 1990: prospective memory is preserved).

    Args:
        session_context: Full current session text (skills, tools, history, profile)
        redundancy_threshold: Suppress if score >= this (default 0.75)
        log_decisions: Write filter decisions to FILTER_LOG
    """

    def __init__(
        self,
        session_context: str = "",
        redundancy_threshold: float = 0.75,
        log_decisions: bool = True,
    ):
        self.session_context = session_context
        self.redundancy_threshold = redundancy_threshold
        self.log_decisions = log_decisions
        self._context_ngrams = _ngram_set(_tokenize(session_context), n=2)

    def _is_prospective(self, fact: dict) -> bool:
        """A fact is prospective if it's an action trigger (Einstein & McDaniel: preserve)."""
        text = fact.get("fact_text", "")
        fact_type = fact.get("fact_type", "")
        # Heuristic markers for prospective facts
        prospective_types = {"reminder", "todo", "action", "prospective", "scheduled"}
        if fact_type.lower() in prospective_types:
            return True
        trigger_phrases = [
            "remember to", "don't forget", "make sure to", "need to", "scheduled",
            "when you", "next time", "before the", "remind",
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in trigger_phrases)

    def score(self, fact: dict) -> float:
        """Compute redundancy score for one fact dict (with 'fact_text' key)."""
        text = fact.get("fact_text", "") or fact.get("text", "") or str(fact)
        return redundancy_score(text, self.session_context)

    def filter(self, facts: list[dict]) -> tuple[list[dict], dict]:
        """Filter facts, returning (kept_facts, stats_dict).

        Stats:
          total: int
          kept: int
          suppressed: int
          suppressed_prospective_override: int (prospective facts that would have been suppressed)
          avg_redundancy_suppressed: float
          avg_redundancy_kept: float
          mutual_information_estimate: float (cross-fact redundancy, Slepian-Wolf)
        """
        kept, suppressed = [], []
        prospective_override = 0
        scores_suppressed, scores_kept = [], []

        for fact in facts:
            score = self.score(fact)
            prospective = self._is_prospective(fact)

            if score >= self.redundancy_threshold and not prospective:
                suppressed.append(fact)
                scores_suppressed.append(score)
            else:
                kept.append(fact)
                scores_kept.append(score)
                if score >= self.redundancy_threshold and prospective:
                    prospective_override += 1

        # Slepian-Wolf cross-fact redundancy among suppressed candidates
        mi_estimate = _mutual_information_token_overlap(
            [f.get("fact_text", "") for f in suppressed]
        )

        stats = {
            "total": len(facts),
            "kept": len(kept),
            "suppressed": len(suppressed),
            "suppressed_prospective_override": prospective_override,
            "avg_redundancy_suppressed": (
                sum(scores_suppressed) / len(scores_suppressed)
                if scores_suppressed else 0.0
            ),
            "avg_redundancy_kept": (
                sum(scores_kept) / len(scores_kept)
                if scores_kept else 0.0
            ),
            "mutual_information_estimate": mi_estimate,
            "threshold": self.redundancy_threshold,
        }

        if self.log_decisions and suppressed:
            self._log(stats, suppressed)

        return kept, stats

    def _log(self, stats: dict, suppressed: list[dict]) -> None:
        FILTER_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "suppressed_ids": [
                f.get("memory_id", f.get("id", "?")) for f in suppressed
            ],
        }
        with FILTER_LOG.open("a") as fh:
            fh.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    context = (
        "The user's name is Alice. She prefers concise answers. "
        "The current project is hermes-fork. Python is the main language. "
        "hermes-fork scheduler uses EDF ordering. lifecycle.db uses WAL mode."
    )
    facts = [
        {"fact_text": "The user's name is Alice and she prefers concise answers.", "fact_type": "user"},
        {"fact_text": "Python is the main programming language for hermes-fork.", "fact_type": "env"},
        {"fact_text": "The capital of France is Paris.", "fact_type": "general"},
        {"fact_text": "Remember to run the privilege audit before deployment.", "fact_type": "reminder"},
        {"fact_text": "hermes-fork scheduler uses EDF ordering for jobs.", "fact_type": "env"},
    ]

    filt = SideInfoMemoryFilter(session_context=context, redundancy_threshold=0.5, log_decisions=False)
    kept, stats = filt.filter(facts)

    # Facts 0, 1, 4 should be high-redundancy (suppressed if threshold low)
    # Fact 2 (Paris) should be low-redundancy (kept)
    # Fact 3 (reminder) should ALWAYS be kept (prospective override)
    assert any(f["fact_text"] == "The capital of France is Paris." for f in kept), \
        "Novel fact should be kept"
    assert any("privilege audit" in f["fact_text"] for f in kept), \
        "Prospective fact should always be kept"
    assert stats["total"] == 5
    assert stats["kept"] + stats["suppressed"] == 5

    # Test redundancy_score directly
    score_high = redundancy_score("The user's name is Alice.", context)
    score_low = redundancy_score("Quantum entanglement is non-local.", context)
    assert score_high > score_low, f"Expected high>low: {score_high:.3f} vs {score_low:.3f}"

    print(f"self-test OK: kept={stats['kept']}, suppressed={stats['suppressed']}, "
          f"prospective_override={stats['suppressed_prospective_override']}")
    print(f"  score(redundant)={score_high:.3f}, score(novel)={score_low:.3f}")
    print(f"  MI estimate={stats['mutual_information_estimate']:.3f}")


# ---------------------------------------------------------------------------
# Module-level adapter for unified-recall integration
# ---------------------------------------------------------------------------

def filter_redundant(fused: list, query: str, threshold: float = 0.70,
                     session_context: str = "") -> list:
    """Adapter for unified-recall: filter fused result dicts by redundancy against query.

    Items whose text is redundant with the query (redundancy_score >= threshold) are
    suppressed UNLESS they contain a prospective-memory marker ([PROSPECTIVE], [ACTION],
    [TODO], [REMINDER]) per Einstein & McDaniel (1990) — those are never suppressed.

    session_context: additional Wyner-Ziv side information (conversation history);
    redundancy is checked against max(query_score, context_score) for better coverage.

    Returns the kept items (original order preserved).
    """
    # ADV-002 fix: threshold=0 would suppress everything. Treat as no-op.
    if threshold <= 0.0:
        return list(fused)
    threshold = min(threshold, 1.0)
    kept = []
    for item in fused:
        text = (item.get("_full_text") or item.get("text") or "").strip()
        if not text:
            kept.append(item)
            continue
        # Prospective override — never suppress action/reminder facts
        _PROSPECTIVE_MARKERS = ("[PROSPECTIVE]", "[ACTION]", "[TODO]", "[REMINDER]",
                                "REMINDER:", "ACTION:", "TODO:")
        if any(m in text for m in _PROSPECTIVE_MARKERS):
            kept.append(item)
            continue
        score = redundancy_score(text, query)
        # COH-002: also check against session_context (Wyner-Ziv side info = full session)
        if session_context:
            ctx_score = redundancy_score(text, session_context)
            score = max(score, ctx_score)
        if score < threshold:
            kept.append(item)
        # else: suppress — fact is already deducible from query context (Wyner-Ziv)
    return kept


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Side-information memory injection filter")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--score", nargs=2, metavar=("FACT", "CONTEXT"),
                        help="Score FACT redundancy against CONTEXT")
    args = parser.parse_args()

    if args.self_test:
        _self_test()
        sys.exit(0)

    if args.score:
        sc = redundancy_score(args.score[0], args.score[1])
        print(f"Redundancy score: {sc:.4f}")
        sys.exit(0)

    parser.print_help()
