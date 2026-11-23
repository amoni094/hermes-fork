#!/usr/bin/python3
"""
relay-routing-capacity-allocator.py

Automatically routes multi-tool workflows toward the cooperation mode
that maximizes information throughput under capacity constraints.

Math basis: relay channel capacity (information theory)
  For a decode-and-forward relay: C_relay = min(I(X;Y_r), I(X,X_r;Y))
  For direct path:               C_direct = I(X;Y)
  Choose relay when C_relay > C_direct + RELAY_OVERHEAD.
  
  Operationally: model tool chains as relay channels where intermediate
  tools (X_r) can amplify or corrupt the signal.
    I(X;Y_r)   ≈ task_clarity × tool_reliability[intermediate]
    I(X,X_r;Y) ≈ task_clarity × tool_reliability[final] × relay_gain
    relay_gain = 1 + synergy(intermediate, final)

Usage:
  python3 relay-routing-capacity-allocator.py --task TASK
  python3 relay-routing-capacity-allocator.py --dry-run
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
OUT_FILE  = CACHE_DIR / "relay-routing-decisions.json"

RELAY_OVERHEAD = 0.05   # capacity units; relay must exceed direct by this much

# Tool reliability estimates (0-1 proxy)
TOOL_RELIABILITY: dict[str, float] = {
    "terminal":       0.95,
    "web_search":     0.75,
    "web_extract":    0.80,
    "execute_code":   0.90,
    "read_file":      0.98,
    "write_file":     0.97,
    "skill_view":     0.92,
    "browser_exec":   0.70,
    "delegate_task":  0.85,
    "memory":         0.88,
}

# Tool pair synergies (intermediate → final amplification)
SYNERGIES: dict[tuple[str,str], float] = {
    ("web_search",  "web_extract"):   0.30,
    ("web_extract", "execute_code"):  0.15,
    ("skill_view",  "terminal"):      0.20,
    ("read_file",   "execute_code"):  0.25,
    ("web_search",  "memory"):        0.10,
    ("execute_code","write_file"):    0.20,
    ("delegate_task","memory"):       0.15,
}


def _task_clarity(task: str) -> float:
    words   = task.split()
    specific = len(re.findall(r'["\']|\d+|\.py|\.json|exactly|specific', task))
    vague   = len(re.findall(r'(?i)\b(maybe|somehow|anything|everything)\b', task))
    clarity = min(len(words)/15, 1.0) + specific*0.05 - vague*0.10
    return max(0.2, min(clarity, 1.0))


def route(task: str, tools: list[str]) -> dict:
    clarity = _task_clarity(task)
    results = []

    for i, final in enumerate(tools):
        r_final = TOOL_RELIABILITY.get(final, 0.75)
        c_direct = clarity * r_final

        # Find best relay through each other tool
        best_relay_cap = 0.0
        best_relay_via = None
        for intermediate in tools:
            if intermediate == final:
                continue
            r_inter   = TOOL_RELIABILITY.get(intermediate, 0.75)
            synergy   = SYNERGIES.get((intermediate, final), 0.0)
            relay_gain = 1.0 + synergy
            c_to_relay = clarity * r_inter
            c_relay_to_final = clarity * r_final * relay_gain
            c_relay = min(c_to_relay, c_relay_to_final)
            if c_relay > best_relay_cap:
                best_relay_cap = c_relay
                best_relay_via = intermediate

        use_relay = best_relay_cap > c_direct + RELAY_OVERHEAD
        results.append({
            "tool":         final,
            "c_direct":     round(c_direct, 4),
            "c_relay":      round(best_relay_cap, 4),
            "relay_via":    best_relay_via,
            "mode":         "RELAY" if use_relay else "DIRECT",
        })

    return {
        "task":    task[:80],
        "clarity": round(clarity, 3),
        "routes":  results,
    }


def run(task: str, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    demo_tasks = [
        task,
        "search web and extract content for research",
        "read config file and execute script",
        "delegate to subagent and store result in memory",
    ] if task == "route multi-tool workflow" else [task]

    print(f"\n=== Relay Routing Capacity Allocator — {now[:10]} ===")
    results = []

    for t in demo_tasks:
        # Pick relevant tools based on task keywords
        candidate_tools = [
            k for k in TOOL_RELIABILITY
            if any(w in t.lower() for w in k.replace("_"," ").split())
        ] or list(TOOL_RELIABILITY.keys())[:4]

        r = route(t, candidate_tools)
        print(f"\n  Task: \"{r['task'][:60]}\"  clarity={r['clarity']:.3f}")
        print(f"  {'Tool':<20} {'Direct':>8} {'Relay':>8}  {'Via':<20} Mode")
        print("  " + "-" * 68)
        for item in r["routes"]:
            print(f"  {item['tool']:<20} {item['c_direct']:>8.4f} {item['c_relay']:>8.4f}"
                  f"  {(item['relay_via'] or '-'):<20} {item['mode']}")
        results.append(r)

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "results": results}, indent=2))
        _tmp_out_file.replace(OUT_FILE)

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task",    default="route multi-tool workflow")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.task, args.dry_run))


if __name__ == "__main__":
    main()
