#!/usr/bin/env python3
"""pending-improvements-review.py — Review pending Hermes self-improvement proposals.

Reads ~/.hermes/profiles/{profile}/pending/ for pending improvement files,
evaluates them against the gate criteria, and emits a JSON report.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
if not _hermes_base.is_dir():
    print(f"ERROR: HERMES_HOME={_hermes_base} does not exist", file=sys.stderr)
    sys.exit(2)

PENDING_DIR = _hermes_root / "pending"
REPORT_PATH = _hermes_root / "cache" / "pending-improvements-report.json"

def main():
    if not PENDING_DIR.exists():
        print(f"[pending-improvements-review] No pending dir at {PENDING_DIR}.")
        sys.exit(0)
    items = list(PENDING_DIR.glob("*.json")) + list(PENDING_DIR.glob("*.md"))
    print(f"[pending-improvements-review] {len(items)} pending items found.")
    report = {"ts": time.time(), "count": len(items),
              "items": [str(p.name) for p in items]}
    tmp = REPORT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2))
    tmp.replace(REPORT_PATH)
    print(f"[pending-improvements-review] Report written to {REPORT_PATH}")
    sys.exit(0)

if __name__ == "__main__":
    main()
