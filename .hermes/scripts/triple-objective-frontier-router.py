#!/usr/bin/python3
"""
triple-objective-frontier-router.py

Explicit Pareto trade-off transparency: routes tasks by optimising
three objectives simultaneously — accuracy, latency, and cost —
and reports the Pareto frontier so Hermes can justify routing choices.

Math basis: Multi-objective optimisation / Pareto frontier
  min (f1(x), f2(x), f3(x)) subject to x in X
  where f1=error_rate, f2=latency, f3=cost per task.

Run on-demand: /usr/bin/python3 triple-objective-frontier-router.py
"""
from __future__ import annotations
import sys

# Route options: (name, error_rate, latency_s, cost_usd)
ROUTES = [
    ("direct_answer",         0.15, 0.5,  0.001),
    ("web_search",            0.10, 2.0,  0.003),
    ("delegate_subagent",     0.05, 8.0,  0.020),
    ("skill_view_then_answer",0.08, 1.2,  0.002),
    ("clarify_first",         0.03, 15.0, 0.005),
]

def _pareto_frontier(routes):
    """Return non-dominated routes (Pareto optimal w.r.t. all 3 objectives)."""
    frontier = []
    for r in routes:
        dominated = False
        for other in routes:
            if other is r: continue
            if (other[1] <= r[1] and other[2] <= r[2] and other[3] <= r[3] and
                (other[1] < r[1] or other[2] < r[2] or other[3] < r[3])):
                dominated = True
                break
        if not dominated:
            frontier.append(r)
    return frontier

def route(task: str, weights=(0.4, 0.3, 0.3)) -> None:
    """weights: (accuracy_weight, speed_weight, cost_weight), sum=1."""
    w_acc, w_spd, w_cst = weights
    # Normalise objectives to [0,1]
    max_err  = max(r[1] for r in ROUTES)
    max_lat  = max(r[2] for r in ROUTES)
    max_cost = max(r[3] for r in ROUTES)

    scored = []
    for name, err, lat, cost in ROUTES:
        # Score = weighted sum of normalised objectives (lower = better)
        score = w_acc*(err/max_err) + w_spd*(lat/max_lat) + w_cst*(cost/max_cost)
        scored.append((score, name, err, lat, cost))
    scored.sort()

    frontier = _pareto_frontier(ROUTES)
    frontier_names = {r[0] for r in frontier}

    print(f"\n=== Triple-Objective Frontier Router ===")
    print(f"Task:    {task[:60]}")
    print(f"Weights: accuracy={w_acc} speed={w_spd} cost={w_cst}\n")
    print(f"  {'Route':<30} {'Score':>7} {'Err':>6} {'Lat(s)':>8} {'Cost':>8}  Pareto")
    print("  " + "-"*70)
    for score, name, err, lat, cost in scored:
        pf = "★" if name in frontier_names else " "
        print(f"  {name:<30} {score:>7.3f} {err:>6.2f} {lat:>8.1f} {cost:>8.4f}  {pf}")

    best = scored[0]
    print(f"\nRecommended: {best[1]}  (score={best[0]:.3f})")
    print(f"Pareto frontier ({len(frontier)} routes): {[r[0] for r in frontier]}")

if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "answer a factual question"
    route(task)
