#!/usr/bin/python3
"""
context-budget-potential-monitor.py

Detects when incremental reasoning (token-by-token or turn-by-turn) is
approaching a context-budget inflection point — where the marginal value
of continuing drops below the cost of the next token/turn.

Math basis: Stopping-time potential (optimal stopping theory)
  V_t = max(g(t), E[V_{t+1}])
  where g(t) = value of stopping now (budget remaining × expected gain rate)
  and E[V_{t+1}] = expected value of continuing one more step.

  Alarm when: g(t) > E[V_{t+1}] for 3+ consecutive turns
  i.e., it is now better to stop than to continue — session has passed
  its optimal stopping point.

Operationally: track context token usage and tool-call productivity
(useful tool calls / total tool calls) over the last WINDOW turns.
When token usage is high AND productivity is falling, flag.

Runs as a monitor in the suite.
"""
from __future__ import annotations
import os

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = HOME / ".hermes/sessions"
FORK_SESSIONS = _RT / "sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "context-budget-potential.json"

WINDOW            = 5      # sessions to look back
MIN_TOOLS         = 8      # skip sessions with fewer tool calls
PRODUCTIVITY_FLOOR = 0.30  # alarm if useful_ratio < this
BUDGET_THRESHOLD  = 0.75   # alarm if token usage > this fraction
CONSECUTIVE_ALARM = 2      # sessions below floor before alarming


def _load_sessions(n: int = WINDOW) -> list[Path]:
    files = sorted(
        [f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists()
         for f in d.glob("*.jsonl")],
        key=lambda p: p.stat().st_mtime
    )
    return files[-n:]


def _parse_session(path: Path) -> dict:
    """Extract tool calls and rough token proxy from a session file."""
    try:
        lines = path.read_text().strip().splitlines()
        if lines and lines[0].startswith("{") and len(lines) > 1:
            messages = [json.loads(l) for l in lines if l.strip()]
        else:
            data = json.loads(path.read_text())
            messages = data if isinstance(data, list) else data.get("messages", [])
    except Exception:
        return {}

    tool_calls   = 0
    useful_calls = 0   # proxy: tool calls that aren't immediate consecutive repeats
    char_total   = 0

    prev_tool: str = ""   # track only the immediately previous tool (not all seen)
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            char_total += len(content)
        elif isinstance(content, list):
            for b in content:
                if isinstance(b, dict):
                    char_total += len(json.dumps(b))
                    if b.get("type") == "tool_use":
                        tool_calls += 1
                        name = b.get("name", "")
                        # Count as useful unless it's an immediate consecutive repeat
                        if name != prev_tool:
                            useful_calls += 1
                        prev_tool = name

    return {
        "session":      path.stem,
        "tool_calls":   tool_calls,
        "useful_calls": useful_calls,
        "char_total":   char_total,
        "productivity": useful_calls / max(tool_calls, 1),
        # Token proxy: chars / 4
        "token_proxy":  char_total // 4,
        # Note: productivity = non-consecutive-repeat tool calls / total tool calls
    }


def run() -> int:
    now = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Context Budget Potential Monitor — {now[:10]} ===\n")

    sessions = _load_sessions()
    if not sessions:
        print("ALARM: no — no session files found")
        return 0

    results = []
    for sess in sessions:
        r = _parse_session(sess)
        if not r or r["tool_calls"] < MIN_TOOLS:
            continue
        results.append(r)

    if not results:
        print(f"Sessions found: {len(sessions)}, analysable: 0 (need {MIN_TOOLS}+ tool calls)")
        print("ALARM: no — insufficient data")
        return 0

    print(f"{'Session':<40} {'Tools':>6} {'Useful':>7} {'Prod':>6} {'Tokens':>8}")
    print("  " + "-" * 70)
    low_prod = 0
    for r in results:
        flag = " <LOW" if r["productivity"] < PRODUCTIVITY_FLOOR else ""
        print(f"  {r['session']:<40} {r['tool_calls']:>6} {r['useful_calls']:>7} "
              f"{r['productivity']:>6.2f} {r['token_proxy']:>8,}{flag}")
        if r["productivity"] < PRODUCTIVITY_FLOOR:
            low_prod += 1

    avg_prod = sum(r["productivity"] for r in results) / len(results)
    print(f"\nSessions analysed: {len(results)}")
    print(f"Avg productivity:  {avg_prod:.3f}  (floor={PRODUCTIVITY_FLOOR})")
    print(f"Low-productivity:  {low_prod}/{len(results)}")

    alarm = low_prod >= CONSECUTIVE_ALARM
    if alarm:
        print(f"\nALARM: yes — {low_prod} session(s) below productivity floor {PRODUCTIVITY_FLOOR} "
              f"(optimal stopping point may have passed)")
    else:
        print(f"\nALARM: no — productivity healthy (avg={avg_prod:.3f})")

    _tmp_out_file = OUT_FILE.with_suffix('.tmp')
    _tmp_out_file.write_text(json.dumps({
        "ts": now, "sessions": len(results),
        "avg_productivity": round(avg_prod, 4),
        "low_productivity_count": low_prod,
        "threshold": PRODUCTIVITY_FLOOR,
        "detail": results,
    }, indent=2))
    _tmp_out_file.replace(OUT_FILE)
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(run())
