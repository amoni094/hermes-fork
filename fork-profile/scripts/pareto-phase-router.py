#!/usr/bin/python3
"""
pareto-phase-router.py

Enables staged multi-goal agent planning — converge on primary objective
first, then diversify toward secondary goals. Implements a two-phase
Pareto routing strategy: Phase 1 (convergence) optimises single best
route; Phase 2 (diversification) fans out to explore Pareto frontier.

Math basis: "Converge Then Diversify" (arXiv spike)
  Phase 1: argmin_{r} loss_primary(r)      — find best single route
  Phase 2: {r : loss_primary(r) ≤ ε_tol} ∩ Pareto(loss_secondary)
           — explore routes within ε_tol of primary optimum that
             maximise secondary objectives.
  Switch from Phase 1→2 when primary loss gap < CONVERGENCE_THRESHOLD.

Usage:
  python3 pareto-phase-router.py --task TASK --primary GOAL --secondary GOAL2
  python3 pareto-phase-router.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "pareto-phase-decisions.json"

CONVERGENCE_THRESHOLD = 0.15   # switch to Phase 2 when gap < 15%
EPSILON_TOL           = 0.10   # allow 10% slack on primary in Phase 2

# Route catalogue with (primary_score, secondary_score) tuples
# primary  = speed/cost efficiency (lower=better)
# secondary = coverage/quality (higher=better)
ROUTES = {
    "direct_tool":       {"cost": 0.10, "quality": 0.60},
    "single_skill":      {"cost": 0.20, "quality": 0.75},
    "parallel_skills":   {"cost": 0.45, "quality": 0.90},
    "subagent_delegate": {"cost": 0.60, "quality": 0.95},
    "cached_result":     {"cost": 0.05, "quality": 0.50},
    "web_search_first":  {"cost": 0.30, "quality": 0.70},
    "multi_hop_rag":     {"cost": 0.55, "quality": 0.88},
}


def _task_complexity(task: str) -> float:
    """Estimate complexity 0-1 from task description."""
    high = len(re.findall(
        r"(?i)\b(comprehensive|all|every|parallel|multi|complex|research|implement|build|consolidat|architect|design|pipeline|system)\b", task
    ))
    low  = len(re.findall(r"(?i)\b(quick|simple|one|single|check|read|list)\b", task))
    return max(0.1, min(0.1 + high * 0.15 - low * 0.05, 1.0))


def route(task: str) -> dict:
    complexity = _task_complexity(task)

    # Phase 1: find min-cost route
    best_route = min(ROUTES.items(), key=lambda x: x[1]["cost"])
    best_cost  = best_route[1]["cost"]

    # Convergence gap: difference between best and worst cost, normalised
    all_costs = [v["cost"] for v in ROUTES.values()]
    gap = (max(all_costs) - best_cost) / max(max(all_costs), 1e-6)
    converged = gap < CONVERGENCE_THRESHOLD or complexity < 0.3

    if converged and complexity < 0.3:
        # Phase 1: use cheapest route
        phase     = 1
        selected  = [best_route[0]]
        rationale = f"low complexity ({complexity:.2f}) → converge to cheapest"
    else:
        # Phase 2: diversify within ε_tol of best cost, maximise quality
        phase2_candidates = [
            (name, v) for name, v in ROUTES.items()
            if v["cost"] <= best_cost * (1 + EPSILON_TOL)
               or v["quality"] >= 0.85  # always include high-quality routes for complex tasks
        ]
        # Pareto-filter: keep non-dominated
        pareto = []
        for name, v in phase2_candidates:
            dominated = any(
                other["cost"] <= v["cost"] and other["quality"] >= v["quality"]
                and (other["cost"] < v["cost"] or other["quality"] > v["quality"])
                for _, other in phase2_candidates if _ != name
            )
            if not dominated:
                pareto.append(name)

        phase     = 2
        selected  = pareto if pareto else [best_route[0]]
        rationale = (f"complexity={complexity:.2f} → diversify; "
                     f"{len(selected)} Pareto-optimal routes")

    return {
        "task":        task[:80],
        "complexity":  round(complexity, 3),
        "phase":       phase,
        "selected":    selected,
        "best_cost":   round(best_cost, 3),
        "rationale":   rationale,
    }


def run(task: str, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    demo_tasks = [
        task,
        "read a config file",
        "implement comprehensive research pipeline in parallel",
        "check if a skill exists",
        "build multi-agent memory consolidation system",
    ] if task == "route agent task to best skill" else [task]

    print(f"\n=== Pareto Phase Router — {now[:10]} ===")
    print(f"  {'Task':<48} Ph  Selected routes")
    print("  " + "-" * 80)

    results = []
    for t in demo_tasks:
        r = route(t)
        print(f"  {r['task'][:47]:<48} {r['phase']}   {', '.join(r['selected'])}")
        print(f"      {r['rationale']}")
        results.append(r)

    if not dry_run:
        OUT_FILE.write_text(json.dumps({"ts": now, "results": results}, indent=2))

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task",      default="route agent task to best skill")
    p.add_argument("--dry-run",   action="store_true")
    args = p.parse_args()
    sys.exit(run(args.task, args.dry_run))


if __name__ == "__main__":
    main()
