#!/usr/bin/python3
"""
cost-cutoff-task-router.py

Avoids wasteful over-preparation on low-value tasks while identifying
high-value tasks that warrant deeper investment. Implements a cost-cutoff
threshold based on expected task value vs routing cost.

Math basis: Optimal stopping / cost-cutoff theory
  Given task value V and routing cost C(route):
    Route r* = argmin C(r) s.t. capability(r) >= required_capability(V)
  Cutoff: if V < V_min, use cheapest route regardless of quality.
  If V >= V_max, use highest-capability route regardless of cost.
  In between: linear interpolation of cost/capability tradeoff.

Usage:
  python3 cost-cutoff-task-router.py --dry-run
  python3 cost-cutoff-task-router.py --task TASK [--value 0.5]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = _HH / "cache" / "monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "cost-cutoff-routing.json"

# Value thresholds
V_MIN = 0.25   # below this: always use cheapest route
V_MAX = 0.80   # above this: always use best route

ROUTES = [
    {"name": "direct",    "cost": 0.02, "capability": 0.55},
    {"name": "skill",     "cost": 0.10, "capability": 0.72},
    {"name": "web",       "cost": 0.25, "capability": 0.83},
    {"name": "subagent",  "cost": 0.55, "capability": 0.93},
    {"name": "ensemble",  "cost": 0.90, "capability": 0.98},
]

# Value signals from task text
HIGH_VALUE = [
    r"(?i)\b(critical|urgent|production|deploy|security|money|revenue|risk)\b",
    r"(?i)\b(compliance|legal|audit|regulation|deadline)\b",
    r"(?i)\b(architecture|refactor|migrate|redesign)\b",
]
LOW_VALUE = [
    r"(?i)\b(quick|simple|just|briefly|roughly|estimate)\b",
    r"(?i)\b(curious|wondering|check|peek|glance)\b",
    r"(?i)\b(temp|scratch|test|dummy|placeholder)\b",
]


def _estimate_value(task: str) -> float:
    score = 0.45   # base
    for pat in HIGH_VALUE:
        score += 0.12 * len(re.findall(pat, task))
    for pat in LOW_VALUE:
        score -= 0.10 * len(re.findall(pat, task))
    return max(0.0, min(score, 1.0))


def _required_capability(value: float) -> float:
    """Map task value to required routing capability."""
    if value <= V_MIN:
        return 0.0    # any route acceptable
    if value >= V_MAX:
        return 0.93   # need subagent or better
    # Linear interpolation
    return 0.55 + (value - V_MIN) / (V_MAX - V_MIN) * (0.93 - 0.55)


def route(task: str, value_override: float | None = None) -> dict:
    value   = value_override if value_override is not None else _estimate_value(task)
    req_cap = _required_capability(value)

    # Find cheapest route meeting capability requirement
    candidates = [r for r in ROUTES if r["capability"] >= req_cap]
    if not candidates:
        candidates = ROUTES   # fallback to all

    chosen = min(candidates, key=lambda r: r["cost"])

    tier = "LOW"  if value < V_MIN else ("HIGH" if value >= V_MAX else "MID")

    return {
        "task":       task[:80],
        "value":      round(value, 3),
        "tier":       tier,
        "req_cap":    round(req_cap, 3),
        "route":      chosen["name"],
        "cost":       chosen["cost"],
        "capability": chosen["capability"],
    }


def run(task: str, value_override: float | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    demo = [
        ("quickly peek at the log file",             None),
        ("check roughly how many files exist",       None),
        ("deploy the payment service to production", None),
        ("critical security audit of auth module",   None),
        ("refactor the database migration layer",    None),
        ("estimate token count",                     None),
        (task,                                       value_override),
    ] if task == "route this task" else [(task, value_override)]

    print(f"\n=== Cost-Cutoff Task Router — {now[:10]} ===")
    print(f"V_min={V_MIN}  V_max={V_MAX}\n")
    print(f"  {'Task':<48} {'Val':>5} {'Tier':<5} {'Route':<10} Cost")
    print("  " + "-" * 78)

    results = []
    for t, v in demo:
        r = route(t, v)
        print(f"  {r['task'][:48]:<48} {r['value']:>5.3f} {r['tier']:<5} "
              f"{r['route']:<10} {r['cost']:.3f}")
        results.append(r)

    print("\nALARM: no — routing decisions complete")
    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "results": results}, indent=2))
        _tmp_out_file.replace(OUT_FILE)
    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task",  default="route this task")
    p.add_argument("--value", type=float, default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.task, args.value, args.dry_run))


if __name__ == "__main__":
    main()
