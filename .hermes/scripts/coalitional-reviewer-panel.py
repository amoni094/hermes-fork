#!/usr/bin/python3
"""
coalitional-reviewer-panel.py

Safe multi-agent review delegation by algorithmically certifying that a
coalition of reviewers (agents) provides sufficient coverage, diversity,
and non-redundancy before a review is accepted.

Math basis: Cooperative game theory / coalitional value
  Shapley value φ_i = sum over S not containing i of:
    [|S|!(n-|S|-1)!/n!] * [v(S∪{i}) - v(S)]
  where v(S) = coalition value = coverage of review dimensions.
  
  A reviewer coalition is CERTIFIED if:
    1. Total coverage v(S) >= COVERAGE_THRESHOLD
    2. No reviewer i has Shapley value < SHAPLEY_MIN (no free-riders)
    3. Pairwise Jaccard similarity between any two reviewers < OVERLAP_MAX
    
  Operationally: each "reviewer" is a review focus area / skill set,
  coverage = union of review dimensions covered.

Usage:
  python3 coalitional-reviewer-panel.py --dry-run
  python3 coalitional-reviewer-panel.py --reviewers R1 R2 R3
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "coalitional-review.json"

COVERAGE_THRESHOLD = 0.70   # need 70% of all dimensions covered
SHAPLEY_MIN        = 0.05   # each reviewer must contribute ≥5% marginal value
OVERLAP_MAX        = 0.60   # reviewers must be <60% similar

# Review dimensions that need coverage
ALL_DIMENSIONS = [
    "correctness", "security", "performance", "maintainability",
    "test_coverage", "documentation", "edge_cases", "dependencies",
    "compatibility", "observability",
]

# Predefined reviewer profiles (name -> set of dimensions they cover well)
DEFAULT_REVIEWERS = {
    "security_expert":  {"correctness", "security", "edge_cases", "dependencies"},
    "perf_engineer":    {"performance", "correctness", "observability", "compatibility"},
    "qa_specialist":    {"test_coverage", "edge_cases", "correctness", "documentation"},
    "maintainability":  {"maintainability", "documentation", "dependencies", "compatibility"},
    "ops_reviewer":     {"observability", "performance", "security", "compatibility"},
}


def _coalition_value(reviewers: list[str], profiles: dict[str, set]) -> float:
    """Coverage value of a coalition = fraction of dimensions covered."""
    covered = set()
    for r in reviewers:
        covered |= profiles.get(r, set())
    return len(covered & set(ALL_DIMENSIONS)) / len(ALL_DIMENSIONS)


def _shapley_values(reviewers: list[str], profiles: dict[str, set]) -> dict[str, float]:
    """Compute Shapley values for each reviewer."""
    n      = len(reviewers)
    phi    = {r: 0.0 for r in reviewers}
    others = reviewers[:]

    for r in reviewers:
        rest = [x for x in others if x != r]
        for size in range(len(rest) + 1):
            for S in combinations(rest, size):
                S     = list(S)
                coeff = (math.factorial(size) * math.factorial(n - size - 1)
                         / math.factorial(n))
                marg  = _coalition_value(S + [r], profiles) - _coalition_value(S, profiles)
                phi[r] += coeff * marg

    return {r: round(v, 4) for r, v in phi.items()}


def _pairwise_overlap(reviewers: list[str], profiles: dict[str, set]) -> list[dict]:
    pairs = []
    for a, b in combinations(reviewers, 2):
        sa, sb = profiles.get(a, set()), profiles.get(b, set())
        jacc   = len(sa & sb) / max(len(sa | sb), 1)
        pairs.append({"a": a, "b": b, "jaccard": round(jacc, 4),
                      "redundant": jacc > OVERLAP_MAX})
    return pairs


def certify(reviewer_names: list[str], profiles: dict[str, set]) -> dict:
    coverage    = _coalition_value(reviewer_names, profiles)
    shapley     = _shapley_values(reviewer_names, profiles)
    pairs       = _pairwise_overlap(reviewer_names, profiles)

    free_riders  = [r for r, v in shapley.items() if v < SHAPLEY_MIN]
    redundant    = [p for p in pairs if p["redundant"]]
    low_coverage = coverage < COVERAGE_THRESHOLD

    certified = not (free_riders or redundant or low_coverage)
    issues    = []
    if low_coverage:
        issues.append(f"coverage={coverage:.3f} < {COVERAGE_THRESHOLD}")
    if free_riders:
        issues.append(f"free-riders: {free_riders}")
    if redundant:
        issues.append(f"redundant pairs: {[(p['a'],p['b']) for p in redundant]}")

    return {
        "reviewers":   reviewer_names,
        "coverage":    round(coverage, 4),
        "shapley":     shapley,
        "pairs":       pairs,
        "free_riders": free_riders,
        "redundant":   redundant,
        "certified":   certified,
        "issues":      issues,
    }


def run(reviewer_names: list[str] | None, dry_run: bool) -> int:
    now     = datetime.now(timezone.utc).isoformat()
    profiles = DEFAULT_REVIEWERS

    if reviewer_names is None:
        reviewer_names = list(profiles.keys())

    result = certify(reviewer_names, profiles)

    print(f"\n=== Coalitional Reviewer Panel — {now[:10]} ===")
    print(f"Reviewers: {result['reviewers']}")
    print(f"Coverage:  {result['coverage']:.3f}  (threshold={COVERAGE_THRESHOLD})\n")

    print("  Shapley values:")
    for r, v in result["shapley"].items():
        icon = "⚠ FREE-RIDER" if v < SHAPLEY_MIN else "✓"
        print(f"    {r:<22} φ={v:.4f}  {icon}")

    if result["pairs"]:
        print("\n  Pairwise overlap:")
        for p in result["pairs"]:
            icon = "⚠ REDUNDANT" if p["redundant"] else "✓"
            print(f"    {p['a']:<20} ↔ {p['b']:<20} J={p['jaccard']:.4f}  {icon}")

    print()
    if result["certified"]:
        print("PANEL: CERTIFIED — coalition provides sufficient diverse coverage")
        print("ALARM: no")
    else:
        print(f"PANEL: NOT CERTIFIED — issues: {'; '.join(result['issues'])}")
        print("ALARM: yes — reviewer coalition fails certification criteria")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({"ts": now, **result}, indent=2))

    return 0 if result["certified"] else 1


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--reviewers", nargs="+", default=None)
    p.add_argument("--dry-run",   action="store_true")
    args = p.parse_args()
    sys.exit(run(args.reviewers, args.dry_run))


if __name__ == "__main__":
    main()
