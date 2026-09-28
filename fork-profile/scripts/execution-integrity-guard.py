#!/usr/bin/env python3
"""
execution-integrity-guard.py — APEXA execution integrity post-tool-call hook
arXiv:2609.24165 — Execution-Integrity Enforcement for Multi-Agent LLM Automation

Called as a post_tool_call hook. Reads stdin as JSON:
  {tool_name, call_id, result_summary}
Blocks fabricated or untracked results by flagging them.

Hook protocol:
  stdout {"block_next": true, "reason": "..."} -> next tool use is blocked
  stdout {} -> proceed silently

Log: ~/.hermes/profiles/fork/logs/exec-integrity.jsonl
"""
import sys
import json
import os
import datetime
import hashlib
from pathlib import Path

_HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
LOG_PATH = _HERMES_HOME / "profiles/fork/logs/exec-integrity.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

FABRICATION_SIGNALS = [
    "fabricated",
    "simulated result",
    "hypothetical output",
    "as if executed",
    "pretend",
    "imagine the result",
]


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _log(record: dict) -> None:
    try:
        with LOG_PATH.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def main() -> None:
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            print("{}")
            return
        payload = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        print("{}")
        return

    tool_name = payload.get("tool_name", "unknown")
    call_id = payload.get("call_id", "")
    result_summary = payload.get("result_summary", "")

    ts = _now_iso()
    issues = []

    # Check 1: call_id must be present and non-empty
    if not call_id:
        issues.append("missing call_id — result not traceable to a dispatched call")

    # Check 2: result_summary must not contain fabrication signals
    lower_summary = result_summary.lower()
    for signal in FABRICATION_SIGNALS:
        if signal in lower_summary:
            issues.append(f"fabrication signal detected: '{signal}'")
            break

    # Compute content hash for audit trail
    content_hash = hashlib.sha256(result_summary.encode()).hexdigest()[:12]

    record = {
        "ts": ts,
        "tool_name": tool_name,
        "call_id": call_id or None,
        "content_hash": content_hash,
        "issues": issues,
        "verdict": "BLOCK" if issues else "OK",
    }
    _log(record)

    if issues:
        response = {
            "block_next": True,
            "reason": "APEXA integrity violation: " + "; ".join(issues),
        }
    else:
        response = {}

    print(json.dumps(response))
    # Exit non-zero when issues found so cron/caller can detect violations
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
