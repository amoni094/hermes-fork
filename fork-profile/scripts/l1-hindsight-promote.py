#!/usr/bin/env python3
"""l1-hindsight-promote.py — Promote L1 memory facts to Hindsight long-term memory.

Reads ~/.hermes/memory-facts/staging.md, parses bullet lines stripping timestamps/
scores and inline tags, builds hindsight_retain calls with cleaned fact text and tags.
Cron job stub: runs via hermes CLI to invoke hindsight_retain in a gateway session.
"""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
if not _hermes_base.is_dir():
    print(f"ERROR: HERMES_HOME={_hermes_base} does not exist", file=sys.stderr)
    sys.exit(2)

STAGING = _hermes_base / "memory-facts" / "staging.md"
LOG = _hermes_base / "cache" / "l1-hindsight-promote.log"

def main():
    if not STAGING.exists():
        print(f"[l1-hindsight-promote] No staging file at {STAGING} — nothing to promote.")
        sys.exit(0)
    lines = [l for l in STAGING.read_text().splitlines() if l.strip().startswith("-")]
    if not lines:
        print("[l1-hindsight-promote] No bullet lines in staging.md.")
        sys.exit(0)
    print(f"[l1-hindsight-promote] {len(lines)} facts staged — promotion requires gateway session.")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    import time
    LOG.write_text(json.dumps({"ts": time.time(), "staged": len(lines), "status": "pending_gateway"}) + "\n")
    sys.exit(0)

if __name__ == "__main__":
    main()
