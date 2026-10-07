#!/usr/bin/env python3
"""real-options-fanout-gate.py — Cron wrapper for real-options-deployment-gate.

Reads pending subagent task descriptions from the advisory queue
(~/.hermes/cache/pending-fanout-queue.json), applies real-options gate,
and writes gated vs deferred decisions to the monitor output.

Wires GAP-4: real-options-deployment-gate.py now has a cron caller.
"""
from __future__ import annotations
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
GATE_SCRIPT = HOME / "scripts/real-options-deployment-gate.py"
QUEUE_FILE  = HOME / "cache/pending-fanout-queue.json"
OUT_FILE    = HOME / "cache/monitors/real-options-gate-decisions.json"
PYTHON      = sys.executable

def _load_queue() -> list:
    """Load pending tasks. Returns empty list if none queued."""
    if not QUEUE_FILE.exists():
        return []
    try:
        raw = json.loads(QUEUE_FILE.read_text())
        return raw if isinstance(raw, list) else raw.get("tasks", [])
    except Exception:
        return []

def _gate(task: str) -> dict:
    """Run real-options-deployment-gate for one task. Returns parsed result.
    Fail-closed: parse error or nonzero rc → DEFER (not COMMIT).
    """
    r = subprocess.run(
        [PYTHON, str(GATE_SCRIPT), task, "--json-output"],  # positional task, then flag
        capture_output=True, text=True, timeout=15
    )
    if r.returncode not in (0, 1):  # 0=COMMIT, 1=DEFER; anything else is a crash
        return {"decision": "DEFER", "task": task,
                "error": f"gate rc={r.returncode}: {r.stderr.strip()[:120]}"}
    lines = [l for l in r.stdout.splitlines() if l.strip().startswith("{")]
    if not lines:
        return {"decision": "DEFER", "task": task,
                "error": f"no JSON from gate (stdout={r.stdout.strip()[:80]!r})"}
    try:
        return json.loads(lines[-1])
    except Exception as exc:
        return {"decision": "DEFER", "task": task, "error": str(exc)}

def main() -> int:
    if not GATE_SCRIPT.exists():
        print(f"SKIP: gate script not found at {GATE_SCRIPT}", file=sys.stderr)
        return 1

    tasks = _load_queue()
    if not tasks:
        # No queued tasks — emit a health-check run record
        results = [{"decision": "NOOP", "task": "__heartbeat__",
                    "ts": datetime.now(tz=timezone.utc).isoformat()}]
    else:
        results = []
        for t in tasks:
            task_str = t if isinstance(t, str) else t.get("task") or t.get("description") or str(t)
            result = _gate(task_str)
            result["ts"] = datetime.now(tz=timezone.utc).isoformat()
            results.append(result)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing: list = []
    if OUT_FILE.exists():
        try:
            existing = json.loads(OUT_FILE.read_text())
        except Exception:
            existing = []
    existing.extend(results)
    # Keep last 200 decisions
    existing = existing[-200:]
    tmp = Path(str(OUT_FILE) + ".tmp")
    tmp.write_text(json.dumps(existing, indent=2))
    tmp.replace(OUT_FILE)

    gated  = sum(1 for r in results if r.get("decision") == "COMMIT")
    defer  = sum(1 for r in results if r.get("decision") == "DEFER")
    print(f"real-options-fanout-gate: {len(results)} tasks — {gated} COMMIT, {defer} DEFER")
    return 0

if __name__ == "__main__":
    sys.exit(main())
