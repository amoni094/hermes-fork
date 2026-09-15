#!/usr/bin/python3
"""
belief-state-threshold-router.py

Reduces expensive skill-routing decisions by replacing full belief-state
computation with threshold policies — only escalates to costly reasoning
when belief state crosses a confidence threshold.

Math basis: optimal threshold policies for POMDPs (arXiv spike)
  For a partially observable resource allocation problem, the optimal
  policy has a threshold structure:
    π*(b) = action_high  if b[s_high] ≥ τ
            action_low   otherwise
  where b = belief state (probability distribution over hidden states),
  τ = threshold (optimal τ minimises expected cost under Bellman equation).
  
  Operationally: b[s_high] proxied by confidence score from belief probe,
  τ calibrated so that low-confidence tasks get escalated to richer routing.

Usage:
  python3 belief-state-threshold-router.py --task TASK [--threshold 0.7]
  python3 belief-state-threshold-router.py --dry-run
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
OUT_FILE  = CACHE_DIR / "belief-threshold-decisions.json"

DEFAULT_THRESHOLD = 0.70   # escalate when confidence < threshold

# Confidence signals from task text
HIGH_CONF_SIGNALS = [
    r"(?i)\b(exactly|specifically|precisely|defined|known|explicit)\b",
    r"(?i)\b(read|list|check|show|print|get)\b",
    r"""['"'][^'"]{2,30}['"']""",     # quoted arguments = specific
    r"\bfile\s+\S+\.\w+\b",          # specific filename
]
LOW_CONF_SIGNALS = [
    r"(?i)\b(maybe|somehow|whatever|anything|everything|all)\b",
    r"(?i)\b(figure out|not sure|unclear|ambiguous|complex)\b",
    r"(?i)\b(research|explore|investigate|discover)\b",
    r"\?",                            # question marks = uncertainty
]

ROUTES = {
    "direct":     {"cost": 0.05, "capability": 0.60},
    "skill":      {"cost": 0.15, "capability": 0.80},
    "web_search": {"cost": 0.30, "capability": 0.85},
    "subagent":   {"cost": 0.60, "capability": 0.95},
    "clarify":    {"cost": 0.10, "capability": 0.70},
}


def _belief_confidence(task: str) -> float:
    """Estimate belief-state confidence in task intent."""
    score = 0.50   # base
    for pat in HIGH_CONF_SIGNALS:
        score += 0.08 * len(re.findall(pat, task))
    for pat in LOW_CONF_SIGNALS:
        score -= 0.10 * len(re.findall(pat, task))
    return max(0.0, min(score, 1.0))


def route(task: str, threshold: float) -> dict:
    confidence = _belief_confidence(task)
    above_threshold = confidence >= threshold

    if above_threshold:
        # High confidence: use cheapest capable route
        best = min(ROUTES.items(), key=lambda x: x[1]["cost"])
        action = best[0]
        rationale = f"confidence={confidence:.3f} ≥ τ={threshold} → cheap route"
    else:
        # Low confidence: escalate to richer reasoning
        # Find minimum-cost route with capability ≥ 0.85
        capable = [(n, v) for n, v in ROUTES.items() if v["capability"] >= 0.85]
        best = min(capable, key=lambda x: x[1]["cost"]) if capable else ("clarify", ROUTES["clarify"])
        action = best[0]
        rationale = f"confidence={confidence:.3f} < τ={threshold} → escalate"

    return {
        "task":       task[:80],
        "confidence": round(confidence, 4),
        "threshold":  threshold,
        "action":     action,
        "cost":       ROUTES[action]["cost"],
        "rationale":  rationale,
    }


def run(task: str, threshold: float, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    demo_tasks = [
        task,
        "read the file 'config.json' and show its contents",
        "figure out somehow what's wrong with the agent",
        "list all files in the current directory",
        "research and discover the best approach to memory compression",
        "check if 'script.py' exists",
    ] if task == "route this task efficiently" else [task]

    print(f"\n=== Belief-State Threshold Router — {now[:10]} ===")
    print(f"Threshold τ={threshold}\n")
    print(f"  {'Task':<50} {'Conf':>6}  {'Action':<12} Cost")
    print("  " + "-" * 78)

    results = []
    escalated = 0
    for t in demo_tasks:
        r = route(t, threshold)
        icon = "↑" if r["confidence"] < threshold else "✓"
        print(f"  {icon} {r['task'][:49]:<50} {r['confidence']:>6.3f}  "
              f"{r['action']:<12} {r['cost']:.3f}")
        results.append(r)
        if r["confidence"] < threshold:
            escalated += 1

    print(f"\nEscalated: {escalated}/{len(results)}")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({"ts": now, "results": results}, indent=2))

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task",      default="route this task efficiently")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    p.add_argument("--dry-run",   action="store_true")
    args = p.parse_args()
    sys.exit(run(args.task, args.threshold, args.dry_run))


if __name__ == "__main__":
    main()
