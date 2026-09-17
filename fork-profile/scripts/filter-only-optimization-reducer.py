#!/usr/bin/python3
"""
filter-only-optimization-reducer.py

Enables skill-routing decisions to discard redundant parameterizations
by reducing the full skill parameter space to only the constraints that
are actually active (filter-only reduction).

Math basis: Fourier/filter-only optimization
  In sparse optimization, many parameters are at their bounds (inactive).
  The reduced problem only optimises over active constraints:
    min f(x)  s.t.  g_i(x) = 0 for active i only
  Filter-only reduction: discard skills whose routing weight is at the
  lower bound (weight ≤ ε) — they contribute nothing to the solution.
  
  Applied to skill routing: given a query, compute initial weights via
  Jaccard. Skills with weight below FILTER_FLOOR are "inactive" and
  pruned before the final ranking step. This reduces the effective
  search space and makes routing faster and more interpretable.

Usage:
  python3 filter-only-optimization-reducer.py --query QUERY [--top N]
  python3 filter-only-optimization-reducer.py --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME       = Path.home()
SKILLS_DIR = HOME / ".hermes/profiles/fork/skills"
ALT_SKILLS = HOME / ".hermes/skills"

FILTER_FLOOR  = 0.02   # prune skills with weight <= this (Jaccard against 60+ skill docs)
MAX_SKILLS    = 60


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def _load_skills(n: int) -> list[dict]:
    skills = []
    seen: set[str] = set()
    for base in [SKILLS_DIR, ALT_SKILLS]:
        if not base.exists():
            continue
        for md in base.rglob("SKILL.md"):
            name = md.parent.name
            if name in seen:
                continue
            try:
                tokens = _tokenize(md.read_text()[:400])
                if tokens:
                    skills.append({"name": name, "tokens": tokens})
                    seen.add(name)
            except Exception:
                pass
            if len(skills) >= n:
                break
        if len(skills) >= n:
            break
    return skills


def reduce_and_rank(query: str, top_n: int, floor: float) -> dict:
    q_tok   = _tokenize(query)
    skills  = _load_skills(MAX_SKILLS)

    # Compute Jaccard weights
    weighted = []
    for s in skills:
        w = len(q_tok & s["tokens"]) / max(len(q_tok | s["tokens"]), 1)
        weighted.append((s["name"], w))

    full_n    = len(weighted)
    # Filter-only reduction: keep active constraints only
    active    = [(name, w) for name, w in weighted if w > floor]
    pruned_n  = full_n - len(active)

    # Rank survivors
    ranked    = sorted(active, key=lambda x: -x[1])[:top_n]

    return {
        "query":       query[:60],
        "full_skills": full_n,
        "pruned":      pruned_n,
        "active":      len(active),
        "top":         ranked,
        "floor":       floor,
    }


def run(query: str, top_n: int, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    demo = [query] if query != "agent memory compression" else [
        "agent memory compression",
        "debug python error",
        "configure hermes settings",
        "search for papers on reinforcement learning",
    ]

    print(f"\n=== Filter-Only Optimization Reducer — {now[:10]} ===")
    print(f"Floor={FILTER_FLOOR}  Top={top_n}\n")

    for q in demo:
        r = reduce_and_rank(q, top_n, FILTER_FLOOR)
        reduction_pct = 100 * r["pruned"] / max(r["full_skills"], 1)
        print(f"  Query: \"{r['query']}\"")
        print(f"  Skills: {r['full_skills']} → active {r['active']} "
              f"(pruned {r['pruned']}, {reduction_pct:.0f}%)")
        print(f"  Top {min(top_n, len(r['top']))}:")
        for name, w in r["top"][:5]:
            print(f"    {name:<40} w={w:.4f}")
        print()

    print("ALARM: no — filter-only reduction complete")
    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--query",   default="agent memory compression")
    p.add_argument("--top",     type=int, default=5)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.query, args.top, args.dry_run))


if __name__ == "__main__":
    main()
