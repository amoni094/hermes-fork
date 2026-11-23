#!/usr/bin/python3
"""
cot-injection-detector.py

Monitors CoT (chain-of-thought) reasoning traces for plan-injection attacks
— detects when actor reasoning contains context-injected instructions that
diverge from the original user task intent.

Research basis ("Corrupt Plans, Clean Traces: Evading Chain-of-Thought Oversight"):
  Adversarial inputs can corrupt an agent's internal plan while leaving the
  visible trace clean. This script detects divergence between the stated
  plan and the observed tool calls, flagging mismatches as potential injections.

Math basis: plan-trace alignment as Jaccard distance on intent vectors
  intent_plan  = keywords extracted from assistant reasoning/plan text
  intent_trace = tools + args used in subsequent tool calls
  mismatch = 1 - |intent_plan ∩ intent_trace| / |intent_plan ∪ intent_trace|
  INJECTION_RISK when mismatch > MISMATCH_THRESHOLD or when trace contains
  tools not mentioned in any plan step.

Usage:
  python3 cot-injection-detector.py              # scan recent sessions
  python3 cot-injection-detector.py --dry-run
  python3 cot-injection-detector.py --session SESSION_ID
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
OUT_FILE     = CACHE_DIR / "cot-injection-report.json"

MISMATCH_THRESHOLD = 0.70   # flag if plan-trace Jaccard distance > 0.70

# Suspicious injection patterns in reasoning text
INJECTION_PATTERNS = [
    re.compile(r"(?i)(ignore (previous|prior|above|all) instructions)"),
    re.compile(r"(?i)(new (task|instruction|objective|goal):)"),
    re.compile(r"(?i)(you are now|act as|pretend (you are|to be))"),
    re.compile(r"(?i)(system prompt:|<system>|<\|im_start\|>)"),
    re.compile(r"(?i)(forget (everything|what|your|the) (above|previous))"),
    re.compile(r"(?i)(disregard|override|bypass) (your |the )?(instructions|constraints|guidelines)"),
]

# Tool → intent keyword mapping
TOOL_INTENT = {
    "web_search":    {"search", "find", "lookup", "research", "news"},
    "web_extract":   {"fetch", "read", "extract", "page", "url", "content"},
    "execute_code":  {"run", "execute", "compute", "code", "script", "test"},
    "terminal":      {"run", "shell", "command", "install", "build", "debug"},
    "write_file":    {"write", "save", "create", "output", "file"},
    "read_file":     {"read", "load", "check", "inspect", "file"},
    "patch":         {"edit", "modify", "fix", "update", "change"},
    "skill_view":    {"skill", "load", "procedure", "workflow"},
    "skill_manage":  {"skill", "create", "update", "manage"},
    "delegate_task": {"delegate", "spawn", "subagent", "parallel"},
    "memory":        {"remember", "store", "persist", "recall"},
    "clarify":       {"ask", "clarify", "question", "confirm"},
}


def _extract_events(session_path: Path) -> list[dict]:
    events = []
    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            content = ev.get("api_content", ev.get("content", ""))
            role    = ev.get("role", "")

            if isinstance(content, str):
                events.append({"role": role, "type": "text", "text": content})
            elif isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type", "")
                    if btype == "text":
                        events.append({"role": role, "type": "text",
                                        "text": block.get("text", "")})
                    elif btype == "tool_use":
                        events.append({"role": role, "type": "tool_use",
                                        "tool": block.get("name", ""),
                                        "args": str(block.get("input", ""))[:200]})
        except Exception:
            pass
    return events


def _plan_keywords(events: list[dict]) -> set[str]:
    """Keywords from assistant text before first tool call."""
    kws: set[str] = set()
    for ev in events:
        if ev["type"] == "tool_use":
            break
        if ev["role"] == "assistant" and ev["type"] == "text":
            kws |= set(re.findall(r"[a-z]{4,}", ev["text"].lower()))
    return kws


def _trace_keywords(events: list[dict]) -> set[str]:
    """Keywords implied by actual tool calls."""
    kws: set[str] = set()
    for ev in events:
        if ev["type"] == "tool_use":
            tool = ev.get("tool", "")
            kws |= TOOL_INTENT.get(tool, set())
            kws |= set(re.findall(r"[a-z]{4,}", ev.get("args", "").lower()))
    return kws


def _injection_patterns_found(events: list[dict]) -> list[str]:
    hits = []
    for ev in events:
        if ev["type"] == "text":
            for pat in INJECTION_PATTERNS:
                m = pat.search(ev["text"])
                if m:
                    hits.append(m.group()[:60])
    return hits


def analyse_session(session_path: Path) -> dict:
    events       = _extract_events(session_path)
    plan_kws     = _plan_keywords(events)
    trace_kws    = _trace_keywords(events)
    injections   = _injection_patterns_found(events)

    tool_calls   = [e for e in events if e["type"] == "tool_use"]
    if not tool_calls:
        return {
            "session":  session_path.stem,
            "note":     "no tool calls",
            "risk":     False,
        }

    # Jaccard distance between plan intent and trace intent
    union        = plan_kws | trace_kws
    intersect    = plan_kws & trace_kws
    mismatch     = 1.0 - (len(intersect) / len(union)) if union else 0.0

    # Unplanned tools: tools used but not mentioned in plan text
    plan_text    = " ".join(re.findall(r"[a-z]+", " ".join(plan_kws)))
    unplanned    = [e["tool"] for e in tool_calls
                   if e["tool"] not in plan_text and e["tool"] != "unknown"]

    risk         = mismatch > MISMATCH_THRESHOLD or bool(injections)

    return {
        "session":           session_path.stem,
        "tool_calls":        len(tool_calls),
        "plan_kws":          len(plan_kws),
        "trace_kws":         len(trace_kws),
        "mismatch":          round(mismatch, 4),
        "unplanned_tools":   list(set(unplanned))[:5],
        "injection_patterns": injections[:3],
        "risk":              risk,
    }


def run(session_id: str | None, dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))
    if session_id:
        paths = [p for p in paths if session_id in p.stem]
    else:
        paths = paths[-10:]

    if not paths:
        print("[cot-detector] No sessions found")
        return 0

    results   = [analyse_session(p) for p in paths]
    at_risk   = [r for r in results if r.get("risk")]

    print(f"\n=== CoT Injection Detector — {now[:10]} ===")
    print(f"Sessions analysed: {len(results)}")
    for r in results:
        if "note" in r:
            print(f"  · {r['session'][:30]}  {r['note']}")
        else:
            icon = "✗" if r["risk"] else "✓"
            print(f"  {icon} {r['session'][:30]}  "
                  f"mismatch={r['mismatch']:.3f}  "
                  f"unplanned={r['unplanned_tools'][:2]}  "
                  f"injections={len(r['injection_patterns'])}")

    if at_risk:
        print(f"\nALARM: yes — {len(at_risk)} session(s) show injection risk")
        alarm_exit = 1
    else:
        print(f"\nALARM: no — no injection patterns detected")
        alarm_exit = 0

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "results": results}, indent=2))
        _tmp_out_file.replace(OUT_FILE)

    return alarm_exit


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--session", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.session, args.dry_run))


if __name__ == "__main__":
    main()
