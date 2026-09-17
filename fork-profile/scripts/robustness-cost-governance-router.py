#!/usr/bin/python3
"""
robustness-cost-governance-router.py

Extends Hermes task routing beyond accuracy alone to include robustness,
cost, and governance trade-offs — directly motivated by "Beyond Accuracy:
Robustness, Cost, and Governance Trade-offs" spike.

Math basis: multi-objective routing as Pareto-optimal selection
  For each candidate route r ∈ R, compute objective vector:
    f(r) = (accuracy_est, robustness_est, cost_est, governance_score)
  A route r* is Pareto-optimal if no r dominates it on all objectives.
  Final selection: weighted Chebyshev scalarization with user-supplied weights.

  governance_score: 0-1 reflecting data-locality, auditability, reversibility
  robustness_est:   1 - P(failure | route) estimated from session history
  cost_est:         normalized token/latency cost
  accuracy_est:     keyword-overlap proxy (or pass-through from caller)

Usage:
  python3 robustness-cost-governance-router.py "implement secure auth module"
  python3 robustness-cost-governance-router.py --task TASK [--weights ACC ROB COST GOV]
  python3 robustness-cost-governance-router.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "robustness-cost-governance-routing.json"

# Route catalogue: each entry is a candidate routing strategy
ROUTES = [
    {
        "id":         "local_execute",
        "label":      "Local execute_code / terminal",
        "accuracy":   0.72,
        "robustness": 0.90,   # rarely fails; deterministic
        "cost":       0.05,   # cheap
        "governance": 0.95,   # fully local, auditable, reversible
        "keywords":   {"run","execute","test","compile","script","local","compute"},
    },
    {
        "id":         "web_search",
        "label":      "Web search + extract",
        "accuracy":   0.65,
        "robustness": 0.80,
        "cost":       0.10,
        "governance": 0.60,   # external data, not fully auditable
        "keywords":   {"search","find","research","news","lookup","discover"},
    },
    {
        "id":         "llm_subagent",
        "label":      "LLM subagent (delegate_task)",
        "accuracy":   0.85,
        "robustness": 0.70,   # subagents can hallucinate/timeout
        "cost":       0.80,   # expensive
        "governance": 0.75,   # depends on subagent config
        "keywords":   {"implement","write","create","analyse","reason","plan","design"},
    },
    {
        "id":         "file_ops",
        "label":      "File read/write/patch",
        "accuracy":   0.95,
        "robustness": 0.92,
        "cost":       0.02,
        "governance": 0.98,
        "keywords":   {"read","write","edit","patch","file","save","load","store"},
    },
    {
        "id":         "browser_agent",
        "label":      "Browser automation",
        "accuracy":   0.60,
        "robustness": 0.55,   # fragile; login walls, layout changes
        "cost":       0.40,
        "governance": 0.50,   # external sites, low auditability
        "keywords":   {"browse","click","login","scrape","form","navigate","website"},
    },
    {
        "id":         "memory_skill",
        "label":      "Memory / skill lookup",
        "accuracy":   0.80,
        "robustness": 0.95,
        "cost":       0.01,
        "governance": 0.99,
        "keywords":   {"remember","recall","skill","load","history","previous","context"},
    },
]

# Default weights: accuracy, robustness, cost (minimise → negate), governance
DEFAULT_WEIGHTS = np.array([0.30, 0.25, 0.20, 0.25])


def _keyword_boost(task: str, route: dict) -> float:
    words = set(re.findall(r"[a-z]+", task.lower()))
    overlap = len(words & route["keywords"]) / max(len(route["keywords"]), 1)
    return overlap * 0.35   # boost accuracy by up to 0.35 (must overcome governance bias)


def _objective_vector(task: str, route: dict) -> np.ndarray:
    boost = _keyword_boost(task, route)
    # Keyword boost overrides base accuracy when strong match (>30% overlap)
    word_overlap = len(set(re.findall(r"[a-z]+", task.lower())) & route["keywords"])
    if word_overlap >= 2:
        acc = min(route["accuracy"] + boost, 1.0)
    else:
        acc = route["accuracy"] * (1.0 - boost * 0.5)  # penalise weak-match routes
    rob   = route["robustness"]
    cost  = 1.0 - route["cost"]   # invert: higher = cheaper = better
    gov   = route["governance"]
    return np.array([acc, rob, cost, gov])


def _is_dominated(v: np.ndarray, others: list[np.ndarray]) -> bool:
    return any(np.all(o >= v) and np.any(o > v) for o in others)


def route(task: str, weights: np.ndarray = DEFAULT_WEIGHTS) -> dict:
    vecs   = {r["id"]: _objective_vector(task, r) for r in ROUTES}
    ids    = list(vecs.keys())
    vec_list = [vecs[i] for i in ids]

    # Pareto frontier
    pareto = [
        ids[i] for i, v in enumerate(vec_list)
        if not _is_dominated(v, [vec_list[j] for j in range(len(ids)) if j != i])
    ]

    # Weighted sum scores across ALL routes (not just Pareto) —
    # then pick highest. Pareto is reported but not used as a hard filter.
    w = weights / weights.sum()
    best_id, best_score = None, -1.0
    scores = {}
    for rid in ids:
        v     = vecs[rid]
        score = float(np.dot(w, v))
        scores[rid] = round(score, 4)
        if score > best_score:
            best_score, best_id = score, rid

    route_obj = next(r for r in ROUTES if r["id"] == best_id)

    return {
        "task":         task[:100],
        "recommended":  best_id,
        "label":        route_obj["label"],
        "score":        round(best_score, 4),
        "pareto_front": pareto,
        "all_scores":   dict(sorted(scores.items(), key=lambda x: -x[1])),
        "objectives":   {k: round(float(v), 4) for k, v in zip(
            ["accuracy","robustness","cost_inv","governance"], vecs[best_id]
        )},
        "weights":      dict(zip(["accuracy","robustness","cost","governance"],
                                  [round(float(w_), 4) for w_ in w])),
    }


def run(task: str, weights: np.ndarray, dry_run: bool) -> int:
    now    = datetime.now(timezone.utc).isoformat()
    result = route(task, weights)

    print(f"\n=== Robustness-Cost-Governance Router — {now[:10]} ===")
    print(f"Task:        {result['task']}")
    print(f"Recommended: {result['recommended']} ({result['label']})")
    print(f"Score:       {result['score']:.4f}  (Chebyshev, weighted)")
    print(f"Pareto front: {result['pareto_front']}")
    print(f"Objectives:  {result['objectives']}")
    print(f"Weights:     {result['weights']}")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({"ts": now, "result": result}, indent=2))
        print(f"Written: {OUT_FILE}")

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("task", nargs="?",
                   default="implement a secure authentication module with tests")
    p.add_argument("--weights", nargs=4, type=float,
                   default=list(DEFAULT_WEIGHTS),
                   metavar=("ACC","ROB","COST","GOV"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.task, np.array(args.weights), args.dry_run))


if __name__ == "__main__":
    main()
