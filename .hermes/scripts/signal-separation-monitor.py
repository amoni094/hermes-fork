#!/usr/bin/python3
"""
signal-separation-monitor.py

Detects delayed generalisation windows in multi-turn sessions: the gap
between when a tool/skill first appears and when it gets reused effectively
(i.e., stops generating errors or retries). High separation = the agent is
slow to integrate new tools — a signal to update skill routing priors.

Math basis: Signal separation in ICA / source separation.
  For each tool T, define:
    first_use(T)  = turn index of first call
    effective(T)  = turn index where success rate first exceeds FLOOR
  Separation S(T) = effective(T) - first_use(T)
  High mean S = slow integration; alarm if mean_S > SEP_THRESHOLD turns.
"""
from __future__ import annotations
import os

import json, sys
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
OUT_FILE      = CACHE_DIR / "signal-separation.json"

SEP_THRESHOLD = 8    # turns; above = slow integration
SUCCESS_FLOOR = 0.70 # tool call success rate to count as "effective"
MIN_TOOLS     = 5
WINDOW        = 5


def _parse(path: Path) -> list[dict]:
    """Return list of {turn, tool, success} dicts."""
    try:
        lines = path.read_text().strip().splitlines()
        msgs = [json.loads(l) for l in lines if l.strip()] if lines and lines[0].startswith("{") \
               else (json.loads(path.read_text()) if path.stat().st_size else [])
        msgs = msgs if isinstance(msgs, list) else msgs.get("messages", [])
    except Exception:
        return []
    events = []
    turn = 0
    for msg in msgs:
        role = msg.get("role", "")
        if role == "assistant":
            for b in ((msg.get("api_content") or msg.get("content") or []) if isinstance((msg.get("api_content") or msg.get("content")), list) else []):
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    events.append({"turn": turn, "tool": b.get("name", "?"), "success": None})
        elif role == "tool":
            # Tool results: role='tool' in Hermes session format
            content = str(msg.get("content", ""))
            ok = not any(w in content.lower() for w in
                         ["error", "exception", "traceback", "failed", "exit_code: 1"])
            for e in reversed(events):
                if e["success"] is None:
                    e["success"] = ok
                    break
        turn += 1
    return events


def run() -> int:
    now = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Signal Separation Monitor — {now[:10]} ===\n")

    files = sorted(
        [f for d in [SESSIONS_DIR, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")],
        key=lambda p: p.stat().st_mtime
    )[-WINDOW:]

    all_events: list[dict] = []
    for f in files:
        all_events.extend(_parse(f))

    # Per-tool: track first use and first window where success_rate >= FLOOR
    by_tool: dict[str, list] = defaultdict(list)
    for e in all_events:
        by_tool[e["tool"]].append(e)

    if len(by_tool) < MIN_TOOLS:
        print(f"Tools seen: {len(by_tool)} (need {MIN_TOOLS})")
        print("ALARM: no — insufficient data")
        return 0

    separations = []
    print(f"  {'Tool':<35} {'First':>6} {'Effective':>10} {'Sep':>5}")
    print("  " + "-"*60)
    for tool, evts in sorted(by_tool.items()):
        evts_s = sorted(evts, key=lambda e: e["turn"])
        first  = evts_s[0]["turn"]
        # Find first turn where rolling 3-call success rate >= FLOOR
        effective = None
        for i in range(2, len(evts_s)):
            window = evts_s[max(0, i-2):i+1]
            ok = sum(1 for e in window if e.get("success"))
            if len(window) > 0 and ok / len(window) >= SUCCESS_FLOOR:
                effective = evts_s[i]["turn"]
                break
        if effective is None:
            sep = "N/A"
        else:
            sep = effective - first
            separations.append(sep)
        print(f"  {tool:<35} {first:>6} {str(effective):>10} {str(sep):>5}")

    if not separations:
        print("\nALARM: no — no tools with enough calls to compute separation")
        return 0

    mean_sep = sum(separations) / len(separations)
    print(f"\nTools with separation: {len(separations)}, Mean separation: {mean_sep:.1f} turns")

    alarm = mean_sep > SEP_THRESHOLD
    if alarm:
        print(f"\nALARM: yes — mean tool integration gap {mean_sep:.1f} turns exceeds {SEP_THRESHOLD}; routing priors may be stale")
    else:
        print(f"\nALARM: no — tool integration gap healthy ({mean_sep:.1f} turns)")

    _tmp_out_file = OUT_FILE.with_suffix('.tmp')
    _tmp_out_file.write_text(json.dumps({
        "ts": now, "tools": len(by_tool), "mean_sep": round(mean_sep, 2),
        "threshold": SEP_THRESHOLD, "alarm": alarm, "separations": separations,
    }, indent=2))
    _tmp_out_file.replace(OUT_FILE)
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(run())
