#!/usr/bin/python3
"""
real-options-deployment-gate.py

Implements staged commitment logic for Hermes subagent fan-out — uses
real-options theory to decide when to commit resources to irreversible
deployments vs. waiting for more information.

Research basis ("Pilot Early, Commit Late: A Real-Options Model of Enterprise AI"):
  Irreversible decisions (spawning expensive subagents, writing large files,
  deploying changes) have option value in deferral. This script computes
  the option value of waiting vs. committing, blocking premature fan-out.

Math basis: real-options value of deferral (Black-Scholes approximation)
  V_wait = max(0, V_commit × N(d1) - Cost × N(d2) × e^(-r×T))
  where d1 = (ln(V/K) + (r + σ²/2)T) / (σ√T)
        d2 = d1 - σ√T
  Operationalised for agent decisions:
    V_commit  = expected_utility(task)
    Cost      = delegation_cost (tokens, time)
    σ         = uncertainty (1 - task_clarity)
    T         = time_horizon (steps remaining)
    r         = 0.05 (discount rate)
  DEFER when V_wait > V_commit × DEFER_THRESHOLD.

Usage:
  python3 real-options-deployment-gate.py "implement complex multi-agent pipeline"
  python3 real-options-deployment-gate.py --task TASK [--uncertainty 0.5]
  python3 real-options-deployment-gate.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "real-options-gate-decisions.json"

DEFER_THRESHOLD = 0.65   # commit when V_commit ≥ 65% of total value
RISK_FREE_RATE  = 0.05
DEFAULT_HORIZON = 2      # was 5; 2 steps is realistic for single-task decisions


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _task_clarity(task: str) -> float:
    """Estimate task clarity from 0 (vague) to 1 (precise)."""
    words = task.split()
    # Precision signals: specific filenames, numbers, quoted strings, tool names
    specific = len(re.findall(r'["\']|\.py|\.json|\d+|specific|exactly|only', task))
    vague    = len(re.findall(
        r"(?i)\b(maybe|perhaps|somehow|whatever|everything|anything|all)\b", task
    ))
    base     = min(len(words) / 20.0, 1.0)   # longer = more specified
    clarity  = base + specific * 0.05 - vague * 0.10
    return max(0.1, min(clarity, 1.0))


def _delegation_cost(task: str) -> float:
    """Estimate delegation cost (0-1 normalised)."""
    # High cost signals
    high = len(re.findall(
        r"(?i)\b(all|every|entire|comprehensive|parallel|multi.?agent|sweep)\b", task
    ))
    low  = len(re.findall(r"(?i)\b(single|one|quick|check|read|list)\b", task))
    cost = 0.20 + high * 0.15 - low * 0.05
    return max(0.05, min(cost, 0.95))


def _expected_utility(task: str) -> float:
    """Rough utility estimate from task value signals."""
    high_value = len(re.findall(
        r"(?i)\b(implement|create|build|deploy|secure|verify|fix|refactor)\b", task
    ))
    return min(0.40 + high_value * 0.10, 1.0)


def real_options_decision(
    task: str,
    uncertainty: float | None = None,
    horizon: int = DEFAULT_HORIZON,
) -> dict:
    clarity    = _task_clarity(task)
    sigma      = uncertainty if uncertainty is not None else (1.0 - clarity)
    cost       = _delegation_cost(task)
    v_commit   = _expected_utility(task)
    K          = cost          # strike price = cost to commit
    T          = max(horizon, 1)
    r          = RISK_FREE_RATE

    # Black-Scholes option value of deferral
    if sigma < 0.01 or T < 0.1:
        v_wait = 0.0
        d1 = d2 = 0.0
    else:
        sqrt_T = math.sqrt(T)
        d1 = (math.log(max(v_commit / K, 1e-9)) + (r + sigma**2 / 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T
        v_wait = max(0.0, v_commit * _norm_cdf(d1) - K * _norm_cdf(d2) * math.exp(-r * T))
    # Scale option value by uncertainty: clear tasks have no benefit from deferral
    v_wait *= sigma

    # Decision: commit if V_commit is sufficiently larger than wait value
    total    = v_commit + v_wait
    commit_ratio = v_commit / total if total > 0 else 1.0
    should_commit = commit_ratio >= DEFER_THRESHOLD

    return {
        "task":          task[:100],
        "clarity":       round(clarity, 4),
        "uncertainty":   round(sigma, 4),
        "v_commit":      round(v_commit, 4),
        "v_wait":        round(v_wait, 4),
        "commit_ratio":  round(commit_ratio, 4),
        "threshold":     DEFER_THRESHOLD,
        "decision":      "COMMIT" if should_commit else "DEFER",
        "rationale": (
            f"commit ratio {commit_ratio:.2f} ≥ {DEFER_THRESHOLD} — proceed"
            if should_commit else
            f"option value of deferral {v_wait:.3f} significant — clarify first"
        ),
    }


def run(task: str, uncertainty: float | None, horizon: int, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    demo_tasks = [
        task,
        "read a single config file and report its contents",
        "implement entire new authentication system from scratch in parallel",
        "check if script exists then run it",
        "deploy comprehensive multi-agent research pipeline to production",
    ] if task == "implement complex multi-agent pipeline" else [task]

    print(f"\n=== Real-Options Deployment Gate — {now[:10]} ===")
    print(f"  {'Task':<50} {'Decision':<8} {'V_commit':>8} {'V_wait':>7}  Rationale")
    print("  " + "-" * 90)

    results = []
    deferred = 0
    for t in demo_tasks:
        r = real_options_decision(t, uncertainty, horizon)
        icon = "✓" if r["decision"] == "COMMIT" else "⏸"
        print(f"  {icon} {r['task'][:49]:<50} {r['decision']:<8} "
              f"{r['v_commit']:>8.3f} {r['v_wait']:>7.3f}  {r['rationale'][:45]}")
        results.append(r)
        if r["decision"] == "DEFER":
            deferred += 1

    print(f"\nDeferred: {deferred}/{len(results)}")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({"ts": now, "decisions": results}, indent=2))
        print(f"Written: {OUT_FILE}")

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("task", nargs="?", default="implement complex multi-agent pipeline")
    p.add_argument("--uncertainty", type=float, default=None)
    p.add_argument("--horizon",     type=int,   default=DEFAULT_HORIZON)
    p.add_argument("--dry-run",     action="store_true")
    args = p.parse_args()
    sys.exit(run(args.task, args.uncertainty, args.horizon, args.dry_run))


if __name__ == "__main__":
    main()
