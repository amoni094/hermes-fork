#!/usr/bin/env python3
"""Local stochastic consensus: majority-amplified skill routing confidence."""
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

OUT_PATH = CACHE / "routing-consensus.json"

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


def load_eval_rows(db_path: Path, limit=3000):
    if not db_path.exists():
        return []
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT skill_id, eval_score FROM anytime_eval_log "
            "WHERE skill_id IS NOT NULL ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    out = []
    for sid, score in rows:
        if not sid or sid == "ue_blackbox":
            continue
        try:
            v = float(score)
        except (TypeError, ValueError):
            continue
        if v != v:
            continue
        out.append((str(sid), max(0.0, min(1.0, v))))
    out.reverse()  # chronological
    return out


def majority_amplify(rows, window=40):
    if not rows:
        return {"status": "insufficient_data", "skills": {}, "margin": None}
    # rolling vote: in each window, the max-score skill gets +1 agreement
    agree = defaultdict(float)
    mass = defaultdict(float)
    counts = defaultdict(int)
    for i in range(0, len(rows), max(1, window // 4)):
        chunk = rows[i : i + window]
        if not chunk:
            continue
        local = defaultdict(list)
        for sid, sc in chunk:
            local[sid].append(sc)
            counts[sid] += 1
            mass[sid] += sc
        if not local:
            continue
        ranked = sorted(((sum(v) / len(v), k) for k, v in local.items()), reverse=True)
        winner = ranked[0][1]
        agree[winner] += 1.0
        if len(ranked) > 1:
            agree[ranked[1][1]] += 0.25
    scores = {}
    for sid, n in counts.items():
        mean = mass[sid] / n
        amp = 1.0 + math.log1p(agree.get(sid, 0.0))
        scores[sid] = {
            "n": n,
            "mean": mean,
            "agreement": agree.get(sid, 0.0),
            "amplified": mean * amp,
        }
    ranked = sorted(scores.items(), key=lambda kv: kv[1]["amplified"], reverse=True)
    margin = None
    if len(ranked) >= 2:
        margin = ranked[0][1]["amplified"] - ranked[1][1]["amplified"]
    elif len(ranked) == 1:
        margin = ranked[0][1]["amplified"]
    return {
        "status": "ok",
        "n_rows": len(rows),
        "n_skills": len(scores),
        "margin": margin,
        "top": ranked[0][0] if ranked else None,
        "skills": {k: v for k, v in ranked[:40]},
    }


def run(out_path=None, db_path=None):
    dest = out_path or OUT_PATH
    db = db_path or LIFECYCLE_DB
    try:
        rows = load_eval_rows(db)
        body = majority_amplify(rows)
        body["ts"] = _now()
        _atomic_write_json(dest, body)
        return body
    except Exception as exc:
        err = {"ts": _now(), "status": "error", "error": str(exc), "margin": None}
        try:
            _atomic_write_json(dest, err)
        except Exception:
            pass
        return err


def _self_test():
    tmp = Path(tempfile.mkdtemp(prefix="cons-"))
    out = tmp / ("routing-consensus_test_" + uuid.uuid4().hex + ".json")
    rows = [("alpha", 0.9)] * 30 + [("beta", 0.4)] * 30 + [("alpha", 0.85)] * 20
    r = majority_amplify(rows, window=10)
    assert r["status"] == "ok"
    assert r["top"] == "alpha"
    assert r["margin"] is not None and r["margin"] > 0
    empty = majority_amplify([])
    assert empty["status"] == "insufficient_data"
    run(out_path=out, db_path=tmp / "no.db")
    assert out.exists()
    json.loads(out.read_text())
    print("[consensus-routing-state] --self-test PASS top={} margin={:.3f}".format(r["top"], r["margin"]))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print("[consensus-routing-state] --self-test FAIL:", exc)
            return 1
    report = run()
    print(json.dumps({"status": report.get("status"), "n_skills": report.get("n_skills"), "margin": report.get("margin"), "top": report.get("top")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
