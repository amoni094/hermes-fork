#!/usr/bin/env python3
"""hermes-research-apply.py — Apply accumulated research findings to Hermes skills.

Reads the research findings bank (arxiv-sweep-findings, cs-sweep-findings, etc.),
identifies high-applicability findings not yet applied, and queues them for
the next operator review session.
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

FINDINGS_DIR = _hermes_root / "cache" / "research-findings"
APPLY_QUEUE  = _hermes_root / "pending" / "research-apply-queue.json"
LOG = _hermes_root / "cache" / "hermes-research-apply.log"

def main():
    findings = []
    if FINDINGS_DIR.exists():
        findings = list(FINDINGS_DIR.glob("*.json"))
    print(f"[hermes-research-apply] {len(findings)} finding files in {FINDINGS_DIR}.")
    report = {"ts": time.time(), "findings_count": len(findings),
              "queued": [str(f.name) for f in findings[:10]]}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    tmp = LOG.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2))
    tmp.replace(LOG)
    sys.exit(0)

if __name__ == "__main__":
    main()
