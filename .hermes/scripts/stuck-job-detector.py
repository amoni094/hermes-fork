#!/usr/bin/env python3
"""Detect cron jobs stuck in running state for >2x expected duration.

Clarke et al. CTL/LTL safety property: AG(running -> EF(complete|failed)).
Exit 0 always — this detector must never crash the cron scheduler.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERMES_BASE = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
_HERMES_PROFILE = os.environ.get("HERMES_PROFILE", "")
_HERMES_ROOT = (
    (_HERMES_BASE / "profiles" / _HERMES_PROFILE)
    if _HERMES_PROFILE and "profiles" not in str(_HERMES_BASE)
    else _HERMES_BASE
)
JOBS_PATH = _HERMES_ROOT / "cron" / "jobs.json"
DB_PATH = _HERMES_ROOT / "cron" / "executions.db"
ALARM_PATH = _HERMES_ROOT / "cron" / "stuck-job-alarms.jsonl"


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



def _empirical_timeout(job_id: str, db_path: Path, fallback_seconds: int = 1800) -> int:
    """Estimate job timeout from historical completion times.

    Theory: Harchol-Balter "Performance Modeling and Design of Computer Systems"
    Ch.10 (M/G/1 queue, service time estimation). Expected completion time grounded
    in empirical distribution of past completions, not a fixed constant.

    Uses: mean + 2*std of historical durations (captures ~97.5% of completions
    under Gaussian approximation; conservative for heavy-tailed distributions).
    Falls back to fallback_seconds if fewer than 3 historical runs.

    Args:
        job_id: cron job identifier
        db_path: path to executions.db
        fallback_seconds: default timeout if insufficient history
    Returns:
        Estimated timeout in seconds.
    """
    if not db_path.exists():
        return fallback_seconds
    try:
        import sqlite3, math, statistics
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        try:
            rows = con.execute(
                "SELECT started_at, completed_at FROM executions "
                "WHERE job_id=? AND status IN ('completed','success') "
                "ORDER BY rowid DESC LIMIT 20",
                (job_id,)
            ).fetchall()
        finally:
            con.close()

        durations = []
        for started_at, completed_at in rows:
            try:
                # Handle both epoch float and ISO string
                def _to_epoch(v):
                    if v is None:
                        return None
                    if isinstance(v, (int, float)):
                        return float(v)
                    s = str(v).strip().replace("Z", "+00:00")
                    from datetime import datetime, timezone
                    dt = datetime.fromisoformat(s)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.timestamp()
                t_start = _to_epoch(started_at)
                t_end = _to_epoch(completed_at)
                if t_start and t_end and t_end > t_start:
                    durations.append(t_end - t_start)
            except Exception:
                continue

        if len(durations) < 3:
            return fallback_seconds

        mean_d = statistics.mean(durations)
        std_d = statistics.stdev(durations) if len(durations) > 1 else mean_d * 0.5
        # Mean + 2*std captures 97.5% of Gaussian; floor at 60s
        estimated = int(math.ceil(mean_d + 2 * std_d))
        return max(60, estimated)
    except Exception:
        return fallback_seconds


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
        static_timeout = _timeout_for(job)
        # Empirical timeout from historical runs (Harchol-Balter Ch.10)
        # Use max(static, empirical) so detector is never stricter than declared
        empirical = _empirical_timeout(str(job_id), DB_PATH, static_timeout)
        timeout = max(static_timeout, empirical)
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
