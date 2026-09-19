#!/usr/bin/python3
"""
horizon-constraint-validator.py

Enables multi-step task planning to verify that tool sequences and state
transitions satisfy safety/feasibility constraints at every planning
horizon — prevents constraint violations before execution.

Math basis: Control Barrier Functions (CBFs) for non-control-affine systems
  A function h: X → R is a CBF if there exists α (class-K function) s.t.
    sup_u [∂h/∂x · f(x,u)] ≥ -α(h(x))   for all x in safe set {h(x) ≥ 0}
  
  Operationally: h(state) = distance to constraint boundary.
  A plan step is SAFE if h(next_state) ≥ 0.
  A plan step is UNSAFE if h(next_state) < 0 (crosses boundary).
  We check each (state → tool → next_state) transition horizon.

Usage:
  python3 horizon-constraint-validator.py --dry-run
  python3 horizon-constraint-validator.py --plan STEP1 STEP2 ...
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
OUT_FILE  = CACHE_DIR / "horizon-constraint-validation.json"

# Constraint boundaries: h(state) >= 0 means safe
# Each constraint is a tuple (name, check_fn: state_dict -> float)
# Positive = safe margin, Negative = violated
CONSTRAINTS = {
    "no_delete_without_backup": lambda s: (
        0.5 if not any(w in s.get("action","").lower()
                       for w in ["delete","remove","rm","drop","wipe"])
        else (-0.5 if not s.get("has_backup") else 0.3)
    ),
    "no_external_write_in_readonly_mode": lambda s: (
        0.5 if not s.get("readonly_mode")
        else (0.5 if not any(w in s.get("action","").lower()
                             for w in ["write","post","send","push","upload"])
              else -0.8)
    ),
    "rate_limit_budget": lambda s: (
        max(-1.0, 0.5 - max(0, s.get("api_calls_this_minute", 0) - 5) * 0.15)
    ),
    "max_subagent_depth": lambda s: (
        0.5 - max(0, s.get("subagent_depth", 0) - 3) * 0.4
    ),
    "no_credential_in_args": lambda s: (
        -1.0 if re.search(r"(?i)(password|secret|token|api.?key)\s*=\s*\S",
                          s.get("action", ""))
        else 0.5
    ),
}


def check_step(state: dict) -> dict:
    """Check all constraints for a single plan step."""
    results = {}
    min_margin = float("inf")
    for name, fn in CONSTRAINTS.items():
        h = float(fn(state))
        results[name] = round(h, 4)
        min_margin = min(min_margin, h)

    violated = [n for n, h in results.items() if h < 0]
    return {
        "action":     state.get("action", "")[:60],
        "min_margin": round(min_margin, 4),
        "safe":       min_margin >= 0,
        "violated":   violated,
        "constraints": results,
    }


def validate_plan(plan_steps: list[dict]) -> dict:
    """Validate a multi-step plan over full horizon."""
    step_results = []
    violations   = 0

    for i, step in enumerate(plan_steps):
        r = check_step(step)
        step_results.append({"step": i + 1, **r})
        if not r["safe"]:
            violations += 1

    return {
        "total_steps":  len(plan_steps),
        "violations":   violations,
        "plan_safe":    violations == 0,
        "steps":        step_results,
    }


def run(plan: list[dict] | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    if plan is None:
        # Demo: a mixed-safety multi-step plan
        plan = [
            {"action": "read file config.json",         "has_backup": False, "readonly_mode": False, "api_calls_this_minute": 0, "subagent_depth": 0},
            {"action": "write output to results.txt",   "has_backup": True,  "readonly_mode": False, "api_calls_this_minute": 2, "subagent_depth": 1},
            {"action": "delete temp/scratch.db",        "has_backup": False, "readonly_mode": False, "api_calls_this_minute": 3, "subagent_depth": 1},
            {"action": "send results via web_extract",  "has_backup": True,  "readonly_mode": True,  "api_calls_this_minute": 4, "subagent_depth": 1},
            {"action": "spawn subagent depth=4 summarize", "has_backup": True, "readonly_mode": False, "api_calls_this_minute": 6, "subagent_depth": 4},
            {"action": "archive final.zip",             "has_backup": True,  "readonly_mode": False, "api_calls_this_minute": 1, "subagent_depth": 0},
        ]

    result = validate_plan(plan)

    print(f"\n=== Horizon Constraint Validator — {now[:10]} ===")
    print(f"Plan steps: {result['total_steps']}  "
          f"Violations: {result['violations']}  "
          f"{'SAFE' if result['plan_safe'] else 'UNSAFE'}\n")

    print(f"  {'Step':<4} {'Action':<45} {'Margin':>7}  Status")
    print("  " + "-" * 72)
    for s in result["steps"]:
        icon = "✓" if s["safe"] else "✗"
        print(f"  {icon} {s['step']:<3} {s['action']:<45} {s['min_margin']:>7.4f}  "
              f"{'OK' if s['safe'] else 'VIOLATED: ' + ', '.join(s['violated'])}")

    print()
    if result["plan_safe"]:
        print("ALARM: no — all plan steps satisfy constraints at every horizon")
    else:
        print(f"ALARM: yes — {result['violations']} constraint violations in plan horizon")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, **result}, indent=2))
        _tmp_out_file.replace(OUT_FILE)

    return 1 if not result["plan_safe"] else 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--plan",    nargs="+", default=None,
                   help="JSON-encoded plan steps (or omit for demo)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    plan = None
    if args.plan:
        plan = [json.loads(s) for s in args.plan]

    sys.exit(run(plan, args.dry_run))


if __name__ == "__main__":
    main()
