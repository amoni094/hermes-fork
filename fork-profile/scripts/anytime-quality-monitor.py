#!/usr/bin/env python3
"""Zilberstein (1996) performance-profile monitor for checkpointed cron jobs.

Q(t) ~ items_per_hour vs expected_rate. Warn when a job is below 50% of the
expected rate (diminishing-returns / stalled anytime contract).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

CHECKPOINT_DIR = _hermes_root / "cache" / "scratch" / "checkpoints"
OUT_PATH = _hermes_root / "omni" / "quality-profiles.json"
LIFECYCLE_DB = _hermes_base / "memory-facts" / "lifecycle.db"
DEFAULT_EXPECTED_RATE = 100.0
WARN_FRACTION = 0.5
DEFAULT_FIT_N = 20


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(raw) -> datetime | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_checkpoint(path: Path) -> dict | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(obj, dict):
        return None
    return obj


def _item_count(obj: dict) -> float:
    if obj.get("item_count") is not None:
        try:
            return float(obj["item_count"])
        except (TypeError, ValueError):
            pass
    completed = obj.get("completed")
    if isinstance(completed, list):
        return float(len(completed))
    start_index = obj.get("start_index")
    if start_index is not None:
        try:
            return float(start_index)
        except (TypeError, ValueError):
            pass
    return 0.0


def monitor(checkpoint_dir: Path | None = None, expected_rate: float = DEFAULT_EXPECTED_RATE) -> dict:
    cdir = checkpoint_dir or CHECKPOINT_DIR
    jobs: list[dict] = []
    warnings: list[str] = []
    if not cdir.is_dir():
        return {
            "checked_at": _utcnow().isoformat(),
            "status": "insufficient_data",
            "reason": "missing_checkpoint_dir",
            "expected_rate": expected_rate,
            "jobs": [],
            "warnings": [],
        }
    files = sorted(p for p in cdir.iterdir() if p.is_file() and p.suffix == ".json" and not p.name.endswith(".tmp"))
    if not files:
        return {
            "checked_at": _utcnow().isoformat(),
            "status": "insufficient_data",
            "reason": "no_checkpoints",
            "expected_rate": expected_rate,
            "jobs": [],
            "warnings": [],
        }
    for path in files:
        obj = _load_checkpoint(path)
        if obj is None:
            continue
        started = _parse_dt(obj.get("started_at") or obj.get("created_at"))
        updated = _parse_dt(obj.get("updated_at"))
        if started is None:
            started = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if updated is None:
            updated = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        elapsed_s = max(0.0, (updated - started).total_seconds())
        elapsed_hours = elapsed_s / 3600.0
        items = _item_count(obj)
        if elapsed_hours <= 0.0:
            rate = None
        else:
            rate = items / elapsed_hours
        job_name = str(obj.get("job_name") or path.stem)
        below = bool(rate is not None and rate < WARN_FRACTION * expected_rate)
        rec = {
            "job_name": job_name,
            "path": str(path),
            "status": obj.get("status"),
            "item_count": items,
            "started_at": started.isoformat(),
            "updated_at": updated.isoformat(),
            "elapsed_hours": elapsed_hours,
            "items_per_hour": rate,
            "expected_rate": expected_rate,
            "below_half_expected": below,
        }
        jobs.append(rec)
        if below:
            msg = (
                "WARNING "
                + job_name
                + " items_per_hour="
                + ("%.3f" % rate)
                + " < 50% of expected_rate="
                + str(expected_rate)
            )
            warnings.append(msg)
            print(msg)
    return {
        "checked_at": _utcnow().isoformat(),
        "status": "ok",
        "expected_rate": expected_rate,
        "jobs": jobs,
        "warnings": warnings,
    }


def _atomic_write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(path))


def _exp_quality(t, q_max, r):
    return q_max * (1.0 - math.e ** (-r * t))


def fit_quality_profile(run_history: list[tuple[float, float]]):
    """Fit Q(t) = Q_max*(1 - exp(-r*t)). Returns {q_max, r, goodness_of_fit_r2} or None."""
    if not run_history or len(run_history) < 3:
        return None
    try:
        import numpy as np
        from scipy.optimize import curve_fit
    except ImportError:
        return None

    def _model(t, q_max, r):
        return q_max * (1.0 - np.exp(-r * t))

    t = np.array([float(pair[0]) for pair in run_history], dtype=float)
    q = np.array([float(pair[1]) for pair in run_history], dtype=float)
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(q)):
        return None
    q_guess = float(max(np.max(q), 1e-6))
    try:
        popt, _pcov = curve_fit(
            _model,
            t,
            q,
            p0=(q_guess, 0.2),
            bounds=([0.0, 0.0], [np.inf, np.inf]),
            maxfev=8000,
        )
    except Exception:
        return None
    q_max = float(popt[0])
    r = float(popt[1])
    pred = _model(t, q_max, r)
    ss_res = float(np.sum((q - pred) ** 2))
    ss_tot = float(np.sum((q - np.mean(q)) ** 2))
    r2 = 1.0 if ss_tot <= 0.0 else 1.0 - ss_res / ss_tot
    return {"q_max": q_max, "r": r, "goodness_of_fit_r2": r2}


def should_continue_running(
    elapsed: float,
    q_now: float,
    profile: dict,
    cost_per_s: float = 0.001,
) -> bool:
    """Zilberstein VoI: continue iff expected gain over 1s exceeds cost."""
    if not profile:
        return False
    try:
        q_max = float(profile["q_max"])
        r = float(profile["r"])
    except (KeyError, TypeError, ValueError):
        return False
    expected_gain = q_max * (1.0 - math.exp(-r * (elapsed + 1.0))) - q_now
    cost = cost_per_s * 1.0
    return (expected_gain - cost) > 0.0


def _rows_to_history(rows: list) -> list[tuple[float, float]]:
    if len(rows) < 3:
        return []
    parsed = []
    for ts, quality in rows:
        try:
            qv = float(quality)
        except (TypeError, ValueError):
            continue
        parsed.append((_parse_dt(ts), qv))
    parsed = [(dt, qv) for dt, qv in parsed if qv is not None]
    if len(parsed) < 3:
        return []
    t0 = next((dt for dt, _qv in parsed if dt is not None), None)
    hist: list[tuple[float, float]] = []
    for i, (dt, qv) in enumerate(parsed):
        if t0 is None or dt is None:
            elapsed = float(i)
        else:
            elapsed = max(0.0, (dt - t0).total_seconds())
        hist.append((elapsed, qv))
    if hist and hist[-1][0] == 0.0 and all(item[0] == 0.0 for item in hist):
        hist = [(float(i), qv) for i, (_e, qv) in enumerate(hist)]
    return hist


def quality_history_from_db(db_path: Path | None = None, n: int = DEFAULT_FIT_N) -> list[tuple[float, float]]:
    """Last N (elapsed_seconds, quality_score) pairs from lifecycle.db."""
    path = Path(db_path) if db_path else LIFECYCLE_DB
    if not path.exists():
        return []
    conn = sqlite3.connect(str(path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        tables = {
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "trajectory_audits" in tables:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(trajectory_audits)")]
            if "quality_score" in cols and "ts" in cols:
                rows = conn.execute(
                    "SELECT ts, quality_score FROM trajectory_audits "
                    "WHERE quality_score IS NOT NULL ORDER BY ts DESC LIMIT ?",
                    (int(n),),
                ).fetchall()
                hist = _rows_to_history(list(reversed(rows)))
                if hist:
                    return hist
        if "fact_lifecycle" in tables:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(fact_lifecycle)")]
            if "quality_score" in cols:
                time_col = "updated_at" if "updated_at" in cols else (
                    "created_at" if "created_at" in cols else None
                )
                if time_col:
                    rows = conn.execute(
                        "SELECT " + time_col + ", quality_score FROM fact_lifecycle "
                        "WHERE quality_score IS NOT NULL ORDER BY " + time_col + " DESC LIMIT ?",
                        (int(n),),
                    ).fetchall()
                    hist = _rows_to_history(list(reversed(rows)))
                    if hist:
                        return hist
        return []
    except Exception:
        return []
    finally:
        conn.close()


def _self_test() -> int:
    import tempfile
    import uuid as _uuid

    d = Path(tempfile.mkdtemp(prefix="aqm-")) / ("cp_" + _uuid.uuid4().hex)
    d.mkdir(parents=True)
    slow = {
        "job_name": "slow-job",
        "item_count": 10,
        "started_at": "2026-10-29T00:00:00+00:00",
        "updated_at": "2026-10-29T02:00:00+00:00",
        "status": "partial",
    }
    (d / "slow-job.json").write_text(json.dumps(slow), encoding="utf-8")
    report = monitor(checkpoint_dir=d, expected_rate=100.0)
    assert report["jobs"][0]["below_half_expected"] is True
    assert report["jobs"][0]["items_per_hour"] == 5.0
    empty = monitor(checkpoint_dir=d / "missing", expected_rate=100.0)
    assert empty["status"] == "insufficient_data"

    true_qmax = 0.9
    true_r = 0.25
    hist = [
        (float(t), true_qmax * (1.0 - math.exp(-true_r * t)))
        for t in (0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 14.0, 20.0)
    ]
    prof = fit_quality_profile(hist)
    assert prof is not None, "curve_fit returned None"
    rel = abs(prof["q_max"] - true_qmax) / true_qmax
    assert rel <= 0.05, prof
    assert should_continue_running(0.5, hist[0][1], prof, cost_per_s=0.001) is True
    late_q = true_qmax * (1.0 - math.exp(-true_r * 200.0))
    assert should_continue_running(200.0, late_q, prof, cost_per_s=0.001) is False
    assert fit_quality_profile([(1.0, 0.1), (2.0, 0.2)]) is None

    print(json.dumps({
        "ok": True,
        "slow": report["jobs"][0]["items_per_hour"],
        "q_max": prof["q_max"],
        "r": prof["r"],
        "r2": prof["goodness_of_fit_r2"],
    }))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Anytime quality-profile monitor")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--fit-profile", action="store_true")
    parser.add_argument("--fit-n", type=int, default=DEFAULT_FIT_N)
    parser.add_argument("--expected-rate", type=float, default=float(os.environ.get("ANYTIME_EXPECTED_RATE") or DEFAULT_EXPECTED_RATE))
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    if args.fit_profile:
        hist = quality_history_from_db(n=args.fit_n)
        prof = fit_quality_profile(hist)
        print(json.dumps({"n_points": len(hist), "profile": prof}, indent=2))
        return 0
    report = monitor(expected_rate=args.expected_rate)
    out = Path(args.out) if args.out else OUT_PATH
    _atomic_write(out, report)
    print(
        "anytime-quality-monitor SUMMARY "
        + json.dumps(
            {
                "out": str(out),
                "status": report.get("status"),
                "n_jobs": len(report.get("jobs") or []),
                "n_warnings": len(report.get("warnings") or []),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
