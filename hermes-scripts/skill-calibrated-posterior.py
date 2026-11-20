#!/usr/bin/env python3
"""Bagged martingale posteriors for skill/tool routing uncertainty."""
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

OUT_PATH = CACHE / "routing-calibrated-posterior.json"
B_DEFAULT = 50
MIN_N = 8
CRED = 0.9

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
    if s in ("partial",):
        return 0.5
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    if v != v:
        return None
    return 1.0 if v >= 0.5 else 0.0


def load_observations(db_path: Path, limit: int = 500):
    out = defaultdict(list)
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
        out[str(name)].append(v)
    return dict(out)


def bootstrap_ci(xs, B=B_DEFAULT, cred=CRED, rng=None):
    if rng is None:
        rng = random.Random(0)
    n = len(xs)
    if n == 0:
        return None
    means = []
    for _ in range(int(B)):
        sample = [xs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    alpha = 1.0 - float(cred)
    lo_i = max(0, math.floor(alpha / 2.0 * B))
    hi_i = min(B - 1, int(math.ceil((1.0 - alpha / 2.0) * B) - 1))
    point = sum(xs) / n
    return {
        "n": n,
        "mean": point,
        "ci_lo": means[lo_i],
        "ci_hi": means[hi_i],
        "width": means[hi_i] - means[lo_i],
        "B": int(B),
        "cred": float(cred),
    }


def width_monotone(xs, Bs=(10, 25, 50, 100)):
    widths = []
    for B in Bs:
        ci = bootstrap_ci(xs, B=B, rng=random.Random(1))
        if ci is None:
            return False
        widths.append(ci["width"])
    return widths[-1] <= widths[0] * 1.5 + 1e-9


def build_report(obs, B=B_DEFAULT):
    skills = {}
    rng = random.Random(7)
    for name, xs in sorted(obs.items(), key=lambda kv: -len(kv[1])):
        if len(xs) < MIN_N:
            continue
        ci = bootstrap_ci(xs, B=B, rng=rng)
        if ci is None:
            continue
        skills[name] = ci
        skills[name]["low_confidence"] = ci["width"] > 0.25
    if not skills:
        return {"ts": _now(), "status": "insufficient_data", "n_skills": 0, "B": int(B), "skills": {}}
    return {"ts": _now(), "status": "ok", "n_skills": len(skills), "B": int(B), "cred": CRED, "skills": skills}


def run(out_path=None, db_path=None, B=B_DEFAULT):
    dest = out_path or OUT_PATH
    db = db_path or LIFECYCLE_DB
    try:
        obs = load_observations(db)
        report = build_report(obs, B=B)
        _atomic_write_json(dest, report)
        return report
    except Exception as exc:
        err = {"ts": _now(), "status": "error", "error": str(exc), "n_skills": 0, "skills": {}}
        try:
            _atomic_write_json(dest, err)
        except Exception:
            pass
        return err


def _self_test():
    tmp = Path(tempfile.mkdtemp(prefix="scp-"))
    out = tmp / ("routing-calibrated-posterior_test_" + uuid.uuid4().hex + ".json")
    rng = random.Random(42)
    xs = [1.0 if rng.random() < 0.8 else 0.0 for _ in range(200)]
    ci = bootstrap_ci(xs, B=50, rng=random.Random(0))
    assert ci is not None
    assert 0.0 <= ci["ci_lo"] <= ci["mean"] <= ci["ci_hi"] <= 1.0
    assert ci["width"] < 0.3
    assert width_monotone(xs)
    empty = build_report({})
    assert empty["status"] == "insufficient_data"
    hits = 0
    trials = 30
    for t in range(trials):
        sample = [1.0 if rng.random() < 0.8 else 0.0 for _ in range(80)]
        c = bootstrap_ci(sample, B=40, rng=random.Random(t))
        if c["ci_lo"] <= 0.8 <= c["ci_hi"]:
            hits += 1
    cover = hits / trials
    assert cover >= 0.7, cover
    db = tmp / "empty.db"
    run(out_path=out, db_path=db, B=10)
    assert out.exists()
    json.loads(out.read_text())
    print(f"[skill-calibrated-posterior] --self-test PASS cover={cover:.2f}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--B", type=int, default=B_DEFAULT)
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print("[skill-calibrated-posterior] --self-test FAIL:", exc)
            return 1
    report = run(B=args.B)
    print(json.dumps({"status": report.get("status"), "n_skills": report.get("n_skills")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
