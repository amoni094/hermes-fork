#!/usr/bin/python3
"""
explanation-narrativizer.py

Enables multi-audience explainability routing: agents can serve technical
summaries, executive briefings, or plain-language explanations of tool
call sequences and outcomes from the same session trace.

Research basis (arXiv core agent sweep — data storytelling + IML):
  Interpretable ML findings show that explanation quality degrades when a
  single format is used for all audiences. This script extracts the raw
  event trace from a session and routes it through audience-specific
  narrative templates: TECHNICAL (full trace), EXECUTIVE (outcome + risk),
  PLAIN (what happened in plain English).

Math basis: audience-conditioned explanation as a projection operator
  Let T = full trace tensor (events × features)
  Let A = audience selector ∈ {technical, executive, plain}
  Narrative(T, A) = P_A(T) where P_A is a linear projection onto the
  audience-relevant feature subspace. Compression ratio = dim(P_A)/dim(T).

Usage:
  python3 explanation-narrativizer.py --session SESSION_ID --audience executive
  python3 explanation-narrativizer.py --audience plain --dry-run
  python3 explanation-narrativizer.py --all-audiences --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
SESSIONS_DIR = HOME / ".hermes/profiles/fork/sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = CACHE_DIR / "explanation-narratives.json"

AUDIENCES = ("technical", "executive", "plain")


def _load_session(path: Path) -> list[dict]:
    events = []
    for line in path.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except Exception:
            pass
    return events


def _extract_events(events: list[dict]) -> list[dict]:
    """Extract tool calls, results, and key decisions."""
    extracted = []
    for ev in events:
        content = ev.get("api_content", ev.get("content", ""))
        role    = ev.get("role", "")

        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type", "")
                if btype == "tool_use":
                    extracted.append({
                        "kind":   "tool_call",
                        "tool":   block.get("name", "unknown"),
                        "args":   str(block.get("input", ""))[:150],
                        "role":   role,
                    })
                elif btype == "tool_result":
                    rc = block.get("content", "")
                    if isinstance(rc, list):
                        rc = " ".join(b.get("text","") for b in rc if isinstance(b,dict))
                    extracted.append({
                        "kind":    "tool_result",
                        "content": str(rc)[:200],
                        "role":    role,
                    })
        elif isinstance(content, str) and content.strip():
            extracted.append({
                "kind":    "message",
                "content": content[:200],
                "role":    role,
            })
    return extracted


def _tool_summary(events: list[dict]) -> dict:
    calls   = [e for e in events if e["kind"] == "tool_call"]
    results = [e for e in events if e["kind"] == "tool_result"]
    errors  = [e for e in results if re.search(r"(?i)error|fail|traceback", e.get("content",""))]
    tool_counts: dict[str, int] = {}
    for c in calls:
        tool_counts[c["tool"]] = tool_counts.get(c["tool"], 0) + 1
    return {
        "total_calls":  len(calls),
        "total_results": len(results),
        "error_count":  len(errors),
        "tools_used":   tool_counts,
        "top_tool":     max(tool_counts, key=lambda k: tool_counts[k]) if tool_counts else "none",
    }


def narrativize(events: list[dict], audience: str, session_id: str) -> str:
    extracted = _extract_events(events)
    summary   = _tool_summary(extracted)
    messages  = [e for e in extracted if e["kind"] == "message" and e["role"] == "user"]
    first_req = messages[0]["content"][:100] if messages else "unknown request"

    if audience == "technical":
        lines = [
            f"Session: {session_id}",
            f"Tool calls: {summary['total_calls']} | Results: {summary['total_results']} | Errors: {summary['error_count']}",
            f"Tools used: {json.dumps(summary['tools_used'])}",
            f"Initial request: {first_req}",
            "",
            "Event trace (tool calls):",
        ]
        calls = [e for e in extracted if e["kind"] == "tool_call"]
        for i, c in enumerate(calls[:20], 1):
            lines.append(f"  {i:02d}. {c['tool']:<22} args={c['args'][:60]}")
        if len(calls) > 20:
            lines.append(f"  ... and {len(calls)-20} more calls")
        return "\n".join(lines)

    elif audience == "executive":
        outcome = "succeeded" if summary["error_count"] == 0 else f"encountered {summary['error_count']} error(s)"
        risk    = "LOW" if summary["error_count"] == 0 else ("HIGH" if summary["error_count"] > 2 else "MEDIUM")
        return "\n".join([
            f"Summary for session {session_id[:12]}",
            f"Request:  {first_req}",
            f"Outcome:  Agent {outcome}",
            f"Actions:  {summary['total_calls']} tool invocations; primary tool: {summary['top_tool']}",
            f"Risk:     {risk}",
        ])

    else:  # plain
        tools_list = ", ".join(list(summary["tools_used"])[:4]) or "no tools"
        outcome    = "finished successfully" if summary["error_count"] == 0 else "ran into some problems"
        return (
            f"The agent worked on: '{first_req}'. "
            f"It used {summary['total_calls']} actions ({tools_list}) and {outcome}."
        )


def run(session_id: str | None, audience: str, all_audiences: bool, dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))

    if not paths:
        print("[narrativizer] No sessions found")
        return 0

    if session_id:
        paths = [p for p in paths if session_id in p.stem]
    path = paths[-1]  # most recent

    events    = _load_session(path)
    audiences = AUDIENCES if all_audiences else (audience,)

    print(f"\n=== Explanation Narrativizer — {now[:10]} ===")
    print(f"Session: {path.stem}")
    print(f"Events:  {len(events)} raw lines\n")

    narratives: dict[str, str] = {}
    for aud in audiences:
        narrative = narrativize(events, aud, path.stem)
        narratives[aud] = narrative
        print(f"── {aud.upper()} ──")
        print(narrative)
        print()

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now, "session": path.stem, "narratives": narratives,
        }, indent=2))
        print(f"Written: {OUT_FILE}")

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--session",      default=None)
    p.add_argument("--audience",     choices=list(AUDIENCES), default="executive")
    p.add_argument("--all-audiences", action="store_true")
    p.add_argument("--dry-run",      action="store_true")
    args = p.parse_args()
    sys.exit(run(args.session, args.audience, args.all_audiences, args.dry_run))


if __name__ == "__main__":
    main()
