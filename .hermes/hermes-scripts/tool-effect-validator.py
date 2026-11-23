#!/usr/bin/python3
"""
tool-effect-validator.py

Enables autonomous detection and reporting of workflow-tool boundary
failures: verifies that each tool call in a session produced the
expected side effects (file written, command exit 0, data returned).

Research basis (arXiv core agent sweep — tool effect validation):
  After each tool call, validate that the expected effect occurred.
  If a tool call produced no observable effect (empty output, non-zero
  exit, file not created), flag it as a workflow boundary failure.

Math basis: effect postcondition checking as a monotone predicate
  Let E_i = expected_effect(tool_i, args_i)
  Let O_i = observed_effect(tool_i, result_i)
  Failure condition: E_i ∧ ¬O_i (expected but not observed)

  Predicate types per tool class:
    write_file → file exists at claimed path with non-zero size
    terminal   → exit_code == 0 AND output is non-empty
    web_search → results list is non-empty
    patch      → file modified time changed
    execute_code → no exception in output

Usage:
  python3 tool-effect-validator.py [--dry-run]
  python3 tool-effect-validator.py --session 20260915_...
  python3 tool-effect-validator.py --check-file ~/.hermes/scripts/foo.py
"""

from __future__ import annotations

import argparse
import json
import os
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
OUT_FILE     = CACHE_DIR / "tool-effect-report.json"

# --- Effect predicate definitions ---

def _check_write_file(args: dict, result_text: str) -> tuple[bool, str]:
    """write_file → target file must exist with non-zero content."""
    path = args.get("path", "")
    if not path:
        return True, "no path in args"
    p = Path(path)
    if not p.exists():
        return False, f"file not created: {path}"
    if p.stat().st_size == 0:
        return False, f"file created but empty: {path}"
    return True, f"file exists ({p.stat().st_size} bytes)"


def _check_terminal(args: dict, result_text: str) -> tuple[bool, str]:
    """terminal → exit_code 0 and non-empty output."""
    # Look for exit_code in result JSON
    exit_match = re.search(r'"exit_code"\s*:\s*(\d+)', result_text)
    if exit_match:
        code = int(exit_match.group(1))
        if code != 0:
            return False, f"exit_code={code} (non-zero)"
    out_match = re.search(r'"output"\s*:\s*"([^"]{5,})"', result_text)
    if not out_match and "output" not in result_text:
        return False, "empty output"
    return True, "exit 0, non-empty output"


def _check_web_search(args: dict, result_text: str) -> tuple[bool, str]:
    """web_search → must have at least one result."""
    if '"url"' not in result_text and '"title"' not in result_text:
        return False, "no results (no url/title in output)"
    return True, "results present"


def _check_patch(args: dict, result_text: str) -> tuple[bool, str]:
    """patch → diff must show actual changes."""
    if "no_change" in result_text and '"no_change": true' in result_text:
        return False, "patch applied but no change (already applied?)"
    if "diff" not in result_text.lower() and "success" not in result_text.lower():
        return False, "no diff or success indicator in output"
    return True, "patch applied with changes"


def _check_execute_code(args: dict, result_text: str) -> tuple[bool, str]:
    """execute_code → no exception/traceback in output."""
    if "Traceback" in result_text or "Error:" in result_text:
        # Only flag as failure if it's not caught/expected
        if "exit_code" in result_text:
            ec = re.search(r'"exit_code"\s*:\s*(\d+)', result_text)
            if ec and int(ec.group(1)) != 0:
                return False, "execute_code produced traceback/error with non-zero exit"
    return True, "executed without fatal error"


EFFECT_CHECKS: dict[str, object] = {
    "write_file":    _check_write_file,
    "terminal":      _check_terminal,
    "web_search":    _check_web_search,
    "search":        _check_web_search,
    "patch":         _check_patch,
    "execute_code":  _check_execute_code,
}


def _extract_tool_calls(session_path: Path) -> list[dict]:
    """Parse JSONL session for tool call records with args and results."""
    calls = []
    lines = session_path.read_text().splitlines()
    for line in lines:
        try:
            ev = json.loads(line)
            content = ev.get("api_content", ev.get("content", ""))
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    calls.append({
                        "tool":   block.get("name", "unknown"),
                        "args":   block.get("input", {}),
                        "result": "",  # will be paired below
                        "call_id": block.get("id", ""),
                    })
                elif block.get("type") == "tool_result":
                    # Pair with last unresolved call
                    call_id = block.get("tool_use_id", "")
                    result_content = block.get("content", "")
                    if isinstance(result_content, list):
                        result_content = " ".join(
                            b.get("text", "") for b in result_content
                            if isinstance(b, dict)
                        )
                    for c in reversed(calls):
                        if c["call_id"] == call_id or not c["result"]:
                            c["result"] = str(result_content)[:500]
                            break
        except Exception:
            pass
    return [c for c in calls if c["tool"] != "unknown"]


def _check_single_file(path: Path) -> dict:
    """Direct check: does a specific file exist and is non-empty?"""
    ok = path.exists() and path.stat().st_size > 0
    return {
        "path": str(path),
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else 0,
        "ok": ok,
    }


def run(session_filter: str | None, check_file: Path | None, dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    alarms: list[str] = []
    results: list[dict] = []

    if check_file:
        r = _check_single_file(check_file)
        print(f"\n[tool-effect] Direct file check: {r}")
        return 0 if r["ok"] else 1

    paths = list(SESSIONS_DIR.glob(f"*{session_filter}*.jsonl")) if session_filter \
            else sorted(SESSIONS_DIR.glob("*.jsonl"))[-10:]

    print(f"[tool-effect-validator] Checking {len(paths)} session(s)")
    total_calls = 0
    total_failures = 0

    for p in paths:
        calls = _extract_tool_calls(p)
        if not calls:
            continue

        session_failures = []
        for call in calls:
            tool = call["tool"]
            check_fn = EFFECT_CHECKS.get(tool)
            if check_fn is None:
                continue  # no predicate for this tool type
            total_calls += 1
            ok, detail = check_fn(call["args"], call["result"])  # type: ignore[call-arg]
            if not ok:
                total_failures += 1
                session_failures.append({
                    "tool": tool,
                    "detail": detail,
                    "args_snippet": str(call["args"])[:80],
                })

        if session_failures:
            alarms.append(
                f"EFFECT_FAILURE: session {p.stem[:16]} — "
                f"{len(session_failures)} tool calls produced no expected effect"
            )
        results.append({
            "session": p.stem,
            "total_calls": len(calls),
            "checkable_calls": total_calls,
            "failures": session_failures,
        })

    print(f"\n=== Tool Effect Validator — {now[:10]} ===")
    print(f"Checkable tool calls: {total_calls}  Failures: {total_failures}")
    for r in results:
        if r["failures"]:
            print(f"  FAIL {r['session'][:20]}: {len(r['failures'])} effect failure(s)")
            for f in r["failures"][:3]:
                print(f"    ! [{f['tool']}] {f['detail']} | args: {f['args_snippet']}")
        elif r["total_calls"] > 0:
            print(f"  OK   {r['session'][:20]}: {r['total_calls']} calls, all effects observed")

    if alarms:
        print(f"\nALARM: yes — {len(alarms)} session(s) with tool effect failures:")
        for a in alarms:
            print(f"  {a}")
        alarm_exit = 1
    else:
        print("\nALARM: no — all checked tool calls produced expected effects")
        alarm_exit = 0

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now, "total_calls": total_calls,
            "total_failures": total_failures,
            "sessions": results, "alarms": alarms,
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nWritten: {OUT_FILE}")

    return alarm_exit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default=None)
    parser.add_argument("--check-file", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(run(session_filter=args.session, check_file=args.check_file, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
