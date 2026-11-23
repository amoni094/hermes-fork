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
    now = _now()
    if rows is None:
        print("No executions.db (or unreadable) — skip running-stuck check")
        rows = []

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
    else:
        _append_alarms(stuck)
        for alarm in stuck:
            print(f"ALARM: {alarm['msg']}")

    # LIVENESS: AF(queued -> eventually running). Max wait bounded.
    live = check_liveness(jobs_by_id, now)
    if live["violations"]:
        _append_alarms(live["violations"])
        for v in live["violations"]:
            print(f"LIVENESS: {v.get('msg')}")
    else:
        print(f"Liveness OK (max_wait_s={live['max_wait_s']}, n_checked={live['n_checked']})")

    # FLP: two triggers within 100ms for same job_id — one must be dropped.
    flp = check_flp_dedup(now)
    if flp["duplicates"]:
        _append_alarms(flp["duplicates"])
        for d in flp["duplicates"]:
            print(f"FLP-DEDUP: {d.get('msg')}")
    else:
        print(f"FLP dedup OK (window_ms={flp['window_ms']})")


MAX_WAIT_SECONDS = 3600
DEDUP_WINDOW_S = 0.100


def check_liveness(jobs_by_id: dict, now: datetime) -> dict:
    """AF(queued -> eventually running): enabled jobs must start within MAX_WAIT_SECONDS.

    Starvation = enabled job whose next_run_at (or last due) is older than max wait
    with no started_at after that due time. Hard core: max wait bounded.
    """
    violations = []
    n_checked = 0
    now_ts = now.timestamp()
    rows_by_job: dict = {}
    if DB_PATH.exists():
        try:
            con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
            try:
                for job_id, started_at, claimed_at, status in con.execute(
                    "SELECT job_id, started_at, claimed_at, status FROM executions"
                ):
                    rows_by_job.setdefault(str(job_id), []).append((started_at, claimed_at, status))
            finally:
                con.close()
        except Exception:
            pass

    for job_id, job in jobs_by_id.items():
        if job.get("enabled") is False:
            continue
        n_checked += 1
        next_run = _parse_started(job.get("next_run_at"))
        last_run = _parse_started(job.get("last_run_at"))
        recently_ran = last_run is not None and (now_ts - last_run.timestamp()) <= MAX_WAIT_SECONDS
        # Never-run / overdue: next_run in the past beyond max wait, or no executions ever.
        overdue = next_run is not None and next_run.timestamp() < now_ts - MAX_WAIT_SECONDS
        never_ran = last_run is None and not rows_by_job.get(str(job_id))
        if (not recently_ran) and (overdue or (never_ran and next_run is not None and next_run.timestamp() < now_ts)):
            recent_start = False
            for started_at, claimed_at, status in rows_by_job.get(str(job_id), []):
                st = _parse_started(started_at) or _parse_started(claimed_at)
                if st is not None and (next_run is None or st.timestamp() >= next_run.timestamp()):
                    recent_start = True
                    break
            if not recent_start:
                wait = now_ts - (next_run.timestamp() if next_run else now_ts)
                violations.append({
                    "ts": now.isoformat(),
                    "job_id": job_id,
                    "kind": "liveness_starvation",
                    "wait_seconds": round(wait, 1),
                    "max_wait_seconds": MAX_WAIT_SECONDS,
                    "msg": (
                        f"STARVE job {job_id}: queued {wait:.0f}s without running "
                        f"(bound {MAX_WAIT_SECONDS}s)"
                    ),
                })
        # claimed -> started delay
        for started_at, claimed_at, status in rows_by_job.get(str(job_id), []):
            c = _parse_started(claimed_at)
            s = _parse_started(started_at)
            if c is None:
                continue
            if s is None:
                wait = now_ts - c.timestamp()
                if wait > MAX_WAIT_SECONDS:
                    violations.append({
                        "ts": now.isoformat(),
                        "job_id": job_id,
                        "kind": "liveness_claimed_unstarted",
                        "wait_seconds": round(wait, 1),
                        "msg": f"STARVE job {job_id}: claimed {wait:.0f}s ago never started",
                    })
            elif (s - c).total_seconds() > MAX_WAIT_SECONDS:
                violations.append({
                    "ts": now.isoformat(),
                    "job_id": job_id,
                    "kind": "liveness_slow_start",
                    "wait_seconds": round((s - c).total_seconds(), 1),
                    "msg": f"STARVE job {job_id}: claimed-to-start > {MAX_WAIT_SECONDS}s",
                })
        _ = last_run  # last_run used as diagnostic only
    return {"violations": violations, "max_wait_s": MAX_WAIT_SECONDS, "n_checked": n_checked}


def check_flp_dedup(now: datetime) -> dict:
    """If two triggers for the same job_id arrive within 100ms, one must be dropped.

    Lynch FLP: no distributed consensus without timeouts; we use a 100ms window.
    """
    duplicates = []
    if not DB_PATH.exists():
        return {"duplicates": duplicates, "window_ms": 100}
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
        try:
            rows = con.execute(
                "SELECT job_id, claimed_at, started_at, status FROM executions "
                "ORDER BY job_id, claimed_at"
            ).fetchall()
        finally:
            con.close()
    except Exception:
        return {"duplicates": duplicates, "window_ms": 100}

    by_job: dict = {}
    for job_id, claimed_at, started_at, status in rows:
        ts = _parse_started(claimed_at) or _parse_started(started_at)
        if job_id is None or ts is None:
            continue
        by_job.setdefault(str(job_id), []).append((ts, status))

    for job_id, events in by_job.items():
        events.sort(key=lambda x: x[0])
        for i in range(1, len(events)):
            dt = (events[i][0] - events[i - 1][0]).total_seconds()
            if 0 <= dt <= DEDUP_WINDOW_S:
                duplicates.append({
                    "ts": now.isoformat(),
                    "job_id": job_id,
                    "kind": "flp_duplicate_trigger",
                    "delta_ms": round(dt * 1000.0, 3),
                    "msg": (
                        f"FLP job {job_id}: two triggers {dt*1000:.1f}ms apart "
                        f"(window 100ms) — one must be dropped"
                    ),
                })
    return {"duplicates": duplicates, "window_ms": 100}


FLP_CLAIM_PATH = _HERMES_ROOT / "cache" / "cron-flp-claim.json"


def flp_should_drop(job_id: str, ts: float | None = None) -> bool:
    """Return True if this trigger must be dropped (duplicate within 100ms).

    Hard core: at most one accepted fire per job_id per 100ms window.
    """
    if ts is None:
        ts = datetime.now(timezone.utc).timestamp()
    job_id = str(job_id)
    claims: dict = {}
    if FLP_CLAIM_PATH.exists():
        try:
            raw = json.loads(FLP_CLAIM_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                claims = raw
        except Exception:
            claims = {}
    last = claims.get(job_id)
    drop = False
    if isinstance(last, (int, float)) and abs(ts - float(last)) <= DEDUP_WINDOW_S:
        drop = True
    else:
        claims[job_id] = ts
        try:
            FLP_CLAIM_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = FLP_CLAIM_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(claims))
            tmp.rename(FLP_CLAIM_PATH)
        except Exception:
            pass
    return drop


def main() -> int:
    try:
        run()
    except Exception as exc:
        print(f"stuck-job-detector error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
