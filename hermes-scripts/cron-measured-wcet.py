#!/usr/bin/env python3
"""Liu & Layland (1973) measured C_i from cron executions.db.

Admission currently uses timeout_seconds as C_i, which inflates U >> 1.
This script computes p95 runtime from started_at/finished_at (and duration_s
when present) and writes cron-measured-utilisation.json for the laptop
governor and for advisory EDF utilisation.

stdlib only. Fail-open. --self-test and --run.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


def _profile_name() -> str:
    profile = os.environ.get("HERMES_PROFILE", "").strip()
    if profile:
        return profile
    raw = os.environ.get("HERMES_HOME", "").strip()
    if raw:
        p = Path(raw)
        if p.parent.name == "profiles":
            return p.name
    if (_hermes_home() / "profiles" / "fork").exists():
        return "fork"
    return ""


def _hermes_root() -> Path:
    base = _hermes_home()
    profile = _profile_name()
    return (base / "profiles" / profile) if profile else base


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    tmp = path.with_name(path.name + ".tmp")
    payload = json.dumps(obj, indent=2) + "\n"
    with open(str(lock), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def percentile(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    k = (p / 100.0) * (len(ys) - 1)
    lo = int(k)
    hi = min(lo + 1, len(ys) - 1)
    frac = k - lo
    return ys[lo] * (1.0 - frac) + ys[hi] * frac


def parse_period_s(job: dict) -> float | None:
    sched = job.get("schedule") or {}
    if not isinstance(sched, dict):
        return None
    kind = str(sched.get("kind") or "").lower()
    if kind == "interval":
        minutes = sched.get("minutes")
        if minutes is None:
            return None
        try:
            m = float(minutes)
        except (TypeError, ValueError):
            return None
        if m <= 0:
            return None
        return m * 60.0
    expr = str(sched.get("expr") or "").strip()
    parts = expr.split()
    if len(parts) != 5:
        return None
    minute, hour, dom, month, dow = parts

    def step_seconds(field: str, unit: float, cycle: float) -> float | None:
        if field == "*":
            return unit
        if field.startswith("*/"):
            try:
                step = float(field[2:])
            except ValueError:
                return None
            if step <= 0:
                return None
            return step * unit
        if field.isdigit():
            return cycle
        return None

    # weekly: day-of-week constrained
    if dow not in ("*", "?") and minute != "*" and hour != "*":
        return 7.0 * 86400.0
    s = step_seconds(minute, 60.0, 3600.0)
    if minute.startswith("*/") or minute == "*":
        return s
    s = step_seconds(hour, 3600.0, 86400.0)
    if hour.startswith("*/") or hour == "*":
        return s
    if dom not in ("*", "?") or month not in ("*", "?"):
        return 86400.0
    return 86400.0


def duration_from_row(started_at, finished_at, duration_s) -> float | None:
    if duration_s is not None:
        try:
            d = float(duration_s)
            if d >= 0:
                return d
        except (TypeError, ValueError):
            pass
    a = _parse_ts(started_at)
    b = _parse_ts(finished_at)
    if a is None or b is None:
        return None
    d = (b - a).total_seconds()
    if d < 0:
        return None
    return d


def load_jobs(jobs_path: Path) -> list[dict]:
    if not jobs_path.exists():
        return []
    try:
        data = json.loads(jobs_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    jobs = data.get("jobs", data) if isinstance(data, dict) else data
    if isinstance(jobs, dict):
        jobs = list(jobs.values())
    return jobs if isinstance(jobs, list) else []


def collect_durations(db_path: Path) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    if not db_path.exists():
        return out
    try:
        conn = sqlite3.connect(str(db_path), timeout=30)
    except sqlite3.Error:
        return out
    try:
        try:
            rows = conn.execute(
                "SELECT job_id, started_at, finished_at, duration_s, status "
                "FROM executions"
            ).fetchall()
        except sqlite3.Error:
            return out
    finally:
        conn.close()
    for job_id, started_at, finished_at, duration_s, status in rows:
        if status and str(status).lower() not in ("completed", "ok", "success", "done"):
            # still count completed-like; skip running/leased
            if str(status).lower() in ("running", "leased", "claimed", "pending"):
                continue
        d = duration_from_row(started_at, finished_at, duration_s)
        if d is None:
            continue
        # clip absurd outliers (hung jobs that eventually marked finished)
        if d > 6 * 3600:
            continue
        key = str(job_id or "")
        if not key:
            continue
        out.setdefault(key, []).append(d)
    return out


def build_report(jobs: list[dict], durations: dict[str, list[float]]) -> dict:
    by_id = {}
    by_base = {}
    for j in jobs:
        if not isinstance(j, dict):
            continue
        jid = str(j.get("id") or "")
        if jid:
            by_id[jid] = j
        script = str(j.get("script") or "")
        if script:
            by_base.setdefault(Path(script).name, []).append(jid)

    job_rows = []
    u_measured = 0.0
    n_with_c = 0
    for jid, xs in durations.items():
        job = by_id.get(jid, {})
        p50 = percentile(xs, 50)
        p95 = percentile(xs, 95)
        mean = sum(xs) / len(xs)
        period = parse_period_s(job) if job else None
        u = None
        if p95 is not None and period and period > 0:
            u = p95 / period
            u_measured += u
            n_with_c += 1
        script = str(job.get("script") or "")
        row = {
            "job_id": jid,
            "name": job.get("name") or jid,
            "script": script,
            "basename": Path(script).name if script else "",
            "n": len(xs),
            "p50_s": p50,
            "p95_s": p95,
            "mean_s": mean,
            "T_s": period,
            "U": u,
            "enabled": job.get("enabled", True),
        }
        job_rows.append(row)

    job_rows.sort(key=lambda r: -(r.get("p95_s") or 0))
    by_basename: dict[str, float] = {}
    for r in job_rows:
        b = r.get("basename")
        p95 = r.get("p95_s")
        if not b or p95 is None:
            continue
        prev = by_basename.get(str(b))
        if prev is None or float(p95) > prev:
            by_basename[str(b)] = float(p95)
    return {
        "ts": _now(),
        "status": "ok" if job_rows else "insufficient_data",
        "n_executions_jobs": len(durations),
        "n_jobs_with_C": n_with_c,
        "U_measured": u_measured,
        "edf_feasible": u_measured <= 1.0,
        "theory": "Liu-Layland-1973 EDF U<=1 using p95(C_i)/T_i",
        "jobs": job_rows,
        "by_basename": by_basename,
    }


def run(root: Path | None = None) -> dict:
    root = root or _hermes_root()
    report = build_report(
        load_jobs(root / "cron" / "jobs.json"),
        collect_durations(root / "cron" / "executions.db"),
    )
    out = root / "cache" / "cron-measured-utilisation.json"
    _atomic_write(out, report)
    return report


def _self_test() -> int:
    # path stripping
    os.environ["HERMES_HOME"] = str(Path.home() / ".hermes" / "profiles" / "fork")
    os.environ.pop("HERMES_PROFILE", None)
    assert _hermes_home() == Path.home() / ".hermes", _hermes_home()
    os.environ["HERMES_HOME"] = str(Path.home() / ".hermes")
    os.environ["HERMES_PROFILE"] = "fork"
    assert _hermes_home() == Path.home() / ".hermes"

    assert abs((percentile([1.0, 2.0, 3.0, 4.0], 50) or 0) - 2.5) < 1e-9
    assert duration_from_row(
        "2026-01-01T00:00:00+00:00",
        "2026-01-01T00:00:05+00:00",
        None,
    ) == 5.0
    assert duration_from_row(None, None, 3.2) == 3.2
    daily = parse_period_s({"schedule": {"kind": "cron", "expr": "0 3 * * *"}})
    assert daily == 86400.0, daily
    hourly = parse_period_s({"schedule": {"kind": "cron", "expr": "0 * * * *"}})
    assert hourly == 3600.0, hourly
    interval = parse_period_s({"schedule": {"kind": "interval", "minutes": 30}})
    assert interval == 1800.0, interval

    jobs = [
        {
            "id": "j1",
            "name": "fast",
            "script": "/x/fast.py",
            "schedule": {"kind": "cron", "expr": "0 * * * *"},
        }
    ]
    durs = {"j1": [1.0, 1.2, 1.1, 4.0]}
    report = build_report(jobs, durs)
    assert report["status"] == "ok"
    assert report["jobs"][0]["n"] == 4
    assert report["U_measured"] > 0
    assert report["edf_feasible"] is True
    empty = build_report([], {})
    assert empty["status"] == "insufficient_data"
    print("[cron-measured-wcet] --self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Measured cron WCET (Liu-Layland C_i)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[cron-measured-wcet] --self-test FAIL: {exc}")
            return 1
    try:
        report = run()
        print(json.dumps({
            "status": report.get("status"),
            "U_measured": report.get("U_measured"),
            "n_jobs_with_C": report.get("n_jobs_with_C"),
            "edf_feasible": report.get("edf_feasible"),
            "top": [
                {"name": r.get("name"), "p95_s": r.get("p95_s"), "U": r.get("U")}
                for r in (report.get("jobs") or [])[:8]
            ],
        }, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
