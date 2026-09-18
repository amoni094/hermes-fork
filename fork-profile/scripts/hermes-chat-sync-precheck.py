#!/usr/bin/env python3
"""
hermes-chat-sync-precheck.py
Fast no-LLM pre-check for hermes-chat-sync-4h.
Exits 0 (run sync) or exits with SKIP sentinel if no new sessions.
"""
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

LIVE_SYNC_NOTE = Path("/var/home/rainbow/Documents/SecondBrain/04 Resources/Hermes Chat Live Sync.md")
SESSIONS_DB = Path("/var/home/rainbow/.hermes/state.db")

def get_last_sync_time():
    """Extract last synced timestamp from the live-sync note frontmatter."""
    if not LIVE_SYNC_NOTE.exists():
        return None
    for line in LIVE_SYNC_NOTE.read_text().splitlines():
        if line.startswith("last_synced:"):
            ts = line.split(":", 1)[1].strip().strip('"\'\' ')
            try:
                return datetime.fromisoformat(ts)
            except ValueError:
                pass
    return None

def count_new_sessions(since: datetime) -> int:
    """Count sessions created after 'since' timestamp via hermes CLI."""
    result = subprocess.run(
        ["hermes", "sessions", "list", "--format", "json"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return 1  # Fail safe: run the sync
    try:
        sessions = json.loads(result.stdout)
        since_utc = since.astimezone(timezone.utc)
        new = [s for s in sessions
               if datetime.fromisoformat(s.get("updated_at","1970-01-01")).astimezone(timezone.utc) > since_utc
               and s.get("source","") not in ("cron","subagent")]
        return len(new)
    except Exception:
        return 1  # Fail safe

def main():
    last_sync = get_last_sync_time()
    if last_sync is None:
        print("No prior sync found — running sync")
        sys.exit(0)

    age_hours = (datetime.now(timezone.utc) - last_sync.astimezone(timezone.utc)).total_seconds() / 3600
    new_count = count_new_sessions(last_sync)

    print(f"Last sync: {last_sync} ({age_hours:.1f}h ago) | New sessions: {new_count}")

    if new_count == 0 and age_hours < 6:
        print("SKIP: no new sessions since last sync")
        # Write a skip sentinel that the cron runner can detect
        sys.exit(42)  # Non-zero non-error exit: job runner treats as skip
    else:
        print(f"RUN: {new_count} new sessions, proceeding with sync")
        sys.exit(0)

if __name__ == "__main__":
    main()
