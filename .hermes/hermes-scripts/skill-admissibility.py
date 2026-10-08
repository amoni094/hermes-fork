#!/usr/bin/env python3
"""BERGER-2: admissibility pruning of dominated skills.

Usage:
  python3 skill-admissibility.py --data '{"skill_a":{"easy":[1,1,0,1],"hard":[0,0,1,0]},"skill_b":{"easy":[1,1,1,0],"hard":[1,1,0,0]}}'
"""
from __future__ import annotations

import argparse
import json
import sys

EPS = 0.05


def mean_loss(xs):
    return 1.0 - (sum(xs) / len(xs) if xs else 0.0)


def analyze(data, eps=EPS):
    skills = list(data)
    risk = {
        s: {c: mean_loss(v) for c, v in clusters.items()}
        for s, clusters in data.items()
    }
    dominated = set()
    comparisons = 0
    for p in skills:
        for q in skills:
            if p == q:
                continue
            comparisons += 1
            clusters = set(risk[p]) & set(risk[q])
            if not clusters:
                continue

            def R(s, c):
                return risk[s][c]

            all_le = all(R(q, c) <= R(p, c) + eps for c in clusters)
            some_lt = any(R(q, c) < R(p, c) - eps for c in clusters)
            if all_le and some_lt:
                dominated.add(p)
    return {
        "dominated": sorted(dominated),
        "admissible": [s for s in skills if s not in dominated],
        "risk_table": risk,
        "comparisons": comparisons,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--eps", type=float, default=EPS)
    a = p.parse_args()
    json.dump(analyze(json.loads(a.data), a.eps), sys.stdout)
    print()


if __name__ == "__main__":
    main()
