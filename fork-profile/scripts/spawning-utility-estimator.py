#!/usr/bin/python3
"""
spawning-utility-estimator.py

Eliminates wasteful agent spawning by implementing a computable dominance
test before delegate_task is called — estimates whether spawning a subagent
will yield higher expected utility than handling locally.

Math basis: dominance test as expected-utility comparison
  U_local(task)  = quality_local × (1 - p_fail_local)  - cost_local
  U_spawn(task)  = quality_spawn × (1 - p_fail_spawn)  - cost_spawn - overhead
  Spawn iff U_spawn > U_local + SPAWN_THRESHOLD
  
  Estimated from session history:
    quality_local = avg tool_result length / 500 (proxy for output richness)
    p_fail_local  = fraction of terminal/execute calls with non-zero exit
    cost_local    = number of tool calls × 0.01 (normalised)
    quality_spawn = 0.85 (prior; improves with observed subagent outcomes)
    p_fail_spawn  = 0.20 (prior; subagents fail more often)
    overhead      = 0.30 (fixed delegation overhead)

Usage:
  python3 spawning-utility-estimator.py "implement auth module"
  python3 spawning-utility-estimator.py --task TASK [--dry-run]
  python3 spawning-utility-estimator.py --batch tasks.txt
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "spawning-utility-estimates.json"

# Spawn decision threshold: spawn only if utility gain exceeds this
SPAWN_THRESHOLD = 0.05   # spawn when utility gain exceeds this
P_FAIL_SPAWN    = 0.20
QUALITY_SPAWN   = 0.85
OVERHEAD_SPAWN  = 0.15   # was 0.30 — too high; real delegation cost is moderate

# Task complexity features → local failure rate estimate
COMPLEX_PATTERNS = [
    r"(?i)\b(all|every|entire|comprehensive|exhaustive)\b",
    r"(?i)\b(recursive|multi.?step|pipeline|workflow)\b",
    r"(?i)\b(>500|>1000|large|massive|bulk)\b",
    r"(?i)\b(parallel|concurrent|simultaneous)\b",
]

SIMPLE_PATTERNS = [
    r"(?i)\b(single|one|just|only|quick|brief)\b",
    r"(?i)\b(read|check|list|show|display|print)\b",
]


def _estimate_local_stats() -> dict:
    """Estimate local execution quality and failure rate from recent sessions."""
    paths   = sorted(SESSIONS_DIR.glob("*.jsonl"))[-5:]
    results = []
    fail_signals = 0
    call_count   = 0

    for p in paths:
        for line in p.read_text().splitlines():
            try:
                ev      = json.loads(line)
                content = ev.get("api_content", ev.get("content", ""))
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "tool_use":
                            call_count += 1
                        elif block.get("type") == "tool_result":
                            rc = str(block.get("content", ""))
                            results.append(len(rc))
                            if re.search(r"exit_code.*[1-9]|Error:|Traceback", rc):
                                fail_signals += 1
            except Exception:
                pass

    total_results = max(len(results), 1)
    avg_quality   = min(sum(results) / total_results / 500.0, 1.0)  # proxy
    p_fail        = fail_signals / total_results

    return {
        "quality_local": round(max(avg_quality, 0.60), 4),   # floor at 0.60 when no data
        "p_fail_local":  round(p_fail, 4),
        "avg_result_len": round(sum(results) / total_results, 1) if results else 0,
        "total_calls":    call_count,
        "sessions":       len(paths),
    }


def _task_complexity(task: str) -> float:
    """0-1 complexity score from task text."""
    score = 0.0
    for pat in COMPLEX_PATTERNS:
        if re.search(pat, task):
            score += 0.20
    for pat in SIMPLE_PATTERNS:
        if re.search(pat, task):
            score -= 0.10
    # Additional: word count
    words  = len(task.split())
    score += min(words / 50.0, 0.3)
    return max(0.0, min(score, 1.0))


def estimate(task: str, local_stats: dict) -> dict:
    complexity    = _task_complexity(task)
    quality_local = local_stats["quality_local"]
    p_fail_local  = local_stats["p_fail_local"] + complexity * 0.20
    cost_local    = min(complexity * 0.40, 0.80)   # more complex = more tool calls

    u_local = quality_local * (1.0 - p_fail_local) - cost_local
    u_spawn = QUALITY_SPAWN * (1.0 - P_FAIL_SPAWN) - cost_local * 0.5 - OVERHEAD_SPAWN

    gain       = u_spawn - u_local
    should_spawn = gain > SPAWN_THRESHOLD

    return {
        "task":         task[:100],
        "complexity":   round(complexity, 4),
        "u_local":      round(u_local, 4),
        "u_spawn":      round(u_spawn, 4),
        "gain":         round(gain, 4),
        "threshold":    SPAWN_THRESHOLD,
        "decision":     "SPAWN" if should_spawn else "LOCAL",
        "rationale":    (
            f"spawn utility gain {gain:.3f} > threshold {SPAWN_THRESHOLD}" if should_spawn
            else f"local execution preferred (gain {gain:.3f} ≤ threshold {SPAWN_THRESHOLD})"
        ),
    }


def run(tasks: list[str], dry_run: bool) -> int:
    now         = datetime.now(timezone.utc).isoformat()
    local_stats = _estimate_local_stats()

    print(f"\n=== Spawning Utility Estimator — {now[:10]} ===")
    print(f"Local stats: quality={local_stats['quality_local']:.3f}  "
          f"p_fail={local_stats['p_fail_local']:.3f}  "
          f"sessions={local_stats['sessions']}")
    print(f"\n  {'Task':<45} {'Decision':<8} {'Gain':>6}  Rationale")
    print("  " + "-" * 80)

    results    = [estimate(t, local_stats) for t in tasks]
    spawn_recs = [r for r in results if r["decision"] == "SPAWN"]

    for r in results:
        icon = "↑" if r["decision"] == "SPAWN" else "·"
        print(f"  {icon} {r['task'][:44]:<44} {r['decision']:<8} "
              f"{r['gain']:>+6.3f}  {r['rationale'][:50]}")

    print(f"\nRecommend spawn: {len(spawn_recs)}/{len(results)}")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({"ts": now, "local_stats": local_stats,
                                        "estimates": results}, indent=2))
        print(f"Written: {OUT_FILE}")

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("task", nargs="?",
                   default="implement all research findings autonomously end to end")
    p.add_argument("--batch",   type=Path, default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.batch and args.batch.exists():
        tasks = [l.strip() for l in args.batch.read_text().splitlines() if l.strip()]
    else:
        tasks = [
            args.task,
            "read a single file and print its contents",
            "research all arxiv papers and implement every finding",
            "check if a skill exists",
            "run comprehensive multi-agent parallel sweep of entire corpus",
        ]
    sys.exit(run(tasks, args.dry_run))


if __name__ == "__main__":
    main()
