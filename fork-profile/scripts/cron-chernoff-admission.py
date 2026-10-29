#!/usr/bin/env python3
"""Chernoff admission companion: P(load > (1+δ)μ) even when U < ln 2 (Motwani Ch 4)."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
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
REPORT_PATH = _hermes_root / "omni" / "cron-chernoff-admission.json"


def _f(x, default=0.0) -> float:
    try:
        v = float(x or 0.0)
    except (TypeError, ValueError):
        v = default
    return v


def _cadence_s(job: dict) -> float | None:
    sched = job.get("schedule") or {}
    if str(sched.get("kind") or "") not in ("cron", "interval"):
        return None
    expr = str(sched.get("expr") or "")
    parts = expr.split()
    if len(parts) != 5:
        return None
    minute, hour, dom, _m, dow = parts
    try:
        if minute.startswith("*/"):
            return max(60.0, float(int(minute[2:])) * 60.0)
        if hour.startswith("*/"):
            return float(int(hour[2:])) * 3600.0
        if dow not in ("*", "?") and dom in ("*", "?"):
            return 7 * 86400.0
        if dom not in ("*", "?"):
            return 30 * 86400.0
        if hour not in ("*", "?"):
            return 86400.0
        if minute not in ("*", "?"):
            return 3600.0
    except (TypeError, ValueError):
        return None
    return 3600.0


def chernoff_overload_prob(jobs, window_s=60, delta=0.5):
    """Additive Chernoff on independent Bernoulli job-fires in a window.

    Bound: P(X > (1+δ)μ) ≤ exp(-μ δ² / 3) for 0<δ<1 (Motwani Thm 4.4 style).
    """
    try:
        window_s = float(window_s or 60)
    except (TypeError, ValueError):
        window_s = 60.0
    try:
        delta = float(delta or 0.5)
    except (TypeError, ValueError):
        delta = 0.5
    mu = 0.0
    u = 0.0
    for j in jobs:
        cad = _cadence_s(j)
        if not cad or cad <= 0:
            continue
        p = min(1.0, window_s / cad)
        mu += p
        timeout = _f(j.get("timeout", 120), 120.0)
        u += timeout / cad
    if mu <= 0:
        return {"P": 0.0, "mu": 0.0, "U": u, "alert": False}
    d = min(1.0, max(1e-6, delta))
    p_over = math.exp(-mu * d * d / 3.0)
    return {
        "P": p_over,
        "mu": mu,
        "U": u,
        "delta": d,
        "ln2": math.log(2.0),
        "alert": bool(p_over > 0.05),
        "u_below_ln2": u < math.log(2.0),
    }


def _load_jobs(path: Path) -> list[dict]:
    if not path.exists():
        return []
    obj = json.loads(path.read_bytes().decode("utf-8", errors="replace"))
    if isinstance(obj, list):
        return [j for j in obj if isinstance(j, dict)]
    if isinstance(obj, dict):
        inner = obj.get("jobs") or []
        if isinstance(inner, list):
            return [j for j in inner if isinstance(j, dict)]
    return []


def run_report() -> dict:
    jobs = _load_jobs(JOBS_PATH)
    ch = chernoff_overload_prob(jobs)
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "chernoff": ch,
        "n_jobs": len(jobs),
        "alert_when_U_ok": bool(ch.get("alert") and ch.get("u_below_ln2")),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(REPORT_PATH))
    return report


def _self_test() -> int:
    jobs = [{"timeout": 10, "schedule": {"kind": "cron", "expr": "* * * * *"}} for _ in range(5)]
    r = chernoff_overload_prob(jobs, window_s=60, delta=0.5)
    assert 0.0 <= r["P"] <= 1.0
    empty = chernoff_overload_prob([], window_s=60)
    assert empty["P"] == 0.0
    print(json.dumps({"ok": True, "P": r["P"], "U": r["U"], "alert": r["alert"]}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Chernoff cron admission")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    report = run_report()
    ch = report.get("chernoff") or {}
    print(json.dumps({"ok": True, "P": ch.get("P"), "U": ch.get("U"), "alert": ch.get("alert")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
