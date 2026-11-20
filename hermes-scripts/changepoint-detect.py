#!/usr/bin/env python3
"""GRACE-style PELT changepoint calculus on session turn metrics."""
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

OUT_PATH = CACHE / "session_changepoints.json"
TURN_LOG = CACHE / "turn-behavior.jsonl"

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


def load_series(path: Path, max_lines=5000):
    xs = []
    if not path.exists():
        return xs
    n = 0
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n += 1
            if n > max_lines:
                break
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("tool_name") == "ue_blackbox":
                continue
            suc = rec.get("success")
            ent = rec.get("skill_entropy")
            try:
                y = (1.0 if suc else 0.0) if isinstance(suc, bool) else float(suc if suc is not None else 0.0)
            except (TypeError, ValueError):
                y = 0.0
            try:
                e = float(ent) if ent is not None else 0.0
            except (TypeError, ValueError):
                e = 0.0
            xs.append(0.5 * y + 0.5 * (1.0 / (1.0 + e)))
    return xs


def prefix_moments(xs):
    n = len(xs)
    s = [0.0] * (n + 1)
    q = [0.0] * (n + 1)
    for i, x in enumerate(xs, 1):
        s[i] = s[i - 1] + x
        q[i] = q[i - 1] + x * x
    return s, q


def seg_cost(s, q, a, b):
    """Gaussian SSE cost of xs[a:b] (a inclusive, b exclusive), 0-based via prefix."""
    n = b - a
    if n <= 0:
        return 0.0
    sumx = s[b] - s[a]
    sumsq = q[b] - q[a]
    mean = sumx / n
    return max(0.0, sumsq - n * mean * mean)


def pelt(xs, beta=None):
    n = len(xs)
    if n < 4:
        return []
    if beta is None:
        var = statistics.pvariance(xs) if n > 1 else 1.0
        beta = 2.0 * math.log(n) * max(var, 1e-6)
    s, q = prefix_moments(xs)
    F = [0.0] + [float("inf")] * n
    prev = [-1] * (n + 1)
    R = [0]
    for t in range(1, n + 1):
        best = float("inf")
        best_tau = 0
        new_R = []
        for tau in R:
            cost = F[tau] + seg_cost(s, q, tau, t) + beta
            if cost < best:
                best = cost
                best_tau = tau
            # PELT prune: keep tau if F[tau] + cost(tau,t) <= F[t] candidate bound
            if F[tau] + seg_cost(s, q, tau, t) <= best:
                new_R.append(tau)
        F[t] = best
        prev[t] = best_tau
        new_R.append(t)
        R = new_R
    cps = []
    t = n
    while t > 0 and prev[t] >= 0:
        tau = prev[t]
        if tau > 0:
            cps.append(tau)
        t = tau
        if t == prev[t]:
            break
    cps.reverse()
    return cps


def build_report(xs):
    if len(xs) < 4:
        return {"ts": _now(), "status": "insufficient_data", "n": len(xs), "changepoints": []}
    cps = pelt(xs)
    var = statistics.pvariance(xs) if len(xs) > 1 else 0.0
    beta = 2.0 * math.log(len(xs)) * max(var, 1e-6)
    return {
        "ts": _now(),
        "status": "ok",
        "n": len(xs),
        "n_changepoints": len(cps),
        "changepoints": cps,
        "beta": beta,
        "method": "PELT_gaussian_SSE",
    }


def run(out_path=None, series_path=None):
    dest = out_path or OUT_PATH
    src = series_path or TURN_LOG
    try:
        xs = load_series(src)
        report = build_report(xs)
        _atomic_write_json(dest, report)
        return report
    except Exception as exc:
        err = {"ts": _now(), "status": "error", "error": str(exc), "changepoints": []}
        try:
            _atomic_write_json(dest, err)
        except Exception:
            pass
        return err


def _self_test():
    tmp = Path(tempfile.mkdtemp(prefix="grace-"))
    out = tmp / ("session_changepoints_test_" + uuid.uuid4().hex + ".json")
    rng = random.Random(0)
    a = [rng.gauss(0.2, 0.05) for _ in range(40)]
    b = [rng.gauss(0.8, 0.05) for _ in range(40)]
    c = [rng.gauss(0.3, 0.05) for _ in range(40)]
    xs = a + b + c
    cps = pelt(xs)
    assert len(cps) >= 1, cps
    # injected around 40 and 80
    near = any(abs(cp - 40) <= 8 for cp in cps) or any(abs(cp - 80) <= 8 for cp in cps)
    assert near, cps
    empty = build_report([0.1, 0.2])
    assert empty["status"] == "insufficient_data"
    series = tmp / ("turn-behavior_test_" + uuid.uuid4().hex + ".jsonl")
    with series.open("w", encoding="utf-8") as f:
        for i, x in enumerate(xs):
            f.write(json.dumps({"success": x > 0.5, "skill_entropy": 0.2, "tool_name": "t"}) + "\n")
    r = run(out_path=out, series_path=series)
    assert out.exists()
    json.loads(out.read_text())
    print("[changepoint-detect] --self-test PASS cps={} status={}".format(cps, r.get("status")))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print("[changepoint-detect] --self-test FAIL:", exc)
            return 1
    report = run()
    print(json.dumps({"status": report.get("status"), "n": report.get("n"), "n_changepoints": report.get("n_changepoints")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
