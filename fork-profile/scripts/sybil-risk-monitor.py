#!/usr/bin/python3
"""
sybil-risk-monitor.py

Detects multi-agent delegation abuse: when a single session spawns an
anomalously large number of subagents, creating Sybil-like amplification
of influence over the shared memory/skill surfaces.

Math basis (random_graphs / distributed systems): in a Sybil-resilient
system, the trust weight assigned to a cluster of identities is bounded
by their connectivity to the honest majority. Here: if a single parent
session spawns N subagents that all write to the same memory/skill surface,
the effective trust amplification is O(N) — indistinguishable from N
independent honest agents. Alarm when N exceeds the Sybil threshold.

Concretely:
  - Mine session logs for delegate_task and subagent-spawn patterns
  - Count concurrent subagent fan-out per parent session
  - Compare against baseline fan-out distribution
  - Alarm when a single session's fan-out > mean + 2σ (Chebyshev bound)
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
SESSIONS  = HOME / ".hermes/sessions"
FORK_SESSIONS = HOME / ".hermes/profiles/fork/sessions"  # fork-profile sessions

CACHE_DIR = HOME / ".hermes/cache/monitors"
ALARM_FILE = CACHE_DIR / "sybil-risk-alarm.json"
OUT_FILE   = CACHE_DIR / "sybil-risk.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

# delegate_task calls in tool_calls
DELEGATE_PAT = re.compile(r"delegate_task")


def _count_delegations(text: str) -> int:
    """Count delegate_task calls in a session."""
    count = 0
    for line in text.split("\n"):
        try:
            obj = json.loads(line)
            if obj.get("role") == "assistant":
                for tc in obj.get("tool_calls", []):
                    if isinstance(tc, dict):
                        if tc.get("function", {}).get("name") == "delegate_task":
                            # Count tasks array length if available
                            args = tc["function"].get("arguments", "{}")
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except Exception:
                                    pass
                            if isinstance(args, dict):
                                tasks = args.get("tasks", [])
                                count += max(1, len(tasks))
                            else:
                                count += 1
        except Exception:
            pass
    return count


def run(dry_run: bool = False) -> None:
    now = datetime.now(timezone.utc).isoformat()
    session_files = sorted([f for d in [SESSIONS, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")])

    fan_out: dict[str, int] = {}
    for sf in session_files:
        try:
            text = sf.read_text()
        except Exception:
            continue
        n = _count_delegations(text)
        fan_out[sf.stem[:20]] = n

    counts = list(fan_out.values())
    total_sessions = len(counts)
    delegating = [c for c in counts if c > 0]

    print(f"\n=== Sybil Risk Monitor — {now[:10]} ===")
    print(f"Sessions scanned:   {total_sessions}")
    print(f"Delegating sessions: {len(delegating)}")

    alarms: list[dict] = []
    if delegating:
        mean = sum(delegating) / len(delegating)
        var  = sum((x - mean) ** 2 for x in delegating) / len(delegating)
        std  = math.sqrt(var)
        threshold = mean + 2 * std

        print(f"Fan-out mean: {mean:.2f},  std: {std:.2f},  threshold: {threshold:.2f}")

        for session, n in fan_out.items():
            if n > threshold and n > 0:
                alarms.append({"session": session, "fan_out": n,
                               "threshold": round(threshold, 2), "z": round((n - mean) / max(std, 0.01), 2)})

        if alarms:
            print(f"\nALARM: yes — {len(alarms)} high-fan-out session(s)")
            for a in alarms:
                print(f"  {a['session']}  fan_out={a['fan_out']}  z={a['z']:.2f}")
        else:
            print("ALARM: no — no anomalous delegation fan-out detected")

        # Top delegators
        top = sorted(fan_out.items(), key=lambda x: -x[1])[:5]
        print(f"\nTop delegating sessions:")
        for s, n in top:
            if n > 0:
                print(f"  {s}: {n} subagent(s)")
    else:
        print("No delegation events in current session history.")

    if not dry_run:
        out = {
            "ts": now, "sessions": total_sessions,
            "delegating": len(delegating),
            "alarms": alarms,
            "fan_out_distribution": dict(sorted(fan_out.items(), key=lambda x: -x[1])[:20]),
        }
        OUT_FILE.write_text(json.dumps(out, indent=2))
        if alarms:
            ALARM_FILE.write_text(json.dumps(alarms, indent=2))
        print(f"Written: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sybil risk monitor for delegation fan-out")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
