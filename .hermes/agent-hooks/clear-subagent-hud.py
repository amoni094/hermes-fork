#!/usr/bin/env python3
"""
clear-subagent-hud.py — subagent_stop hook complement for HUD
~/.hermes/agent-hooks/clear-subagent-hud.py

Marks a completed agent as done in the HUD state file.
Prunes entries older than 2 hours to prevent stale buildup.
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

STATE_DIR = Path("/var/home/rainbow/.hermes/state")
HUD_FILE = STATE_DIR / "hud-active-agents.json"
PRUNE_AFTER = timedelta(hours=2)


def load_hud():
    if HUD_FILE.exists():
        try:
            return json.loads(HUD_FILE.read_text())
        except Exception:
            pass
    return {"agents": []}


def main():
    payload = json.load(sys.stdin)
    extra = payload.get("extra") or {}

    agent_id = extra.get("child_session_id") or extra.get("task_id")
    child_status = extra.get("child_status", "done")
    now = datetime.now(timezone.utc)

    hud = load_hud()
    updated = []
    for a in hud["agents"]:
        if a.get("id") == agent_id:
            a["status"] = child_status
            a["finished_at"] = now.isoformat()
        # Prune old completed entries
        finished = a.get("finished_at")
        if finished:
            try:
                age = now - datetime.fromisoformat(finished)
                if age > PRUNE_AFTER:
                    continue
            except Exception:
                pass
        updated.append(a)
    hud["agents"] = updated
    HUD_FILE.write_text(json.dumps(hud, indent=2))
    sys.stdout.write("{}\n")


if __name__ == "__main__":
    main()
