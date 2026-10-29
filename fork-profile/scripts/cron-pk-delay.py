#!/usr/bin/env python3
"""Pollaczek–Khinchine delay + Little's Law monitor for cron (Harchol-Balter).

Completed runs only — never in-flight (inspection paradox).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
JOBS_PATH = _hermes_root / "cron" / "jobs.json"
_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
_profile = os.environ.get("HERMES_PROFILE", "default")
_base = _home if "profiles" in str(_home) else _home / "profiles" / _profile
EXEC_DB = _base / "cron" / "executions.db"
REPORT_PATH = _hermes_root / "omni" / "cron-pk-delay-report.json"
DEFAULT_TIMEOUT = 120.0


def _f(x, default=0.0) -> float:
    try:
        v = float(x or 0.0)
    except (TypeError, ValueError):
        v = default
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return default
    return v


def _job_timeout_seconds(job: dict) -> float:
    v = job.get("timeout", job.get("timeout_seconds", DEFAULT_TIMEOUT))
    t = _f(v, DEFAULT_TIMEOUT)
    return t if t > 0 else DEFAULT_TIMEOUT


def _job_cadence_seconds(job: dict) -> float | None:
    sched = job.get("schedule") or {}
    kind = str(sched.get("kind") or "")
    if kind in ("once", "event"):
        return None
    expr = str(sched.get("expr") or "")
    parts = expr.split()
    if len(parts) != 5:
        return None
    minute, hour, dom, _month, dow = parts

    def is_star(x: str) -> bool:
        return x in ("*", "?")

    try:
        if minute.startswith("*/") and all(is_star(x) for x in (hour, dom, _month, dow)):
            return float(int(minute[2:])) * 60.0
        if hour.startswith("*/") and is_star(minute) and all(is_star(x) for x in (dom, _month, dow)):
            return float(int(hour[2:])) * 3600.0
        if not is_star(dow) and is_star(dom) and is_star(_month):
            return 7.0 * 86400.0
        if not is_star(dom) and is_star(dow):
            return 30.0 * 86400.0
        if is_star(dow) and is_star(dom) and not is_star(hour) and not is_star(minute):
            return 86400.0
        if is_star(dow) and is_star(dom) and is_star(hour) and not is_star(minute):
            return 3600.0
        if all(is_star(x) for x in (minute, hour, dom, _month, dow)):
            return 60.0
    except (TypeError, ValueError):
        return None
    return 86400.0


def job_service_moments(conn, job_id, lookback=50):
    """Completed runs only — never in-flight (inspection paradox)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(executions)").fetchall()}
    if "duration_s" not in cols:
        return None
    status_col = "status" if "status" in cols else "state"
    rows = conn.execute(
        f"""SELECT duration_s FROM executions
           WHERE job_id=? AND {status_col}='completed' AND duration_s IS NOT NULL
           ORDER BY rowid DESC LIMIT ?""",
        (job_id, lookback),
    ).fetchall()
    xs = [r[0] for r in rows if r[0] is not None and _f(r[0]) > 0]
    if len(xs) < 3:
        return None
    n = len(xs)
    m1 = sum(xs) / n
    m2 = sum(x * x for x in xs) / n
    return m1, m2, (m2 / (m1 * m1) - 1.0)


def pk_wait(lambda_rate, mean_s, m2):
    rho = lambda_rate * mean_s
    if rho >= 1.0:
        return float("inf"), rho
    return lambda_rate * m2 / (2.0 * (1.0 - rho)), rho


def farm_pk_report(jobs, moments_by_id=None, horizon_s=3600.0):
    """Treat the parallel pool as one M/G/1 of speed k later; here k=1 bound."""
    del horizon_s
    moments_by_id = moments_by_id or {}
    lam = 0.0
    mean_s = 0.0
    m2 = 0.0
    for j in jobs:
        cad = _job_cadence_seconds(j)
        if not cad:
            continue
        lam_i = 1.0 / cad
        mom = moments_by_id.get(j.get("id"))
        e_s = mom[0] if mom else _job_timeout_seconds(j)
        e_s2 = mom[1] if mom else e_s * e_s
        lam += lam_i
        mean_s += lam_i * e_s
        m2 += lam_i * e_s2
    if lam <= 0:
        return {"status": "EMPTY"}
    mean_s /= lam
    m2 /= lam
    w, rho = pk_wait(lam, mean_s, m2)
    c2 = m2 / (mean_s * mean_s) - 1.0 if mean_s else 0.0
    return {
        "lambda": lam,
        "E[S]": mean_s,
        "E[S2]": m2,
        "C2": c2,
        "rho_k1": rho,
        "E[W]_k1": w,
        "status": "UNSTABLE" if rho >= 1 else ("WARN_VARIABILITY" if c2 > 4 else "OK"),
    }


def littles_snapshot(conn, window_s=3600.0):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(executions)").fetchall()}
    status_col = "status" if "status" in cols else "state"
    L = conn.execute(
        f"SELECT COUNT(*) FROM executions WHERE {status_col} IN ('running','claimed')"
    ).fetchone()[0]
    now = time.time()
    dur_sql = "COALESCE(SUM(duration_s),0)" if "duration_s" in cols else "0"
    if "finished_at" in cols:
        n_done, sum_t = conn.execute(
            f"""SELECT COUNT(*), {dur_sql} FROM executions
               WHERE {status_col}='completed' AND finished_at IS NOT NULL""",
        ).fetchone()
    else:
        n_done, sum_t = 0, 0.0
    lam = n_done / window_s if window_s else 0.0
    W_obs = (L / lam) if lam > 0 else float("inf")
    E_S = (sum_t / n_done) if n_done else 0.0
    return {
        "L": L,
        "lambda": lam,
        "W_little": W_obs,
        "E[S]": E_S,
        "Wq": max(0.0, W_obs - E_S) if math.isfinite(W_obs) else float("inf"),
        "alert": bool(math.isfinite(W_obs) and W_obs > 3.0 * max(E_S, 1.0)),
        "now": now,
    }


def _load_jobs(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw = path.read_bytes().decode("utf-8", errors="replace")
    obj = json.loads(raw)
    if isinstance(obj, list):
        return [j for j in obj if isinstance(j, dict)]
    if isinstance(obj, dict):
        inner = obj.get("jobs") or []
        if isinstance(inner, list):
            return [j for j in inner if isinstance(j, dict)]
        if isinstance(inner, dict):
            return [j for j in inner.values() if isinstance(j, dict)]
    return []


def run_report() -> dict:
    jobs = _load_jobs(JOBS_PATH)
    moments = {}
    little = {"alert": False}
    if EXEC_DB.exists():
        conn = sqlite3.connect(str(EXEC_DB), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            for j in jobs:
                jid = j.get("id")
                if jid:
                    moments[jid] = job_service_moments(conn, jid)
            little = littles_snapshot(conn)
        finally:
            conn.close()
    farm = farm_pk_report(jobs, {k: v for k, v in moments.items() if v})
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "farm": farm,
        "little": little,
        "n_jobs": len(jobs),
        "n_with_moments": sum(1 for v in moments.values() if v),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    os.replace(str(tmp), str(REPORT_PATH))
    return report


def _self_test() -> int:
    w, rho = pk_wait(0.1, 2.0, 8.0)
    assert rho == 0.2
    assert w > 0
    inf, rho2 = pk_wait(1.0, 2.0, 4.0)
    assert rho2 >= 1.0 and inf == float("inf")
    jobs = [
        {"id": "a", "timeout": 10, "schedule": {"kind": "cron", "expr": "0 * * * *"}},
        {"id": "b", "timeout": 20, "schedule": {"kind": "cron", "expr": "0 * * * *"}},
    ]
    r = farm_pk_report(jobs, {})
    assert r["status"] in ("OK", "WARN_VARIABILITY", "UNSTABLE")
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE executions (job_id TEXT, status TEXT, duration_s REAL, finished_at TEXT)"
    )
    conn.executemany(
        "INSERT INTO executions VALUES (?,?,?,?)",
        [("a", "completed", 1.0, "t"), ("a", "completed", 2.0, "t"), ("a", "completed", 3.0, "t")],
    )
    mom = job_service_moments(conn, "a", lookback=50)
    assert mom is not None and mom[0] == 2.0
    snap = littles_snapshot(conn, window_s=3600.0)
    assert "L" in snap
    print(json.dumps({"ok": True, "pk_w": w, "farm": r["status"], "m1": mom[0]}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="PK delay + Little monitor")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    report = run_report()
    print(json.dumps({"ok": True, "farm": report.get("farm", {}).get("status"),
                      "little_alert": report.get("little", {}).get("alert")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
