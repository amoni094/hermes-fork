#!/usr/bin/env python3
"""
track-subagent-hud.py — subagent_start hook for real-time HUD tracking
~/.hermes/agent-hooks/track-subagent-hud.py

Fires when a subagent is spawned. Writes an entry to the HUD state file
so hermes-hud can show in-flight delegations.

HUD state: ~/.hermes/state/hud-active-agents.json
  { "agents": [ { "id", "goal", "role", "started_at", "parent_session_id" }, ... ] }
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path("/var/home/rainbow/.hermes/state")
STATE_DIR.mkdir(parents=True, exist_ok=True)
HUD_FILE = STATE_DIR / "hud-active-agents.json"


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
    session_id = payload.get("session_id", "unknown")

    agent_id = extra.get("child_session_id") or extra.get("task_id") or f"agent-{datetime.now(timezone.utc).timestamp():.0f}"
    goal = (extra.get("goal") or extra.get("prompt") or "")[:200]
    role = extra.get("role", "leaf")

    hud = load_hud()
    # Avoid duplicates
    hud["agents"] = [a for a in hud["agents"] if a.get("id") != agent_id]
    hud["agents"].append({
        "id": agent_id,
        "goal": goal,
        "role": role,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "parent_session_id": session_id,
        "status": "running",
    })

    HUD_FILE.write_text(json.dumps(hud, indent=2))
    sys.stdout.write("{}\n")


if __name__ == "__main__":
    main()
