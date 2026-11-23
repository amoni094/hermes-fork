#!/usr/bin/env python3
"""
se-gos-graphiti-bridge.py — SE-GoS Graphiti skill-graph evolution bridge.

Reads skill_yield_metrics from state.db and writes reinforce/decay episodes
to Graphiti. Empty yield table is a successful no-op (exit 0).
"""
import argparse
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_PROFILE = os.environ.get("HERMES_PROFILE", "")
if _PROFILE and "profiles" not in str(_HERMES_HOME):
    _PROFILE_ROOT = _HERMES_HOME / "profiles" / _PROFILE
else:
    _PROFILE_ROOT = _HERMES_HOME

STATE_DB = _PROFILE_ROOT / "state.db"
GRAPHITI_BASE = "http://127.0.0.1:8765/mcp"
GROUP_ID = "hermes-skills"
TIMEOUT = 30
REINFORCE_THRESHOLD = 0.5
DECAY_THRESHOLD = 0.1
MIN_INVOCATIONS = 5


def _graphiti_post(endpoint: str, payload: dict):
    url = f"{GRAPHITI_BASE}{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError:
        return None


def _graphiti_alive() -> bool:
    try:
        with urllib.request.urlopen(GRAPHITI_BASE, timeout=5):
            pass
        return True
    except Exception:
        return False


def _write_episode(name: str, body: str) -> bool:
    payload = {
        "name": name,
        "episode_body": body,
        "source_type": "cron",
        "group_id": GROUP_ID,
        "reference_time": datetime.now(timezone.utc).isoformat(),
    }
    return _graphiti_post("/add_episode", payload) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description="SE-GoS Graphiti bridge")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--min-invocations", type=int, default=MIN_INVOCATIONS)
    args = parser.parse_args()

    if not STATE_DB.exists():
        print(f"[se-gos] state.db not found at {STATE_DB} -- no-op")
        return 0

    try:
        conn = sqlite3.connect(str(STATE_DB), timeout=10)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='skill_yield_metrics'"
        )
        if not cur.fetchone():
            print("[se-gos] skill_yield_metrics table absent -- no-op")
            conn.close()
            return 0
        cur.execute(
            "SELECT skill_name, invocation_count, normalized_yield, "
            "success_count, failure_count, deprecated "
            "FROM skill_yield_metrics WHERE invocation_count >= ?",
            (args.min_invocations,)
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except sqlite3.Error as e:
        print(f"[se-gos] DB error: {e}", file=sys.stderr)
        return 0

    if not rows:
        print("[se-gos] No skills meet min_invocations threshold -- no-op")
        return 0

    reinforce = [r for r in rows if r["normalized_yield"] >= REINFORCE_THRESHOLD]
    decay = [r for r in rows if r["normalized_yield"] < DECAY_THRESHOLD
             and not r.get("deprecated")]

    print(f"[se-gos] {len(rows)} skills: {len(reinforce)} reinforce, {len(decay)} decay")

    if not reinforce and not decay:
        print("[se-gos] Nothing to write -- no-op")
        return 0

    if args.dry_run:
        for r in reinforce:
            print(f"  [DRY REINFORCE] {r['skill_name']} yield={r['normalized_yield']:.3f}")
        for r in decay:
            print(f"  [DRY DECAY]     {r['skill_name']} yield={r['normalized_yield']:.3f}")
        return 0

    if not _graphiti_alive():
        print("[se-gos] Graphiti not reachable -- no-op")
        return 0

    written = 0
    for row in reinforce:
        body = (
            f"Skill '{row['skill_name']}' strong performance: "
            f"normalized_yield={row['normalized_yield']:.3f}, "
            f"invocations={row['invocation_count']}. Reinforce routing weight."
        )
        if _write_episode(f"se-gos:reinforce:{row['skill_name']}", body):
            written += 1
            print(f"  [REINFORCE] {row['skill_name']}")
    for row in decay:
        body = (
            f"Skill '{row['skill_name']}' weak performance: "
            f"normalized_yield={row['normalized_yield']:.3f}, "
            f"invocations={row['invocation_count']}. Decay routing weight."
        )
        if _write_episode(f"se-gos:decay:{row['skill_name']}", body):
            written += 1
            print(f"  [DECAY]     {row['skill_name']}")

    print(f"[se-gos] Wrote {written} episodes to Graphiti")
    return 0


if __name__ == "__main__":
    sys.exit(main())
