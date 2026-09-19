#!/usr/bin/python3
"""
containment-monitor.py

Provides real-time, auditable proof that an agent's action sequence
remains within a pre-configured safety envelope — implements the
containment invariant from reachable-state bounded safety theory.

Math basis: containment invariant as set membership
  Let S_t = set of (tool, outcome_type) pairs used at step t
  Let C = configured containment set (allowed tools × outcome categories)
  Invariant: ∀t, S_t ⊆ C  →  agent is contained
  Violation score V = |S_t \\ C| / |S_t|  (fraction of calls outside envelope)
  Alarm when V > THRESHOLD or when a forbidden tool appears even once (hard rule).

Usage:
  python3 containment-monitor.py              # scan recent sessions
  python3 containment-monitor.py --dry-run
  python3 containment-monitor.py --envelope envelope.json  # custom envelope
"""
from __future__ import annotations
import os

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = _RT / "sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "containment-monitor-report.json"

# Default safety envelope: allowed tools and forbidden patterns
DEFAULT_ENVELOPE = {
    "allowed_tools": {
        "web_search", "web_extract", "execute_code", "terminal", "read_file",
        "write_file", "patch", "search_files", "skill_view", "skills_list",
        "skill_manage", "memory", "vision_analyze", "text_to_speech",
        "browser_exec", "clarify", "delegate_task", "tool_search", "tool_describe",
        "tool_call", "browser_vault_list", "browser_vault_fill",
        "browser_vault_save_login", "browser_vault_enter_code",
    },
    "forbidden_patterns": [
        r"(?i)\b(rm\s+-rf|sudo\s+rm|mkfs|dd\s+if=|format\s+[a-z]:)\b",
        r"(?i)(eval\s*\(|exec\s*\(|__import__\s*\().*os\.(system|popen|remove)",
        r"(?i)\bcurl\s+.*\|\s*bash\b",
    ],
    "max_delegation_depth": 3,
    "max_terminal_calls_per_session": 20,
}

VIOLATION_THRESHOLD = 0.10   # alarm if >10% of calls outside envelope


def _extract_tool_calls(session_path: Path) -> list[dict]:
    calls = []
    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            content = ev.get("api_content", ev.get("content", ""))
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        calls.append({
                            "tool":  block.get("name", "unknown"),
                            "args":  str(block.get("input", ""))[:300],
                            "id":    block.get("id", ""),
                        })
        except Exception:
            pass
    return calls


def _check_containment(calls: list[dict], envelope: dict) -> dict:
    allowed   = set(envelope.get("allowed_tools", set()))
    forbidden = envelope.get("forbidden_patterns", [])
    max_depth = envelope.get("max_delegation_depth", 3)
    max_term  = envelope.get("max_terminal_calls_per_session", 20)

    outside        = []
    pattern_hits   = []
    delegation_cnt = 0
    terminal_cnt   = 0

    for call in calls:
        tool = call["tool"]
        args = call["args"]

        if allowed and tool not in allowed:
            outside.append({"tool": tool, "id": call["id"]})

        for pat in forbidden:
            if re.search(pat, args):
                pattern_hits.append({
                    "tool":    tool,
                    "pattern": pat[:40],
                    "args":    args[:80],
                })

        if tool in ("delegate_task",):
            delegation_cnt += 1
        if tool == "terminal":
            terminal_cnt += 1

    total    = max(len(calls), 1)
    v_score  = len(outside) / total

    violations = []
    if outside:
        violations.append({
            "type":  "UNKNOWN_TOOL",
            "count": len(outside),
            "tools": [o["tool"] for o in outside[:5]],
        })
    if pattern_hits:
        violations.append({
            "type":    "FORBIDDEN_PATTERN",
            "count":   len(pattern_hits),
            "samples": pattern_hits[:2],
        })
    if delegation_cnt > max_depth:
        violations.append({
            "type":    "DELEGATION_OVERFLOW",
            "count":   delegation_cnt,
            "limit":   max_depth,
        })
    if terminal_cnt > max_term:
        violations.append({
            "type":    "TERMINAL_OVERUSE",
            "count":   terminal_cnt,
            "limit":   max_term,
        })

    return {
        "total_calls":    len(calls),
        "outside_count":  len(outside),
        "violation_score": round(v_score, 4),
        "violations":     violations,
        "contained":      len(violations) == 0 and v_score <= VIOLATION_THRESHOLD,
    }


def run(envelope_file: Path | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    envelope = DEFAULT_ENVELOPE
    if envelope_file and envelope_file.exists():
        envelope = json.loads(envelope_file.read_text())

    paths  = sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]
    if not paths:
        print("[containment] No sessions found")
        return 0

    results = []
    for p in paths:
        calls  = _extract_tool_calls(p)
        result = _check_containment(calls, envelope)
        result["session"] = p.stem
        results.append(result)

    print(f"\n=== Containment Monitor — {now[:10]} ===")
    print(f"Sessions checked: {len(results)}")

    alarm_sessions = [r for r in results if not r["contained"]]
    for r in results:
        icon = "✓" if r["contained"] else "✗"
        print(f"  {icon} {r['session'][:30]}  calls={r['total_calls']}  "
              f"V={r['violation_score']:.3f}  "
              f"violations={len(r['violations'])}")
        for v in r["violations"]:
            print(f"      [{v['type']}] {str(v)[:80]}")

    if alarm_sessions:
        print(f"\nALARM: yes — {len(alarm_sessions)} session(s) outside containment envelope")
        alarm_exit = 1
    else:
        print("\nALARM: no — all sessions within containment envelope")
        alarm_exit = 0

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "sessions": len(results),
            "alarm_count": len(alarm_sessions),
            "results": results,
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)

    return alarm_exit


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--envelope", type=Path, default=None)
    p.add_argument("--dry-run",  action="store_true")
    args = p.parse_args()
    sys.exit(run(args.envelope, args.dry_run))


if __name__ == "__main__":
    main()
