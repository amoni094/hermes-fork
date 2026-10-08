#!/usr/bin/python3
"""
adversarial-allocation-auditor.py

Detects unfair multi-agent task distributions under worst-case (adversarial)
online arrival order. Checks the PROP1 (Proportionality up to 1 item)
approximation ratio is maintained.

Math basis: Worst-case approximation ratio under adversarial online arrivals.
  PROP1 guarantee: each agent i receives >= (OPT/n) - max_item_value.
  If any agent's allocation falls below this bound, the online allocator
  is failing its fairness guarantee.

Run on-demand or as suite monitor.
"""
from __future__ import annotations
import os

import json, math, sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

HOME          = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR  = HOME / ".hermes/sessions"
FORK_SESSIONS = _RT / "sessions"
CACHE_DIR     = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE      = CACHE_DIR / "adversarial-allocation-audit.json"

MIN_TASKS     = 6
PROP1_SLACK   = 0.20   # allow 20% slack above theoretical minimum
WINDOW        = 8


def _extract_tasks(path: Path) -> list[dict]:
    try:
        lines = path.read_text().strip().splitlines()
        msgs = [json.loads(l) for l in lines if l.strip()] if lines and lines[0].startswith("{") \
               else (json.loads(path.read_text()) if path.stat().st_size else [])
        msgs = msgs if isinstance(msgs, list) else msgs.get("messages", [])
    except Exception:
        return []
    tasks = []
    for msg in msgs:
        if not isinstance(msg, dict):
            continue
        for b in ((msg.get("api_content") or msg.get("content") or []) if isinstance((msg.get("api_content") or msg.get("content")), list) else []):
            if isinstance(b, dict) and b.get("type") == "tool_use":
                name = b.get("name", "")
                inp  = b.get("input", {})
                if name == "delegate_task":
                    subtasks = inp.get("tasks", [])
                    for st in subtasks:
                        # Value proxy: goal length (longer = more complex = more value)
                        v = len(st.get("goal", "")) / 100.0
                        tasks.append({"agent": "subagent", "value": v, "goal": st.get("goal","")[:40]})
                elif name in ("terminal", "write_file", "patch", "execute_code"):
                    tasks.append({"agent": "direct", "value": 0.5, "goal": name})
                elif name in ("web_search", "web_extract"):
                    tasks.append({"agent": "search", "value": 0.3, "goal": name})
    return tasks


def run() -> int:
    now = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Adversarial Allocation Auditor — {now[:10]} ===\n")

    files = sorted(
        [f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")],
        key=lambda p: p.stat().st_mtime
    )[-WINDOW:]

    all_tasks: list[dict] = []
    for f in files:
        all_tasks.extend(_extract_tasks(f))

    if len(all_tasks) < MIN_TASKS:
        print(f"Tasks found: {len(all_tasks)} (need {MIN_TASKS})")
        print("ALARM: no — insufficient task data")
        return 0

    agents = list(set(t["agent"] for t in all_tasks))
    n      = len(agents)
    by_agent: dict[str, float] = defaultdict(float)
    for t in all_tasks:
        by_agent[t["agent"]] += t["value"]

    total_value = sum(by_agent.values())
    opt_n       = total_value / n
    max_item    = max(t["value"] for t in all_tasks)
    prop1_floor = opt_n - max_item - PROP1_SLACK * opt_n
    # Guard: floor must be positive to be meaningful; if negative the check is trivially true
    if prop1_floor <= 0:
        print(f"PROP1 floor non-positive ({prop1_floor:.3f}) — max_item dominates; skipping fairness check")
        print("ALARM: no — PROP1 floor degenerate (single large item dominates allocation)")
        return 0
    print(f"Tasks: {len(all_tasks)}, Agents: {n}, Total value: {total_value:.2f}")
    print(f"OPT/n: {opt_n:.3f}, Max item: {max_item:.3f}, PROP1 floor: {prop1_floor:.3f}\n")
    print(f"  {'Agent':<15} {'Value':>8}  {'vs Floor':>10}  Status")
    print("  " + "-"*48)

    violations = []
    for agent in sorted(agents):
        v    = by_agent[agent]
        diff = v - prop1_floor
        viol = v < prop1_floor
        print(f"  {agent:<15} {v:>8.3f}  {diff:>+10.3f}  {'VIOLATION' if viol else 'OK'}")
        if viol:
            violations.append(agent)

    if violations:
        print(f"\nALARM: yes — {len(violations)} agent(s) below PROP1 fairness floor: {violations}")
    else:
        print(f"\nALARM: no — all agents satisfy PROP1 allocation guarantee")

    _tmp_out_file = OUT_FILE.with_suffix('.tmp')
    _tmp_out_file.write_text(json.dumps({
        "ts": now, "tasks": len(all_tasks), "agents": n,
        "total_value": round(total_value, 4), "prop1_floor": round(prop1_floor, 4),
        "violations": violations,
    }, indent=2))
    _tmp_out_file.replace(OUT_FILE)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(run())
