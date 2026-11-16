#!/usr/bin/env python3
"""Rank tool/skill encoding variants by downstream latency and quality."""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import sqlite3
import sys
import tempfile
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_raw_home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_base = _raw_home
if _hermes_base.name != ".hermes" and _hermes_base.parent.name == "profiles":
    _hermes_base = _hermes_base.parent.parent
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
if not _hermes_profile and _raw_home.parent.name == "profiles":
    _hermes_profile = _raw_home.name
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
CACHE = _hermes_root / "cache"
LIFECYCLE_DB = _hermes_base / "memory-facts" / "lifecycle.db"
UE_SENTINEL = "ue_blackbox"
EPS = 1e-12


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    tmp = path.with_name(path.name + ".tmp")
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _connect(db: Path):
    conn = sqlite3.connect(str(db), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _iter_jsonl(path: Path, max_rows: int | None = None):
    if not path.exists():
        return
    n = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                yield rec
                n += 1
                if max_rows is not None and n >= max_rows:
                    return
    except OSError:
        return


def _clip01(x: float) -> float:
    if not math.isfinite(x):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


OUT_PATH = CACHE / "encoding-scores.json"
LATENCY = CACHE / "skill-latency.jsonl"
CALIB = CACHE / "calibration-log.jsonl"


def _pctl(xs, p):
    if not xs:
        return 0.0
    ys = sorted(xs)
    k = min(len(ys) - 1, max(0, round((p / 100.0) * (len(ys) - 1))))
    return float(ys[k])


def collect_latencies():
    by = defaultdict(list)
    for rec in _iter_jsonl(LATENCY):
        name = rec.get("tool_name") or rec.get("skill") or rec.get("encoding")
        if not name:
            continue
        name = str(name).strip()
        if not name or name.startswith("audit"):
            continue
        ms = rec.get("elapsed_ms")
        try:
            v = float(ms)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(v) or v < 0:
            continue
        by[name].append(v)
    return dict(by)


def collect_quality():
    by = defaultdict(list)
    db = LIFECYCLE_DB
    if not db.exists():
        return {}
    conn = _connect(db)
    try:
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "anytime_eval_log" not in tabs:
            return {}
        rows = conn.execute(
            "SELECT skill_id, eval_score FROM anytime_eval_log "
            "WHERE skill_id IS NOT NULL AND skill_id != ''"
        ).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        conn.close()
    for skill, score in rows:
        s = str(skill).strip()
        if not s or s.startswith("audit"):
            continue
        try:
            q = float(score)
        except (TypeError, ValueError):
            continue
        if math.isfinite(q):
            by[s].append(q)
    return dict(by)


def rank_encodings(lat_by, qual_by) -> dict:
    names = set(lat_by) | set(qual_by)
    if not names:
        return {"status": "insufficient_data", "n": 0, "ts": _now(), "encodings": []}
    rows = []
    times = []
    for name in names:
        lats = lat_by.get(name) or []
        quals = qual_by.get(name) or []
        mean_ms = (sum(lats) / len(lats)) if lats else None
        p95 = _pctl(lats, 95) if lats else None
        mean_q = (sum(quals) / len(quals)) if quals else None
        # rank key: lower latency better; missing latency sorts last
        rows.append({
            "encoding": name,
            "n_latency": len(lats),
            "mean_ms": mean_ms,
            "p95_ms": p95,
            "n_quality": len(quals),
            "mean_quality": mean_q,
        })
        if mean_ms is not None:
            times.append(mean_ms)
    timed = [r for r in rows if r["mean_ms"] is not None]
    timed.sort(key=lambda r: (r["mean_ms"], r["encoding"]))
    untimed = [r for r in rows if r["mean_ms"] is None]
    untimed.sort(key=lambda r: r["encoding"])
    ranked = timed + untimed
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    top = timed[0]["mean_ms"] if timed else None
    rand = (sum(times) / len(times)) if times else None
    improve = None
    if top is not None and rand and rand > 0:
        improve = (rand - top) / rand
    return {
        "ts": _now(),
        "status": "ok",
        "n": len(ranked),
        "top_encoding": ranked[0]["encoding"] if ranked else None,
        "top_mean_ms": top,
        "random_baseline_mean_ms": rand,
        "top_vs_random_improve": improve,
        "kill_test_pass": (improve is not None and improve >= 0.10),
        "encodings": ranked[:80],
    }


def run(out_path: Path | None = None) -> dict:
    out_path = out_path or OUT_PATH
    result = rank_encodings(collect_latencies(), collect_quality())
    if result.get("status") != "insufficient_data":
        _atomic_write(out_path, result)
    return result


def _self_test() -> int:
    lat = {"enc_a": [10.0, 12.0, 11.0], "enc_b": [50.0, 60.0, 55.0], "enc_c": [30.0]}
    qual = {"enc_a": [0.9, 0.8], "enc_b": [0.5]}
    r = rank_encodings(lat, qual)
    assert r["status"] == "ok"
    assert r["encodings"][0]["encoding"] == "enc_a"
    assert r["top_vs_random_improve"] >= 0.10
    empty = rank_encodings({}, {})
    assert empty["status"] == "insufficient_data"
    tmp = Path(tempfile.mkdtemp()) / ("encoding-scores_" + uuid.uuid4().hex + ".json")
    _atomic_write(tmp, r)
    assert json.loads(tmp.read_text())["n"] == 3
    tmp.unlink(missing_ok=True)
    print("[encoding-ranker] --self-test PASS top={} improve={:.3f}".format(r["top_encoding"], r["top_vs_random_improve"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Encoding variant ranker")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[encoding-ranker] --self-test FAIL: {exc}")
            return 1
    try:
        print(json.dumps(run()))
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
