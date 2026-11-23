#!/usr/bin/env python3
"""cron-ucb-safe.py — UCB1 cron-script selection with P(fail) <= 0.1 envelope.

Lattimore bandits + Amodei-style safe exploration.
Arms = cron job_ids. Rewards from executions.db (completed vs failed).
Recency window 24h: stale all-time success must NOT certify safety.

Hard core: any selected arm with n>=10 satisfies Laplace P(failure) <= 0.1.

Usage:
  python3 cron-ucb-safe.py --self-test
  python3 cron-ucb-safe.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Import helpers from sibling aimd_controller (stdlib).
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from aimd_controller import (  # noqa: E402
    FAIL_BOUND,
    UCB_MIN_SAMPLES,
    UCB_RECENCY_SECONDS,
    arm_is_safe,
    laplace_p_fail,
    select_ucb_arm,
)

_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_profile = os.environ.get("HERMES_PROFILE", "")
_root = (_base / "profiles" / _profile) if _profile and "profiles" not in str(_base) else _base
DB_PATH = _root / "cron" / "executions.db"
JOBS_PATH = _root / "cron" / "jobs.json"
OUT_PATH = _root / "cache" / "cron-ucb-safe.json"


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _parse_ts(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (TypeError, ValueError):
        try:
            return float(s)
        except (TypeError, ValueError):
            return None


def load_arms(now: float, recency: float = UCB_RECENCY_SECONDS) -> dict:
    arms: dict = {}
    if not DB_PATH.exists():
        return arms
    cutoff = now - recency
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
        try:
            rows = con.execute(
                "SELECT job_id, status, started_at, finished_at FROM executions"
            ).fetchall()
        finally:
            con.close()
    except Exception:
        return arms
    for job_id, status, started_at, finished_at in rows:
        if not job_id:
            continue
        ts = _parse_ts(finished_at) or _parse_ts(started_at)
        if ts is None or ts < cutoff:
            continue  # stale — ignore for both mean and safety
        st = str(status or "").lower()
        rec = arms.setdefault(str(job_id), {"n": 0, "failures": 0, "last_ts": ts})
        rec["n"] += 1
        if st in ("failed", "error", "fail"):
            rec["failures"] += 1
        rec["last_ts"] = max(float(rec["last_ts"]), float(ts))
    return arms


def self_test() -> int:
    now = 1e9
    safe = {"a": {"n": 30, "failures": 1, "last_ts": now}}
    unsafe = {"b": {"n": 30, "failures": 10, "last_ts": now}}  # 11/32 > 0.1
    stale = {"c": {"n": 30, "failures": 0, "last_ts": now - 2 * UCB_RECENCY_SECONDS}}
    assert arm_is_safe(1, 30, now, now) is True
    assert arm_is_safe(10, 30, now, now) is False
    assert arm_is_safe(0, 30, now - 2 * UCB_RECENCY_SECONDS, now) is False
    picked = select_ucb_arm({**safe, **unsafe, **stale}, t=100, now=now)
    assert picked == "a"
    p = laplace_p_fail(1, 30)
    assert p <= FAIL_BOUND
    print(json.dumps({
        "property": "selected arm P(failure) <= 0.1 (recency-windowed)",
        "passed": True,
        "p_fail_selected": p,
        "stale_rejected": True,
        "unsafe_rejected": True,
    }))
    return 0


def run() -> int:
    now = time.time()
    arms = load_arms(now)
    t = max(sum(a["n"] for a in arms.values()), 1)
    picked = select_ucb_arm(arms, t=t, now=now)
    safe_ids = [k for k, v in arms.items() if arm_is_safe(v["failures"], v["n"], v.get("last_ts"), now)]
    unsafe = [k for k in arms if k not in safe_ids]
    selected_p = None
    if picked and picked in arms:
        selected_p = laplace_p_fail(arms[picked]["failures"], arms[picked]["n"])
        n_picked = arms[picked]["n"]
        if n_picked > 0 and selected_p > FAIL_BOUND:
            print("SAFETY VIOLATION: selected arm P(fail) > 0.1", file=sys.stderr)
            picked = None
            selected_p = None
    out = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "theorem": "Lattimore UCB1 + Amodei safety envelope P(fail)<=0.1",
        "n_arms": len(arms),
        "n_safe": len(safe_ids),
        "n_unsafe": len(unsafe),
        "selected": picked,
        "selected_p_fail": selected_p,
        "fail_bound": FAIL_BOUND,
        "recency_s": UCB_RECENCY_SECONDS,
        "unsafe_job_ids": unsafe[:30],
        "note": "Never run unsafe arms. Stale (no 24h samples) is unsafe if n>0.",
    }
    _atomic_write(OUT_PATH, out)
    print(json.dumps({
        "selected": picked,
        "selected_p_fail": selected_p,
        "n_safe": len(safe_ids),
        "n_unsafe": len(unsafe),
    }))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    return run()


if __name__ == "__main__":
    sys.exit(main())
