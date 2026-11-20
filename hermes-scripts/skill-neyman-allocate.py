#!/usr/bin/env python3
"""Neyman allocation over skill success-rate variances (speculative evaluation)."""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import random
import sqlite3
import statistics
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
_lifecycle_home = _hermes_base.parent.parent if _hermes_base.parent.name == "profiles" else _hermes_base
LIFECYCLE_DB = _lifecycle_home / "memory-facts" / "lifecycle.db"
CACHE = _hermes_root / "cache"

OUT_PATH = CACHE / "routing-neyman.json"
MIN_N = 5

def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    tmp = path.with_name(path.name + ".tmp")
    payload = json.dumps(obj, indent=2) + "\n"
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _connect(db: Path):
    conn = sqlite3.connect(str(db), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _success_from_outcome(outcome):
    if outcome is None:
        return None
    s = str(outcome).strip().lower()
    if s in ("ok", "success", "true", "1", "pass"):
        return 1.0
    if s in ("fail", "failure", "false", "0", "error"):
        return 0.0
    if s == "partial":
        return 0.5
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    if v != v:
        return None
    return max(0.0, min(1.0, v))


def load_series(db_path: Path, limit=4000):
    series = defaultdict(list)
    if not db_path.exists():
        return {}
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT tool_name, outcome FROM tool_review_log ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    for name, outcome in rows:
        if not name or name == "ue_blackbox":
            continue
        v = _success_from_outcome(outcome)
        if v is None:
            continue
        series[str(name)].append(v)
    return dict(series)


def neyman_weights(series, total_budget=100.0):
    stats = {}
    sigmas = {}
    for name, xs in series.items():
        if len(xs) < MIN_N:
            continue
        mu = sum(xs) / len(xs)
        var = statistics.pvariance(xs) if len(xs) > 1 else 0.0
        sigma = math.sqrt(max(var, 1e-12))
        stats[name] = {
            "n": len(xs),
            "mean": mu,
            "var": var,
            "sigma": sigma,
            "success_count": round(sum(xs)),
            "failure_count": int(len(xs) - round(sum(xs))),
        }
        sigmas[name] = sigma
    z = sum(sigmas.values())
    if z <= 0:
        return {}, stats
    weights = {k: (v / z) * float(total_budget) for k, v in sigmas.items()}
    for k, w in weights.items():
        stats[k]["neyman_n"] = w
        stats[k]["weight"] = sigmas[k] / z
    return weights, stats


def build_report(series, total_budget=100.0):
    weights, stats = neyman_weights(series, total_budget=total_budget)
    if not stats:
        return {"ts": _now(), "status": "insufficient_data", "n_skills": 0, "skills": {}, "weights": {}}
    return {
        "ts": _now(),
        "status": "ok",
        "n_skills": len(stats),
        "total_budget": total_budget,
        "weights": weights,
        "skills": stats,
    }


def run(out_path=None, db_path=None):
    dest = out_path or OUT_PATH
    db = db_path or LIFECYCLE_DB
    try:
        report = build_report(load_series(db))
        _atomic_write_json(dest, report)
        return report
    except Exception as exc:
        err = {"ts": _now(), "status": "error", "error": str(exc), "n_skills": 0}
        try:
            _atomic_write_json(dest, err)
        except Exception:
            pass
        return err


def _self_test():
    tmp = Path(tempfile.mkdtemp(prefix="neyman-"))
    out = tmp / ("routing-neyman_test_" + uuid.uuid4().hex + ".json")
    rng = random.Random(1)
    high_var = [1.0 if rng.random() < 0.5 else 0.0 for _ in range(80)]
    low_var = [1.0 if rng.random() < 0.95 else 0.0 for _ in range(80)]
    w, st = neyman_weights({"noisy": high_var, "stable": low_var}, total_budget=100)
    assert w["noisy"] > w["stable"], (w, st)
    empty = build_report({})
    assert empty["status"] == "insufficient_data"
    run(out_path=out, db_path=tmp / "no.db")
    assert out.exists()
    json.loads(out.read_text())
    print("[skill-neyman-allocate] --self-test PASS noisy={:.1f} stable={:.1f}".format(w["noisy"], w["stable"]))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print("[skill-neyman-allocate] --self-test FAIL:", exc)
            return 1
    report = run()
    print(json.dumps({"status": report.get("status"), "n_skills": report.get("n_skills")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
