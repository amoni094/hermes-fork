#!/usr/bin/python3
"""
state-concentration-monitor.py

Detects and corrects over-commitment or inconsistent belief updates in
multi-turn agent sessions by monitoring whether the agent's internal
state distribution is becoming too concentrated (over-confident) or
too diffuse (confused).

Math basis: Concentration inequalities + belief update monitoring
  Over-concentration: H(b_t) << H(b_0)  →  agent locked into one path
  Under-concentration: H(b_t) >> H(uniform)  →  agent confused/random
  Healthy range: H_min <= H(b_t) <= H_max
  
  Concentration detected via tool-call entropy over rolling window:
    H_t = -sum_i p_i log p_i  where p_i = freq of tool i in window
  Alarm if H_t < ENTROPY_FLOOR (over-concentrated)
           or H_t > ENTROPY_CEIL (too diffuse)

Usage:
  python3 state-concentration-monitor.py [--session SESSION_FILE]
  
Runs as a monitor in the suite.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import math

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "state-concentration.json"

WINDOW       = 20       # rolling window of tool calls
ENTROPY_FLOOR = 0.40    # min healthy entropy (over-concentrated below this)
ENTROPY_CEIL  = 2.80    # max healthy entropy (too diffuse above this)
MIN_TOOL_CALLS = 10     # skip if fewer tool calls


def _tool_entropy(tool_calls: list[str]) -> float:
    from collections import Counter
    counts = Counter(tool_calls)
    total  = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((c/total) * math.log2(c/total) for c in counts.values())


def _load_recent_tools(session_path: Path) -> list[str]:
    try:
        lines = session_path.read_text().strip().splitlines()
        # Support both JSONL (one message per line) and single-object JSON
        if lines and lines[0].startswith("{") and lines[0].strip().endswith("}") and len(lines) > 1:
            messages = [json.loads(l) for l in lines if l.strip()]
        else:
            data = json.loads(session_path.read_text())
            messages = data if isinstance(data, list) else data.get("messages", [])
    except Exception:
        return []
    tools = []
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tools.append(block.get("name", "unknown"))
    return tools[-WINDOW:]


def run() -> int:
    now = datetime.now(timezone.utc).isoformat()

    # Find most recent session
    if not SESSIONS_DIR.exists():
        print("[state-concentration] No sessions directory found")
        print("ALARM: no — insufficient data")
        return 0

    sessions = sorted(SESSIONS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not sessions:
        print("[state-concentration] No session files found")
        print("ALARM: no — insufficient data")
        return 0

    # Check top 3 most recent sessions
    alarms   = []
    results  = []
    checked  = 0

    for sess in sessions[:5]:
        tools = _load_recent_tools(sess)
        if len(tools) < MIN_TOOL_CALLS:
            continue

        H   = _tool_entropy(tools)
        checked += 1

        over_conc  = H < ENTROPY_FLOOR
        too_diffuse = H > ENTROPY_CEIL
        status = ("OVER_CONCENTRATED" if over_conc
                  else "TOO_DIFFUSE" if too_diffuse
                  else "healthy")

        result = {
            "session": sess.name[:40],
            "tool_calls": len(tools),
            "entropy": round(H, 4),
            "status": status,
            "floor": ENTROPY_FLOOR,
            "ceil":  ENTROPY_CEIL,
        }
        results.append(result)
        if over_conc or too_diffuse:
            alarms.append(result)

        icon = "⚠" if (over_conc or too_diffuse) else "✓"
        print(f"  {icon} {sess.name[:35]:<35} H={H:.4f}  {status}")

    if checked == 0:
        print("[state-concentration] All recent sessions too small (<10 tool calls)")
        print("ALARM: no — insufficient data")
        return 0

    print(f"\nChecked: {checked}  Alarms: {len(alarms)}")

    alarm = len(alarms) > 0
    if alarm:
        print(f"ALARM: yes — state concentration anomaly in {len(alarms)} session(s)")
    else:
        print("ALARM: no — all session tool entropies in healthy range")

    OUT_FILE.write_text(json.dumps({
        "ts": now, "checked": checked,
        "alarms": len(alarms), "results": results,
    }, indent=2))

    return 1 if alarm else 0


if __name__ == "__main__":
    print(f"\n=== State Concentration Monitor — {datetime.now(timezone.utc).date()} ===\n")
    sys.exit(run())
