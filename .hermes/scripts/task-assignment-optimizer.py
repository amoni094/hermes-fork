#!/usr/bin/python3
"""
task-assignment-optimizer.py

Replaces ad-hoc skill routing with principled assignment that minimizes
total routing cost while respecting skill capacity constraints.

CS SPIKE basis (Context-Aware System Synthesis, Task Assignment, and Routing):
applies context-aware optimal assignment theory to Hermes skill routing.
Given a query, compute the minimum-cost assignment of task dimensions to skills
using the Hungarian algorithm (optimal O(n³) assignment).

Math basis: bipartite matching / linear assignment problem.
  Cost matrix C[i,j] = cost of assigning task dimension i to skill j
  Optimal assignment minimizes Σ C[i,j] × X[i,j]  s.t. X is a permutation matrix

For Hermes:
  - Task dimensions = sub-queries extracted from the user request
  - Skills = candidates from projection-implication-scorer
  - Cost C[i,j] = 1 - semantic_overlap(dimension_i, skill_j)
  - Output: ranked list of (task_dimension, best_skill) assignments

Usage:
  python3 task-assignment-optimizer.py "debug code and search docs and run tests"
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

HOME      = Path.home()
SKILLS_DIR = HOME / ".hermes/skills"
CACHE_DIR  = HOME / ".hermes/cache/monitors"
OUT_FILE   = CACHE_DIR / "task-assignments.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_skills(max_skills: int = 50) -> dict[str, str]:
    skills: dict[str, str] = {}
    for sd in SKILLS_DIR.rglob("SKILL.md"):
        try:
            text = sd.read_text()
            m = re.search(r"description:\s*['\"]?(.+?)['\"]?\n", text)
            desc = m.group(1).strip() if m else sd.parent.name
            skills[sd.parent.name] = desc
            if len(skills) >= max_skills:
                break
        except Exception:
            pass
    return skills


def _split_task_dimensions(query: str) -> list[str]:
    """Split query into sub-task dimensions via conjunctions/punctuation."""
    parts = re.split(r"\band\b|\bthen\b|\balso\b|,|;|\bwhile\b|\bafter\b", query, flags=re.IGNORECASE)
    dims = [p.strip() for p in parts if len(p.strip()) > 5]
    return dims if dims else [query]


def _keyword_overlap(text_a: str, text_b: str) -> float:
    wa = set(re.findall(r"[a-z]{3,}", text_a.lower()))
    wb = set(re.findall(r"[a-z]{3,}", text_b.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def assign(query: str, top_k: int = 20) -> list[dict]:
    """Run optimal task-skill assignment via Hungarian algorithm."""
    dims  = _split_task_dimensions(query)
    skills = _load_skills(max_skills=top_k)
    if not skills:
        return []

    skill_names = list(skills.keys())
    skill_descs = list(skills.values())

    # Build cost matrix: C[i,j] = 1 - overlap(dim_i, skill_j)
    n_dims   = len(dims)
    n_skills = len(skill_names)
    # Pad to square if needed
    size = max(n_dims, n_skills)
    C = np.ones((size, size))
    for i, dim in enumerate(dims):
        for j, desc in enumerate(skill_descs):
            overlap = _keyword_overlap(dim, desc)
            C[i, j] = 1.0 - overlap

    # Hungarian algorithm: find optimal assignment
    row_ind, col_ind = linear_sum_assignment(C)

    results = []
    for r, c in zip(row_ind, col_ind):
        if r < n_dims and c < n_skills:
            results.append({
                "dimension": dims[r],
                "skill":     skill_names[c],
                "cost":      round(float(C[r, c]), 4),
                "overlap":   round(1.0 - float(C[r, c]), 4),
            })

    # Sort by overlap descending
    results.sort(key=lambda x: -x["overlap"])
    return results


def run(query: str, dry_run: bool = False) -> None:
    now = datetime.now(timezone.utc).isoformat()
    assignments = assign(query)

    print(f"\n=== Task Assignment Optimizer — {now[:10]} ===")
    print(f"Query: '{query}'")
    if not assignments:
        print("No assignments computed.")
        return

    total_cost = sum(a["cost"] for a in assignments)
    print(f"Task dimensions: {len(assignments)},  Total assignment cost: {total_cost:.3f}")
    print(f"\n  {'Dimension':<30} → {'Skill':<35} overlap")
    print("  " + "-" * 75)
    for a in assignments:
        print(f"  {a['dimension'][:29]:<30} → {a['skill'][:34]:<35} {a['overlap']:.3f}")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "query": query,
            "assignments": assignments,
            "total_cost": round(total_cost, 4),
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimal task-skill assignment (Hungarian algorithm)")
    parser.add_argument("query", nargs="?",
                        default="research arxiv papers and implement findings and review code")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(query=args.query, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
