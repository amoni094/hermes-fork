"""ZooKeeper-inspired watch-style config change detector for cron jobs.json.

Theory: ZooKeeper (Hunt et al. 2010) implements watches — one-shot change
notifications that fire when a znode changes. Unlike polling, watches avoid
unnecessary work when config is stable and provide near-zero latency detection
when it changes.

Applied here: watch jobs.json for changes by comparing inode+mtime+size (the
"version" in ZooKeeper terms). When a change is detected, write a reload-needed
sentinel file that the cron scheduler can check on its next tick, without
requiring a full restart. Also compute a content-hash diff to identify WHICH
jobs changed (added/removed/modified) — analogous to ZooKeeper's getData()
response after a watch fires.

Also inspired by Chubby (Burrows 2006) §2.7 caching: the watcher maintains
a local cache of job state and emits precise invalidations rather than
broadcasting the whole config. A job's "version" is its content hash — only
jobs whose hash changed are flagged for reload.

Usage:
  python3 jobs-config-watcher.py [--daemon] [--interval 5]

  --daemon: run continuously, checking every --interval seconds
  Default: run once and exit with rc=0 (no change) or rc=1 (changed)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("jobs-config-watcher")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes" / "profiles" / "fork"))
JOBS_FILE = HERMES_HOME / "cron" / "jobs.json"
# Sentinel: presence triggers reload on next scheduler tick
RELOAD_SENTINEL = HERMES_HOME / "cron" / ".jobs-reload-needed"
# Watcher state: persisted across runs so single-shot calls are cheap
WATCHER_STATE = HERMES_HOME / "omni" / "jobs-watcher-state.json"


# ---------------------------------------------------------------------------
# "Version" computation (ZooKeeper-style: stat + content hash)
# ---------------------------------------------------------------------------

def _file_stat(path: Path) -> Optional[dict]:
    """Return a ZooKeeper-style stat for the file, or None if missing."""
    try:
        st = path.stat()
        return {
            "inode": st.st_ino,
            "mtime": st.st_mtime,
            "size": st.st_size,
        }
    except FileNotFoundError:
        return None


def _job_content_hash(job: dict) -> str:
    """Stable hash of job dict (sorted keys, excludes runtime-only fields)."""
    # Exclude fields that change every run but don't represent config changes
    runtime_fields = {"last_run", "next_run_at", "last_dispatch", "last_result"}
    stable = {k: v for k, v in job.items() if k not in runtime_fields}
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def _load_jobs(path: Path) -> Optional[dict[str, str]]:
    """Return {job_id: content_hash} or None if file unreadable."""
    try:
        data = json.loads(path.read_text())
        jobs = data if isinstance(data, list) else data.get("jobs", [])
        return {
            j.get("id", f"__anon_{i}"): _job_content_hash(j)
            for i, j in enumerate(jobs)
            if isinstance(j, dict)
        }
    except Exception as exc:
        logger.warning("Failed to parse %s: %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# State persistence (Chubby-style cache with invalidation)
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    try:
        return json.loads(WATCHER_STATE.read_text())
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    WATCHER_STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = WATCHER_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(WATCHER_STATE)


# ---------------------------------------------------------------------------
# Change detection (ZooKeeper watch semantics)
# ---------------------------------------------------------------------------

def check_for_changes(*, write_sentinel: bool = True) -> dict:
    """Check jobs.json for changes. Returns a change report dict.

    Change report keys:
      changed (bool): True if any change detected
      added (list[str]): job IDs added since last check
      removed (list[str]): job IDs removed since last check
      modified (list[str]): job IDs whose content changed
      stat_changed (bool): file inode/mtime/size changed
      sentinel_written (bool): reload sentinel was written
    """
    state = _load_state()
    current_stat = _file_stat(JOBS_FILE)
    prev_stat = state.get("stat")

    # Fast path: stat unchanged → content unchanged (ZooKeeper: cversion unchanged)
    stat_changed = current_stat != prev_stat
    if not stat_changed and state.get("job_hashes") is not None:
        return {
            "changed": False,
            "added": [],
            "removed": [],
            "modified": [],
            "stat_changed": False,
            "sentinel_written": False,
        }

    # Stat changed (or no prior state): compute full content diff
    current_hashes_or_none = _load_jobs(JOBS_FILE)
    # ADV-017 fix: if jobs.json is missing/invalid, do NOT emit mass-removal sentinel.
    # The file may be temporarily unavailable (write-in-progress, deployment, etc.).
    # Only emit changes when we successfully parsed the file.
    if current_hashes_or_none is None:
        logger.warning("jobs.json unavailable or invalid — skipping change detection to avoid false mass-removal")
        return {
            "changed": False, "added": [], "removed": [], "modified": [],
            "stat_changed": stat_changed, "sentinel_written": False,
            "parse_error": True,
        }
    current_hashes = current_hashes_or_none
    prev_hashes: dict = state.get("job_hashes") or {}

    added = [jid for jid in current_hashes if jid not in prev_hashes]
    removed = [jid for jid in prev_hashes if jid not in current_hashes]
    modified = [
        jid for jid in current_hashes
        if jid in prev_hashes and current_hashes[jid] != prev_hashes[jid]
    ]

    changed = bool(added or removed or modified or stat_changed)

    if changed:
        logger.info(
            "jobs.json changed: +%d -%d ~%d jobs (stat_changed=%s)",
            len(added), len(removed), len(modified), stat_changed,
        )
        if write_sentinel:
            RELOAD_SENTINEL.parent.mkdir(parents=True, exist_ok=True)
            RELOAD_SENTINEL.write_text(json.dumps({
                "detected_at": time.time(),
                "added": added,
                "removed": removed,
                "modified": modified,
            }, indent=2))
            logger.info("Wrote reload sentinel: %s", RELOAD_SENTINEL)

    # Always update state after a stat change (even if no job-level diff)
    if stat_changed or changed:
        _save_state({
            "stat": current_stat,
            "job_hashes": current_hashes,
            "last_checked": time.time(),
        })

    return {
        "changed": changed,
        "added": added,
        "removed": removed,
        "modified": modified,
        "stat_changed": stat_changed,
        "sentinel_written": changed and write_sentinel,
    }


# ---------------------------------------------------------------------------
# Daemon mode
# ---------------------------------------------------------------------------

def run_daemon(interval: float) -> None:
    logger.info("Watching %s every %.1fs", JOBS_FILE, interval)
    while True:
        try:
            report = check_for_changes()
            if report["changed"]:
                logger.info("Change report: %s", report)
        except Exception as exc:
            logger.error("Watcher error: %s", exc, exc_info=True)
        time.sleep(interval)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Watch jobs.json for changes")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=float, default=5.0, help="Check interval in daemon mode")
    parser.add_argument("--no-sentinel", action="store_true", help="Don't write reload sentinel")
    parser.add_argument("--self-test", action="store_true", help="Verify module imports and exit")
    args = parser.parse_args()

    if args.self_test:
        report = check_for_changes(write_sentinel=False)
        print(f"self-test OK: changed={report['changed']}, jobs_file_exists={JOBS_FILE.exists()}")
        return 0

    if args.daemon:
        run_daemon(args.interval)
        return 0

    report = check_for_changes(write_sentinel=not args.no_sentinel)
    print(json.dumps(report, indent=2))
    return 1 if report["changed"] else 0


if __name__ == "__main__":
    sys.exit(main())
