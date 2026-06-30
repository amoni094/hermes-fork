#!/usr/bin/env python3
"""
subagent_stop hook — auto-apply agent findings + ledger logging
~/.hermes/agent-hooks/log-subagent-stop.py

Fires each time a delegated agent completes. Does two things:

1. Ledger: appends a JSONL entry to hermes-task-ledger.jsonl (original behaviour)
2. Auto-apply: scans ~/.hermes/agent-workspace/ for any *.finding.json files
   written since the agent started; runs apply-findings.py on each one
   immediately. This means findings are applied the moment an agent finishes —
   no manual apply step, no --watch polling needed.

The apply result summary is injected into the hook's stdout context so the
parent LLM sees what was applied without having to read prose summaries.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG = Path("/var/home/rainbow/.hermes/logs/hermes-task-ledger.jsonl")
WORKSPACE = Path("/var/home/rainbow/.hermes/agent-workspace")
APPLIER = WORKSPACE / "apply-findings.py"
LOG.parent.mkdir(parents=True, exist_ok=True)

payload = json.load(sys.stdin)
extra = payload.get("extra") or {}

# ── 1. Ledger entry (original behaviour) ─────────────────────────────────────

entry = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "parent_session_id": payload.get("session_id"),
    "child_role": extra.get("child_role"),
    "child_status": extra.get("child_status"),
    "duration_ms": extra.get("duration_ms"),
    "child_summary_excerpt": (extra.get("child_summary") or "")[:1000],
}
with LOG.open("a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# ── 2. Auto-apply any pending findings ───────────────────────────────────────

output_context = {}

if APPLIER.exists() and WORKSPACE.exists():
    pending = list(WORKSPACE.glob("*.finding.json"))
    if pending:
        result = subprocess.run(
            [sys.executable, str(APPLIER)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        summary_lines = [
            l for l in (result.stdout + result.stderr).splitlines()
            if any(kw in l for kw in ("APPLIED", "PATCHED", "APPENDED", "WROTE", "COMMITTED",
                                       "CONFIG-SET", "OBSERVED", "DEFER", "SKIP", "ERROR",
                                       "ALREADY", "Done.", "archived"))
        ]
        summary = "\n".join(summary_lines[-20:])  # last 20 relevant lines
        n_files = len(pending)
        status = "ok" if result.returncode == 0 else f"exit={result.returncode}"
        output_context["context"] = (
            f"[auto-apply {status}] Applied findings from {n_files} agent file(s). "
            f"Summary:\n{summary}"
        )

if output_context:
    json.dump(output_context, sys.stdout)
else:
    sys.stdout.write("{}\n")
