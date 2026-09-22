#!/usr/bin/env python3
"""Detect cron jobs stuck in running state for >2x expected duration.

Clarke et al. CTL/LTL safety property: AG(running -> EF(complete|failed)).
Exit 0 always — this detector must never crash the cron scheduler.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

JOBS_PATH = Path("/var/home/rainbow/.hermes/profiles/fork/cron/jobs.json")
DB_PATH = Path("/var/home/rainbow/.hermes/profiles/fork/cron/executions.db")
ALARM_PATH = Path("/var/home/rainbow/.hermes/profiles/fork/cron/stuck-job-alarms.jsonl")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_started(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        try:
            return datetime.fromtimestamp(float(s), tz=timezone.utc)
        except (OSError, OverflowError, TypeError, ValueError):
            return None


def _timeout_for(job: dict) -> int:
    raw = job.get("timeout_seconds")
    if raw is None:
        return 1800
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 1800


def _load_jobs() -> dict:
    jobs_by_id: dict = {}
    try:
        data = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
        jobs = data.get("jobs", data) if isinstance(data, dict) else data
        for job in jobs or []:
            if isinstance(job, dict) and job.get("id"):
                jobs_by_id[str(job["id"])] = job
    except Exception:
        pass
    return jobs_by_id


def _running_rows():
    if not DB_PATH.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
        try:
            return con.execute(
                "SELECT job_id, started_at FROM executions WHERE status='running'"
            ).fetchall()
        finally:
            con.close()
    except Exception:
        return None


def _append_alarms(alarms: list[dict]) -> None:
    ALARM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ALARM_PATH.open("a", encoding="utf-8") as fh:
        for alarm in alarms:
            fh.write(json.dumps(alarm, default=str) + "\n")


def run() -> None:
    jobs_by_id = _load_jobs()
    rows = _running_rows()
    if rows is None:
        print("No executions.db (or unreadable) — skip")
        return
    if not rows:
        print("No stuck jobs")
        return

    now = _now()
    stuck: list[dict] = []
    for job_id, started_at in rows:
        job = jobs_by_id.get(str(job_id) if job_id is not None else "") or {}
        timeout = _timeout_for(job)
        threshold = 2 * timeout
        started = _parse_started(started_at)
        if started is None:
            continue
        elapsed = (now - started).total_seconds()
        if elapsed <= threshold:
            continue
        msg = (
            f"STUCK job {job_id}: running {elapsed:.0f}s > 2x timeout "
            f"({threshold}s)"
        )
        stuck.append(
            {
                "ts": now.isoformat(),
                "job_id": job_id,
                "started_at": started_at,
                "elapsed_seconds": round(elapsed, 1),
                "timeout_seconds": timeout,
                "threshold_seconds": threshold,
                "msg": msg,
            }
        )

    if not stuck:
        print("No stuck jobs")
        return

    _append_alarms(stuck)
    for alarm in stuck:
        print(f"ALARM: {alarm['msg']}")


def main() -> int:
    try:
        run()
    except Exception as exc:
        print(f"stuck-job-detector error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
