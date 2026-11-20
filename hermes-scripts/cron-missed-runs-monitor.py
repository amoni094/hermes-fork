#!/usr/bin/env python3
"""Cron missed-run / timeout-cascade monitor (single-user reliability).

Reads profile cron/executions.db (last 1000 rows) plus jobs.json failure_streak.
Writes cache/cron-missed-runs.json and optional *-alarm.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime, timezone, UTC
from pathlib import Path

WINDOW_S = 24 * 3600
MISSED_WARN = 10
MISSED_HIGH = 30
STREAK_WARN = 3


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    path = Path(env).expanduser().resolve() if env else (Path.home() / ".hermes")
    if path.name == ".hermes":
        return path
    if path.parent.name == "profiles":
        return path.parent.parent
    return path


def _profile_name() -> str:
    return os.environ.get("HERMES_PROFILE") or "fork"


def _hermes_root() -> Path:
    home = _hermes_home()
    env = os.environ.get("HERMES_HOME", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if p.parent.name == "profiles":
            return p
    cand = home / "profiles" / _profile_name()
    return cand if cand.is_dir() else home


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    data = json.dumps(payload, indent=2, default=str) + "\n"
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, data.encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_iso(val: object) -> float | None:
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def scan_executions(db: Path, cutoff: float) -> dict:
    empty = {
        "n_rows": 0,
        "in_window": 0,
        "status": {},
        "timeout_124": 0,
        "top_missed_jobs": [],
        "top_failed_jobs": [],
        "db": str(db) if db.is_file() else None,
    }
    if not db.is_file():
        return empty
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA busy_timeout=5000")
            con.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            pass
    except sqlite3.Error:
        return empty
    try:
        n_rows = con.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
        status_all = Counter()
        missed_jobs: Counter[str] = Counter()
        failed_jobs: Counter[str] = Counter()
        timeout_124 = 0
        in_window = 0
        for row in con.execute(
            "SELECT job_id, status, claimed_at, scheduled_instant, finished_at, error, duration_s "
            "FROM executions"
        ):
            status = str(row["status"] or "unknown")
            ts = (
                _parse_iso(row["finished_at"])
                or _parse_iso(row["claimed_at"])
                or _parse_iso(row["scheduled_instant"])
            )
            if ts is not None and ts < cutoff:
                continue
            in_window += 1
            status_all[status] += 1
            jid = str(row["job_id"] or "?")
            if status == "missed":
                missed_jobs[jid] += 1
            if status == "failed":
                failed_jobs[jid] += 1
            try:
                dur = row["duration_s"]
                if dur is not None and float(dur) >= 120:
                    timeout_124 += 1
            except (TypeError, ValueError):
                pass
        return {
            "n_rows": int(n_rows),
            "in_window": in_window,
            "status": dict(status_all),
            "status_all_time": dict(
                con.execute("SELECT status, COUNT(*) FROM executions GROUP BY status")
            ),
            "timeout_124": timeout_124,
            "top_missed_jobs": missed_jobs.most_common(8),
            "top_failed_jobs": failed_jobs.most_common(8),
            "db": str(db),
        }
    except sqlite3.Error as exc:
        empty["error"] = str(exc)
        return empty
    finally:
        try:
            con.close()
        except sqlite3.Error:
            pass


def scan_jobs(jobs_path: Path) -> dict:
    out = {"n_jobs": 0, "enabled": 0, "failure_streaks": [], "last_status": {}}
    if not jobs_path.is_file():
        return out
    try:
        data = json.loads(jobs_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        return out
    streaks = []
    last_status: Counter[str] = Counter()
    enabled = 0
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("enabled"):
            enabled += 1
        last_status[str(job.get("last_status") or "unknown")] += 1
        streak = job.get("failure_streak")
        try:
            streak_i = int(streak or 0)
        except (TypeError, ValueError):
            streak_i = 0
        if streak_i >= STREAK_WARN:
            streaks.append(
                {
                    "id": job.get("id"),
                    "name": job.get("name"),
                    "failure_streak": streak_i,
                    "last_error": (str(job.get("last_error") or "")[:200] or None),
                }
            )
    streaks.sort(key=lambda x: int(x.get("failure_streak") or 0), reverse=True)
    out["n_jobs"] = len(jobs)
    out["enabled"] = enabled
    out["failure_streaks"] = streaks[:12]
    out["last_status"] = dict(last_status)
    return out


def build_report(ex: dict, jobs: dict) -> dict:
    missed = int((ex.get("status") or {}).get("missed") or 0)
    failed = int((ex.get("status") or {}).get("failed") or 0)
    alarms: list[dict] = []
    if missed >= MISSED_HIGH:
        alarms.append({"severity": "HIGH", "why": "missed runs in 24h", "missed": missed})
    elif missed >= MISSED_WARN:
        alarms.append({"severity": "MEDIUM", "why": "missed runs in 24h", "missed": missed})
    if ex.get("timeout_124", 0) >= 8:
        alarms.append(
            {
                "severity": "MEDIUM",
                "why": "timeout cascade (exit 124)",
                "timeout_124": ex["timeout_124"],
            }
        )
    if jobs.get("failure_streaks"):
        alarms.append(
            {
                "severity": "MEDIUM",
                "why": "jobs with failure_streak >= 3",
                "n": len(jobs["failure_streaks"]),
                "ids": [s.get("id") for s in jobs["failure_streaks"][:6]],
            }
        )
    n_err = int((jobs.get("last_status") or {}).get("error") or 0)
    n_jobs = int(jobs.get("n_jobs") or 0)
    if n_jobs and n_err >= 15:
        alarms.append(
            {
                "severity": "MEDIUM",
                "why": "jobs.json last_status=error count is high",
                "n_error": n_err,
                "n_jobs": n_jobs,
            }
        )
    status = "ok"
    if any(a["severity"] == "HIGH" for a in alarms):
        status = "alarm"
    elif alarms:
        status = "warn"
    return {
        "ts": _now().isoformat(),
        "window_s": WINDOW_S,
        "status": status,
        "executions": ex,
        "jobs": jobs,
        "missed_24h": missed,
        "failed_24h": failed,
        "alarms": alarms,
        "theory": "missed_runs.scan_missed_runs + timeout-cascade admission",
    }


def _self_test() -> int:
    home = _hermes_home()
    os.environ["HERMES_HOME"] = str(home / "profiles" / "fork")
    assert _hermes_home() == home
    os.environ["HERMES_HOME"] = str(home)
    report = build_report(
        {"status": {"missed": 12, "ok": 80, "failed": 2}, "timeout_124": 1, "n_rows": 100},
        {"failure_streaks": [{"id": "x", "failure_streak": 4}], "n_jobs": 10, "enabled": 10},
    )
    assert report["status"] == "warn"
    report2 = build_report({"status": {"missed": 40}, "timeout_124": 0}, {"failure_streaks": []})
    assert report2["status"] == "alarm"
    print(json.dumps({"status": "ok", "self_test": True}))
    return 0


def _run() -> int:
    root = _hermes_root()
    cutoff = time.time() - WINDOW_S
    ex = scan_executions(root / "cron" / "executions.db", cutoff)
    jobs = scan_jobs(root / "cron" / "jobs.json")
    report = build_report(ex, jobs)
    out = root / "cache" / "cron-missed-runs.json"
    _atomic_write(out, report)
    alarm_path = root / "cache" / "cron-missed-runs-alarm.json"
    if report["status"] in {"warn", "alarm"} and report["alarms"]:
        sev = "HIGH" if report["status"] == "alarm" else "MEDIUM"
        _atomic_write(
            alarm_path,
            {
                "ts": report["ts"],
                "name": "cron-missed-runs-monitor",
                "severity": sev,
                "status": report["status"],
                "summary": f"cron missed={report['missed_24h']} failed={report['failed_24h']}",
                "alarms": report["alarms"],
            },
        )
    elif alarm_path.exists():
        try:
            alarm_path.unlink()
        except OSError:
            pass
    print(json.dumps({"status": report["status"], "out": str(out), "missed": report["missed_24h"]}))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--run", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    # Scheduler does not pass job.args; cron argv is empty → default --run.
    try:
        return _run()
    except Exception as exc:
        print(f"fail-open: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
