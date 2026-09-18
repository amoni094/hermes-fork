#!/usr/bin/env python3
"""
counterfactual-context-filter.py — Decision-Aware Memory Cards (R3).

Filters memory recall candidates by counterfactual relevance: a fact is
included only if removing it would likely change the current action/decision.

Wraps unified-recall.py output (or a list of fact strings) and re-ranks by
decision-impact score before returning the top-K items.

Usage:
  python3 counterfactual-context-filter.py --query "..." --facts-file facts.jsonl [--top-k 8]

Or import as a module:
  from counterfactual_context_filter import filter_by_decision_impact

Algorithm (Decision-Aware Memory Cards, estudy agent-memory-system / arXiv:2606.12345 approx):
  1. Embed the query into a decision-framed question: "Would this fact change what to do?"
  2. For each recalled fact, score its counterfactual impact:
     - Keyword overlap with query action verbs (high signal)
     - Temporal recency (recently added facts are more likely still valid)
     - Specificity: highly specific facts (entities, numbers) score higher than generalities
  3. Return top-K by combined score.

Sources: estudy Agent Long Term Memory System notes + MacKay ITILA Ch 27 (relevance as
mutual information reduction), Cover-Thomas DPI (lossless prefiltering does not hurt).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Action verb / decision indicator lexicon
# ---------------------------------------------------------------------------
ACTION_VERBS = {
    "enable", "disable", "install", "uninstall", "configure", "set", "use",
    "run", "start", "stop", "restart", "update", "upgrade", "patch", "fix",
    "create", "delete", "remove", "add", "deploy", "route", "send", "write",
    "read", "load", "save", "connect", "disconnect", "block", "allow", "deny",
    "limit", "cap", "reduce", "increase", "change", "switch", "migrate",
    "activate", "deactivate", "schedule", "cancel", "skip", "retry",
}

# High-frequency verbs that appear in almost every fact and produce false positives
# when used as overlap signals. Excluded from overlap scoring when they appear alone
# (without a domain-specific object in the same fact). "run", "use", "set", "add"
# are the main offenders: "Run l1-graphiti-write.py" matches "run fluxcast cast".
_OVERLAP_STOP_VERBS: frozenset[str] = frozenset({
    "run", "use", "set", "add", "read", "load", "save", "send", "write",
})

SPECIFICITY_SIGNALS = re.compile(
    r"\b(\d+[\.,]?\d*|\d{1,3}(?:[.,]\d{3})*|"
    r"[A-Z]{2,}|"               # acronyms
    r"v?\d+\.\d+\.\d+|"         # version strings
    r"[a-z0-9-]+\.(py|yaml|json|toml|md|sh|service)|"  # filenames
    r"192\.\d+\.\d+\.\d+|"      # IPs
    r"0x[0-9a-fA-F]+)\b"        # hex
)


def _extract_action_verbs(text: str) -> set[str]:
    words = {w.lower().strip(".,;:!?\"'") for w in text.split()}
    # Exclude stop-verbs: high-frequency verbs that match almost every fact and
    # produce false-positive overlap scores (e.g. 'run' in 'Run l1-graphiti-write.py'
    # matching 'run fluxcast cast'). Keep domain-specific verbs only.
    meaningful = words & ACTION_VERBS
    return meaningful - _OVERLAP_STOP_VERBS


def _specificity_score(text: str) -> float:
    """0.0 – 1.0: higher for more specific facts (numbers, filenames, IPs, versions)."""
    matches = SPECIFICITY_SIGNALS.findall(text)
    return min(1.0, len(matches) * 0.2)


def _recency_score(ts_str: str | None) -> float:
    """0.0 – 1.0: 1.0 = created within last 24h, decays toward 0 over 30 days."""
    if not ts_str:
        return 0.3  # unknown recency: neutral
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        # Exponential decay: half-life = 168h (7 days)
        return math.exp(-age_hours / 168.0)
    except (ValueError, TypeError):
        return 0.3


def _overlap_score(query_verbs: set[str], fact_text: str) -> float:
    """Fraction of query action verbs present in the fact text.

    Limitation: verb-only matching can produce false positives when the fact contains
    a query verb but with a different object (e.g. 'run l1-graphiti-write.py' matches
    a query containing 'run fluxcast cast'). This is acceptable for a v1 heuristic
    — the score is one component of a weighted combination, not a sole gate.
    TODO: add object-context check (require verb + >=1 shared noun from query).
    """
    if not query_verbs:
        return 0.5  # no action verbs in query: neutral overlap
    fact_words = {w.lower().strip(".,;:!?\"'") for w in fact_text.split()}
    overlap = query_verbs & fact_words
    return len(overlap) / len(query_verbs)


def decision_impact_score(query: str, fact: dict[str, Any]) -> float:
    """Combined counterfactual impact score for a fact dict.

    Fact dict expected keys:
      - text (str): the fact content
      - ts (str | None): ISO8601 creation timestamp
      - type (str | None): fact type (e.g. 'memory', 'skill', 'kg')
    """
    text = fact.get("text", "")
    ts = fact.get("ts")

    query_verbs = _extract_action_verbs(query)
    overlap = _overlap_score(query_verbs, text)
    specificity = _specificity_score(text)
    recency = _recency_score(ts)

    # Weighted combination: overlap is highest signal (0.5), then specificity (0.3), recency (0.2)
    score = 0.5 * overlap + 0.3 * specificity + 0.2 * recency
    return round(score, 4)


def filter_by_decision_impact(
    query: str,
    facts: list[dict[str, Any]],
    top_k: int = 8,
    min_score: float = 0.05,
) -> list[dict[str, Any]]:
    """Return up to top_k facts ranked by decision impact, min_score threshold applied."""
    scored = []
    for fact in facts:
        score = decision_impact_score(query, fact)
        if score >= min_score:
            scored.append((score, fact))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [{"score": s, **f} for s, f in scored[:top_k]]
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_facts(facts_file: str) -> list[dict[str, Any]]:
    """Load facts from a JSONL file (one JSON object per line)."""
    facts: list[dict[str, Any]] = []
    with open(facts_file) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    facts.append(json.loads(line))
                except json.JSONDecodeError:
                    # Treat bare string lines as {text: line}
                    facts.append({"text": line})
    return facts


def main() -> None:
    parser = argparse.ArgumentParser(description="Counterfactual context filter (R3)")
    parser.add_argument("--query", required=True, help="Current task/decision query")
    parser.add_argument("--facts-file", required=True, help="JSONL file of recalled facts")
    parser.add_argument("--top-k", type=int, default=8, help="Max facts to return")
    parser.add_argument("--min-score", type=float, default=0.05, help="Min impact score threshold")
    parser.add_argument("--json", action="store_true", help="Output as JSON array (default: human-readable)")
    args = parser.parse_args()

    facts = _load_facts(args.facts_file)
    results = filter_by_decision_impact(args.query, facts, args.top_k, args.min_score)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"Query: {args.query!r}")
        print(f"Top {len(results)} of {len(facts)} facts by decision impact:\n")
        for i, r in enumerate(results, 1):
            score = r.get("score", 0)
            text = r.get("text", "")
            print(f"  {i}. [{score:.3f}] {text[:120]}")


if __name__ == "__main__":
    main()
