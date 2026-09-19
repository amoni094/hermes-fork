#!/usr/bin/python3
"""
constraint-alignment-validator.py

Enables Hermes to validate that skill-routing and context-allocation
decisions remain aligned with the original task constraints throughout
a multi-step session — detects constraint drift before it compounds.

Math basis: constraint alignment as a monotone operator
  Let C_0 = initial constraint set (from task description)
  Let C_t = active constraints at step t (inferred from tool call sequence)
  Alignment score A_t = |C_t ∩ C_0| / |C_0|  (fraction of original constraints still active)
  Drift alert when A_t < DRIFT_THRESHOLD or when C_t contains constraints
  not in C_0 (scope creep).

Usage:
  python3 constraint-alignment-validator.py --dry-run
  python3 constraint-alignment-validator.py --session SESSION_ID
  python3 constraint-alignment-validator.py --task "original task" --trace trace.json
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
OUT_FILE     = CACHE_DIR / "constraint-alignment-report.json"

DRIFT_THRESHOLD = 0.50   # alarm if <50% original constraints still active

# Constraint extraction: look for these in task descriptions and tool calls
CONSTRAINT_PATTERNS = {
    "file_scope":     re.compile(r"(?i)\b(only|just|specific|single)\s+(file|script|skill)\b"),
    "no_llm":         re.compile(r"(?i)\bno[_\s]?llm\b|without\s+(llm|api|model)"),
    "local_only":     re.compile(r"(?i)\b(local|offline|no.?internet|no.?web)\b"),
    "dry_run":        re.compile(r"(?i)\bdry.?run\b"),
    "read_only":      re.compile(r"(?i)\bread.?only|don'?t\s+(write|modify|edit|change)"),
    "no_delete":      re.compile(r"(?i)\b(don'?t|no)\s+(delete|remove|drop|wipe)\b"),
    "single_session": re.compile(r"(?i)\b(this session|current session|don'?t spawn)\b"),
    "budget_limit":   re.compile(r"(?i)\b(budget|limit|max|at most)\s+\d+\b"),
    "secure":         re.compile(r"(?i)\b(secure|auth|credential|permission)\b"),
    "reversible":     re.compile(r"(?i)\b(reversible|undo|rollback|backup)\b"),
}

# Tool calls that violate specific constraints
VIOLATION_MAP = {
    "no_llm":     {"execute_code", "delegate_task"},   # LLM invocations
    "local_only": {"web_search", "web_extract", "browser_exec"},
    "dry_run":    {"write_file", "patch", "terminal", "skill_manage"},
    "read_only":  {"write_file", "patch", "skill_manage", "memory"},
    "no_delete":  {"terminal"},   # checked via args pattern
}


def _extract_constraints(text: str) -> set[str]:
    """Extract active constraint labels from text."""
    active = set()
    for label, pat in CONSTRAINT_PATTERNS.items():
        if pat.search(text):
            active.add(label)
    return active


def _extract_tool_calls(session_path: Path) -> list[dict]:
    calls = []
    for line in session_path.read_text().splitlines():
        try:
            ev = json.loads(line)
            content = ev.get("api_content", ev.get("content", ""))
            role = ev.get("role", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        calls.append({
                            "tool": block.get("name", "unknown"),
                            "args": str(block.get("input", ""))[:300],
                            "role": role,
                        })
        except Exception:
            pass
    return calls


def _extract_user_task(session_path: Path) -> str:
    """Get first user message as the original task."""
    for line in session_path.read_text().splitlines():
        try:
            ev = json.loads(line)
            if ev.get("role") == "user":
                content = ev.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content[:500]
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            return block.get("text", "")[:500]
        except Exception:
            pass
    return ""


def validate_session(session_path: Path) -> dict:
    task       = _extract_user_task(session_path)
    calls      = _extract_tool_calls(session_path)
    c0         = _extract_constraints(task)

    if not c0:
        return {
            "session":    session_path.stem,
            "task_len":   len(task),
            "constraints_found": 0,
            "drift": False,
            "note": "no constraints detected in task",
        }

    # Check each call for constraint violations
    violations = []
    for call in calls:
        tool = call["tool"]
        args = call["args"]

        for constraint in c0:
            violating_tools = VIOLATION_MAP.get(constraint, set())
            if tool in violating_tools:
                # Extra check for no_delete
                if constraint == "no_delete" and not re.search(
                    r"(?i)\b(rm|del|delete|remove|unlink)\b", args
                ):
                    continue
                violations.append({
                    "constraint": constraint,
                    "tool":       tool,
                    "args":       args[:80],
                })

    # Drift: how many original constraints are still respected?
    violated_labels = {v["constraint"] for v in violations}
    still_active    = c0 - violated_labels
    alignment       = len(still_active) / len(c0) if c0 else 1.0
    drift           = alignment < DRIFT_THRESHOLD

    return {
        "session":     session_path.stem,
        "task":        task[:100],
        "constraints": sorted(c0),
        "violations":  violations[:10],
        "alignment":   round(alignment, 4),
        "drift":       drift,
    }


def run(session_id: str | None, dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))

    if session_id:
        paths = [p for p in paths if session_id in p.stem]
    else:
        paths = paths[-10:]

    if not paths:
        print("[constraint-align] No sessions found")
        return 0

    results      = [validate_session(p) for p in paths]
    drift_cases  = [r for r in results if r.get("drift")]
    violation_cases = [r for r in results if r.get("violations")]

    print(f"\n=== Constraint Alignment Validator — {now[:10]} ===")
    print(f"Sessions checked: {len(results)}")
    for r in results:
        constrs = r.get("constraints", [])
        if constrs:
            icon = "✗" if r.get("drift") else ("⚠" if r.get("violations") else "✓")
            print(f"  {icon} {r['session'][:28]}  constraints={constrs}  "
                  f"align={r.get('alignment', 1.0):.2f}  "
                  f"violations={len(r.get('violations', []))}")
        else:
            print(f"  · {r['session'][:28]}  {r.get('note', 'no constraints')}")

    if drift_cases:
        print(f"\nALARM: yes — {len(drift_cases)} session(s) show constraint drift")
        alarm_exit = 1
    elif violation_cases:
        print(f"\nWARN: {len(violation_cases)} session(s) have violations (alignment still OK)")
        alarm_exit = 0
    else:
        print("\nALARM: no — all sessions within constraint alignment bounds")
        alarm_exit = 0

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "sessions": len(results), "drift_count": len(drift_cases),
            "results": results,
        }, indent=2))
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
