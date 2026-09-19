#!/usr/bin/python3
"""
free-energy-task-optimizer.py

Enables principled trade-off between task optimality (cost), consistency
(accuracy), and exploration (entropy) using a free-energy decomposition
of the agent's planning objective.

Math basis: Thermodynamic free energy (Bridging Control, Inference, Transport)
  F = E[cost] - β⁻¹ · H[policy]
  where E[cost] = expected task cost, H[policy] = policy entropy (exploration),
  β = inverse temperature (exploitation pressure).
  
  Optimal policy: π*(a|s) ∝ exp(-β · cost(a,s))  [softmax/Boltzmann]
  
  Operationally: score candidate actions/routes by their free-energy cost;
  select the minimum free-energy action. β tunes exploitation vs exploration:
    β → ∞: pure exploitation (greedy)
    β → 0:  pure exploration (uniform random)

Usage:
  python3 free-energy-task-optimizer.py --actions A1 A2 A3 --costs 0.3 0.5 0.1
  python3 free-energy-task-optimizer.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "free-energy-decisions.json"

DEFAULT_BETA = 3.0   # inverse temperature; 3.0 = moderate exploitation


def softmax_policy(costs: list[float], beta: float) -> list[float]:
    """Boltzmann policy: π(a) ∝ exp(-β·cost(a))."""
    scaled = [-beta * c for c in costs]
    max_s  = max(scaled)
    exps   = [math.exp(s - max_s) for s in scaled]
    total  = sum(exps)
    return [e / total for e in exps]


def free_energy(costs: list[float], probs: list[float], beta: float) -> float:
    """F = E[cost] - β⁻¹ · H[π]."""
    e_cost = sum(p * c for p, c in zip(probs, costs))
    h_pi   = -sum(p * math.log(p) for p in probs if p > 0)
    return e_cost - h_pi / beta


def optimise(actions: list[str], costs: list[float], beta: float) -> dict:
    probs   = softmax_policy(costs, beta)
    f       = free_energy(costs, probs, beta)
    best_i  = max(range(len(probs)), key=lambda i: probs[i])
    entropy = -sum(p * math.log(p) for p in probs if p > 0)

    return {
        "beta":      beta,
        "free_energy": round(f, 4),
        "entropy":   round(entropy, 4),
        "best":      actions[best_i],
        "best_prob": round(probs[best_i], 4),
        "policy":    [
            {"action": a, "cost": round(c, 4), "prob": round(p, 4)}
            for a, c, p in zip(actions, costs, probs)
        ],
    }


def run(actions: list[str], costs: list[float], beta: float, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    # Demo: route Hermes task across 5 action types
    if not actions:
        actions = [
            "direct_answer",
            "single_tool_call",
            "skill_lookup",
            "web_search",
            "delegate_subagent",
        ]
        costs = [0.05, 0.20, 0.15, 0.35, 0.60]

    if len(actions) != len(costs):
        print(f"ERROR: {len(actions)} actions but {len(costs)} costs")
        return 1

    print(f"\n=== Free-Energy Task Optimizer — {now[:10]} ===")

    # Show effect of different β values
    betas = [beta, 1.0, 10.0] if not dry_run or beta == DEFAULT_BETA else [beta]

    results = []
    for b in betas:
        r = optimise(actions, costs, b)
        results.append(r)
        print(f"\n  β={b:.1f}  F={r['free_energy']:.4f}  H={r['entropy']:.4f}")
        print(f"  Best: {r['best']} (prob={r['best_prob']:.3f})")
        print(f"  {'Action':<20} {'Cost':>6}  {'Prob':>6}")
        for item in r["policy"]:
            print(f"    {item['action']:<20} {item['cost']:>6.3f}  {item['prob']:>6.3f}")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "results": results}, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--actions", nargs="+", default=[])
    p.add_argument("--costs",   nargs="+", type=float, default=[])
    p.add_argument("--beta",    type=float, default=DEFAULT_BETA)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.actions, args.costs, args.beta, args.dry_run))


if __name__ == "__main__":
    main()
