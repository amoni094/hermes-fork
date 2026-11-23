#!/usr/bin/python3
"""
proportionality-monitor.py

Enables Hermes to audit and alert on fairness drift when delegating tasks
to multiple sub-agents — detects when cumulative value share falls below
the proportional guarantee.

Math basis: Online proportionality (allocation fairness)
  For n agents over T rounds, agent i receives value v_i(t) per round.
  Proportionality requires: V_i(T) >= (1/n) * V_total(T) for all i.
  
  Proportionality violation: some agent receives strictly less than
  their fair share across cumulative allocations.
  
  Operationally: track task delegation counts per subagent type
  (skill domains). Alert when any domain receives < (1/n - SLACK) share.

Runs as a monitor in the suite.
"""
from __future__ import annotations
import os

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = HOME / ".hermes/sessions"
FORK_SESSIONS = _RT / "sessions"  # fork-profile sessions

CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "proportionality.json"

SLACK        = 0.05   # allow up to 5% below fair share before alarm
MIN_CALLS    = 20     # skip if fewer total tool calls seen
WINDOW       = 5      # sessions to analyse


def _load_tool_calls(sessions: list[Path]) -> Counter:
    """Count tool calls by name across recent sessions."""
    counts: Counter = Counter()
    for sess in sessions[-WINDOW:]:
        try:
            data = json.loads(sess.read_text())
            msgs = data if isinstance(data, list) else data.get("messages", [])
            for m in msgs:
                if not isinstance(m, dict) or m.get("role") != "assistant":
                    continue
                for block in (m.get("content", []) if isinstance(m.get("content"), list) else []):
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        counts[block.get("name", "unknown")] += 1
        except Exception:
            pass
    return counts


def check_proportionality(counts: Counter) -> dict:
    total = sum(counts.values())
    if total < MIN_CALLS:
        return {"total": total, "skip": True}

    n     = len(counts)
    fair  = 1.0 / n if n > 0 else 0.0
    floor = fair - SLACK

    shares  = {name: c / total for name, c in counts.items()}
    violators = {name: share for name, share in shares.items() if share < floor}

    return {
        "total":      total,
        "agents":     n,
        "fair_share": round(fair, 4),
        "floor":      round(floor, 4),
        "violators":  {k: round(v, 4) for k, v in violators.items()},
        "shares":     {k: round(v, 4) for k, v in sorted(shares.items(), key=lambda x: -x[1])},
        "skip":       False,
    }


def run() -> int:
    now = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Proportionality Monitor — {now[:10]} ===\n")

    if not SESSIONS_DIR.exists():
        print("ALARM: no — no sessions directory")
        return 0

    sessions = sorted([f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")], key=lambda p: p.stat().st_mtime)
    if not sessions:
        print("ALARM: no — no sessions found")
        return 0

    counts = _load_tool_calls(sessions)
    result = check_proportionality(counts)

    if result.get("skip"):
        print(f"Total tool calls: {result['total']} (need {MIN_CALLS})")
        print("ALARM: no — insufficient data")
        return 0

    print(f"Tool calls: {result['total']}  Agents: {result['agents']}")
    print(f"Fair share: {result['fair_share']:.4f}  Floor: {result['floor']:.4f}\n")

    print(f"  {'Tool':<35} {'Share':>7}  Status")
    print("  " + "-" * 50)
    for name, share in list(result["shares"].items())[:10]:
        icon = "✗" if name in result["violators"] else "✓"
        print(f"  {icon} {name:<35} {share:>7.4f}")

    alarm = bool(result["violators"])
    print(f"\nViolators: {len(result['violators'])}")
    if alarm:
        print(f"ALARM: yes — {len(result['violators'])} tool(s) below proportional floor "
              f"{result['floor']:.4f}: {list(result['violators'].keys())[:3]}")
    else:
        print("ALARM: no — all tools above proportional floor")

    _tmp_out_file = OUT_FILE.with_suffix('.tmp')
    _tmp_out_file.write_text(json.dumps({"ts": now, **result}, indent=2))
    _tmp_out_file.replace(OUT_FILE)
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(run())
