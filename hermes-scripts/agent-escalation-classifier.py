#!/usr/bin/python3
"""
agent-escalation-classifier.py

Enables Hermes to predict and steer agent behavior during impossible-task
scenarios — classifying whether a task will likely escalate (loop, crash,
or exceed budget) before committing resources.

Research basis (arXiv core agent sweep — agent escalation/collapse detection):
  LLM agents collapse in predictable patterns when encountering impossible
  tasks: (a) tool-loop (same tool called >N times), (b) context saturation,
  (c) delegation cascade (infinite subagent spawning), (d) schema fixation
  (agent keeps reformatting the same wrong answer). Early classification
  enables preemptive steering.

Math basis: escalation risk as a multi-class logistic classifier
  Features:
    - task_ambiguity: fraction of task words without known tool mapping
    - external_dependency: requires external service / login / live data
    - constraint_conflict: task contains contradictory requirements
    - scope_breadth: number of distinct intent dimensions in task
    - delegation_depth_needed: estimated delegation depth
  
  Classes: SAFE | LOOP_RISK | CONTEXT_RISK | CASCADE_RISK | IMPOSSIBLE

Usage:
  python3 agent-escalation-classifier.py "some task description"
  python3 agent-escalation-classifier.py --batch tasks.txt
  python3 agent-escalation-classifier.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "escalation-classifications.json"

# Known tool intent keywords (from agent-action-planner manifest)
KNOWN_INTENTS = {
    "search", "find", "lookup", "research", "fetch", "read", "extract",
    "write", "create", "edit", "fix", "update", "patch", "run", "execute",
    "test", "debug", "verify", "compile", "deploy", "implement", "build",
    "delegate", "spawn", "remember", "load", "save", "review", "summarise",
    "analyse", "ask", "clarify", "speak", "image", "screenshot",
}

# Patterns that indicate external/impossible requirements
EXTERNAL_PATTERNS = [
    r"(?i)\b(login|authenticate|2fa|password|secret|api.?key)\b",
    r"(?i)\b(real.?time|live|streaming|websocket|push notification)\b",
    r"(?i)\b(call me|phone|sms|whatsapp|telegram)\b",
    r"(?i)\b(purchase|buy|order|pay|checkout|credit.?card)\b",
]

CONTRADICTION_PATTERNS = [
    (r"(?i)\bfast\b", r"(?i)\bthorough\b"),
    (r"(?i)\bsimple\b", r"(?i)\bcomprehensive\b"),
    (r"(?i)\bno.?llm\b", r"(?i)\bgenerate|summarize|explain\b"),
    (r"(?i)\boffline\b", r"(?i)\bsearch|fetch|download\b"),
]

# Escalation class weights (logistic regression coefficients, hand-calibrated)
# Features: [ambiguity, external, contradiction, scope_breadth, delegation_depth, task_len]
CLASS_WEIGHTS = {
    "SAFE":         np.array([-1.5, -2.0, -2.0, -0.5, -1.0, -0.2]),
    "LOOP_RISK":    np.array([ 0.8,  0.0,  0.5,  1.2,  0.0,  0.1]),
    "CONTEXT_RISK": np.array([ 0.5,  0.5,  0.3,  1.5,  0.5,  0.8]),
    "CASCADE_RISK": np.array([ 0.3,  1.0,  0.5,  0.8,  2.0,  0.2]),
    "IMPOSSIBLE":   np.array([ 1.5,  2.0,  2.5,  0.5,  1.5,  0.0]),
}
BIAS = {"SAFE": 2.0, "LOOP_RISK": -1.0, "CONTEXT_RISK": -1.5,
        "CASCADE_RISK": -2.0, "IMPOSSIBLE": -3.0}


def _extract_features(task: str) -> np.ndarray:
    words = re.findall(r"[a-z]{3,}", task.lower())
    total = max(len(words), 1)

    # 1. Ambiguity: fraction of words not in known intent vocabulary
    unmapped = [w for w in words if w not in KNOWN_INTENTS]
    ambiguity = len(unmapped) / total

    # 2. External dependency
    external = float(any(re.search(p, task) for p in EXTERNAL_PATTERNS))

    # 3. Contradiction
    contradiction = float(any(
        re.search(pa, task) and re.search(pb, task)
        for pa, pb in CONTRADICTION_PATTERNS
    ))

    # 4. Scope breadth: distinct intent dimensions
    dims_hit = set()
    dim_map = {
        "research": {"search","find","research","read","fetch"},
        "implement": {"write","create","implement","build","code"},
        "verify": {"test","verify","check","validate","debug"},
        "delegate": {"delegate","spawn","parallel","subagent"},
        "memory": {"remember","store","save","persist"},
    }
    for w in words:
        for dim, kws in dim_map.items():
            if w in kws:
                dims_hit.add(dim)
    scope_breadth = len(dims_hit) / 5.0

    # 5. Delegation depth: count of "then" / "after" / nested clauses
    delegation_depth = min(
        len(re.findall(r"\bthen\b|\bafter\b|\bfollowed by\b", task, re.IGNORECASE)) / 3.0,
        1.0
    )

    # 6. Task length normalised
    task_len = min(len(task) / 500.0, 1.0)

    return np.array([ambiguity, external, contradiction, scope_breadth,
                     delegation_depth, task_len])


def _softmax(scores: dict) -> dict[str, float]:
    keys = list(scores.keys())
    vals = np.array([scores[k] for k in keys])
    exp_v = np.exp(vals - vals.max())
    probs = exp_v / exp_v.sum()
    return {k: round(float(p), 4) for k, p in zip(keys, probs)}


def classify(task: str) -> dict:
    fv = _extract_features(task)
    raw_scores = {
        cls: float(np.dot(CLASS_WEIGHTS[cls], fv)) + BIAS[cls]
        for cls in CLASS_WEIGHTS
    }
    probs = _softmax(raw_scores)
    prediction = max(probs, key=lambda k: probs[k])

    risk_level = {
        "SAFE": "low", "LOOP_RISK": "medium",
        "CONTEXT_RISK": "medium", "CASCADE_RISK": "high", "IMPOSSIBLE": "critical",
    }[prediction]

    recommendations = {
        "SAFE":         "proceed normally",
        "LOOP_RISK":    "set max_tool_calls limit; break on repeated same-tool pattern",
        "CONTEXT_RISK": "split task; use background=True; prefer delegate_task",
        "CASCADE_RISK": "cap delegation depth to 2; require explicit scope per subagent",
        "IMPOSSIBLE":   "clarify with user before proceeding; task may have no valid completion",
    }

    return {
        "task":        task[:100],
        "prediction":  prediction,
        "risk":        risk_level,
        "probabilities": probs,
        "features": {
            "ambiguity":        round(float(fv[0]), 3),
            "external_dep":     round(float(fv[1]), 3),
            "contradiction":    round(float(fv[2]), 3),
            "scope_breadth":    round(float(fv[3]), 3),
            "delegation_depth": round(float(fv[4]), 3),
            "task_length":      round(float(fv[5]), 3),
        },
        "recommendation": recommendations[prediction],
    }


def run(tasks: list[str], dry_run: bool) -> int:
    now     = datetime.now(timezone.utc).isoformat()
    results = [classify(t) for t in tasks]

    print(f"\n=== Agent Escalation Classifier — {now[:10]} ===")
    print(f"Tasks classified: {len(results)}")
    print(f"\n  {'Task':<40} {'Class':<14} {'Risk':<10} {'P(pred)'}")
    print("  " + "-" * 75)
    for r in results:
        print(f"  {r['task'][:39]:<40} {r['prediction']:<14} "
              f"{r['risk']:<10} {r['probabilities'][r['prediction']]:.3f}")
        if r["risk"] in ("high", "critical"):
            print(f"    → {r['recommendation']}")

    high_risk = [r for r in results if r["risk"] in ("high", "critical")]
    if high_risk:
        print(f"\nALARM: yes — {len(high_risk)} high/critical escalation risk task(s)")
        alarm_exit = 1
    else:
        print(f"\nALARM: no — all tasks classified as low/medium risk")
        alarm_exit = 0

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now, "classifications": results,
        }, indent=2))
        print(f"\nWritten: {OUT_FILE}")

    return alarm_exit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", nargs="?",
                        default="research all papers and implement every finding autonomously")
    parser.add_argument("--batch", type=Path, default=None,
                        help="File with one task per line")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.batch and args.batch.exists():
        tasks = [l.strip() for l in args.batch.read_text().splitlines() if l.strip()]
    else:
        tasks = [args.task]

    import sys
    sys.exit(run(tasks=tasks, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
