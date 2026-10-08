#!/usr/bin/python3
"""
participation-surplus-monitor.py

Monitors per-agent participation surplus in multi-agent delegation:
detects when subagent utility V_i(T) falls below its fair share
(1/n) * V_total — i.e., an agent is being systematically under-utilised
or over-burdened relative to the delegation pool.

Math basis: Pathwise federated participation bound (wave12).
  Guarantee: sum_{t=1}^{T} V_i(t) >= (1/n) * sum_{t=1}^{T} V(t) - O(sqrt(T))
  Alarm when any agent's running surplus deficit exceeds sqrt(T) bound.

Operationally: reads delegate_task call logs from session files.
  V_i(t) = 1 if subagent i produced a useful result in round t, 0 otherwise.
  Proxy for "useful": subagent returned without error and result len > 200 chars.
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
OUT_FILE      = CACHE_DIR / "participation-surplus.json"

MIN_DELEGATIONS = 5
DEFICIT_K       = 1.5   # alarm if deficit > K * sqrt(T)
WINDOW          = 8


def _extract_delegations(path: Path) -> list[dict]:
    """Extract delegate_task calls and their result sizes."""
    try:
        lines = path.read_text().strip().splitlines()
        msgs = [json.loads(l) for l in lines if l.strip()] if lines and lines[0].startswith("{") \
               else (json.loads(path.read_text()) if path.stat().st_size else [])
        msgs = msgs if isinstance(msgs, list) else msgs.get("messages", [])
    except Exception:
        return []
    delegations = []
    pending: dict[str, str] = {}  # tool_use_id -> subagent label

    for msg in msgs:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")

        # Collect delegate_task calls from assistant messages
        if role == "assistant":
            # Check api_content (Anthropic tool_use blocks) and tool_calls (OpenAI format)
            for source in [msg.get("api_content"), msg.get("content")]:
                if isinstance(source, list):
                    for b in source:
                        if not isinstance(b, dict):
                            continue
                        if b.get("type") == "tool_use" and b.get("name") == "delegate_task":
                            tid = b.get("id", "?")
                            tasks = b.get("input", {}).get("tasks", [{}])
                            label = tasks[0].get("goal", "subagent")[:30] if tasks else "subagent"
                            pending[tid] = label
            # OpenAI tool_calls format
            for tc in (msg.get("tool_calls") or []):
                if isinstance(tc, dict) and tc.get("function", {}).get("name") == "delegate_task":
                    tid = tc.get("id", "?")
                    try:
                        inp = json.loads(tc["function"].get("arguments", "{}"))
                        tasks = inp.get("tasks", [{}])
                        label = tasks[0].get("goal", "subagent")[:30] if tasks else "subagent"
                    except Exception:
                        label = "subagent"
                    pending[tid] = label

        # Tool results arrive as role='tool' messages in Hermes session format
        elif role == "tool":
            tid = msg.get("tool_call_id", msg.get("tool_use_id", "?"))
            if tid in pending:
                content = str(msg.get("content", ""))
                useful  = len(content) > 200 and "error" not in content.lower()
                delegations.append({"agent": pending.pop(tid), "useful": useful})

    return delegations


def run() -> int:
    now = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Participation Surplus Monitor — {now[:10]} ===\n")

    files = sorted(
        [f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")],
        key=lambda p: p.stat().st_mtime
    )[-WINDOW:]

    all_delegations: list[dict] = []
    for f in files:
        all_delegations.extend(_extract_delegations(f))

    if len(all_delegations) < MIN_DELEGATIONS:
        print(f"Delegations found: {len(all_delegations)} (need {MIN_DELEGATIONS})")
        print("ALARM: no — insufficient delegation data")
        return 0

    T  = len(all_delegations)
    n  = len(set(d["agent"] for d in all_delegations))
    V_total = sum(1 for d in all_delegations if d["useful"])
    fair_share = V_total / max(n, 1)
    bound = DEFICIT_K * math.sqrt(T)

    by_agent: dict[str, int] = defaultdict(int)
    for d in all_delegations:
        if d["useful"]:
            by_agent[d["agent"]] += 1

    print(f"Total delegations: {T}, Agents: {n}, Useful: {V_total}")
    print(f"Fair share per agent: {fair_share:.1f}, Surplus bound: ±{bound:.1f}\n")
    print(f"  {'Agent':<35} {'Useful':>7} {'Deficit':>8}  Status")
    print("  " + "-"*60)

    alarms = []
    for agent in sorted(set(d["agent"] for d in all_delegations)):
        v = by_agent[agent]
        deficit = fair_share - v
        over = deficit > bound
        print(f"  {agent:<35} {v:>7} {deficit:>8.1f}  {'ALARM' if over else 'OK'}")
        if over:
            alarms.append(agent)

    if alarms:
        print(f"\nALARM: yes — {len(alarms)} agent(s) below fair-share surplus bound: {alarms}")
    else:
        print(f"\nALARM: no — all agents within participation surplus bounds")

    _tmp_out_file = OUT_FILE.with_suffix('.tmp')
    _tmp_out_file.write_text(json.dumps({
        "ts": now, "T": T, "n": n, "V_total": V_total,
        "fair_share": round(fair_share, 2), "bound": round(bound, 2),
        "alarm_agents": alarms,
    }, indent=2))
    _tmp_out_file.replace(OUT_FILE)
    return 1 if alarms else 0


if __name__ == "__main__":
    sys.exit(run())
