#!/usr/bin/env python3
"""Adaptive KT/xi* weighting of skill priors from session mismatch."""
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


OUT_PATH = CACHE / "skill-prior-weights.json"
PRIOR = CACHE / "skill-prior.json"
EVENTS = CACHE / "routing-events.jsonl"


def load_counts():
    counts = Counter()
    db = LIFECYCLE_DB
    if db.exists():
        conn = _connect(db)
        try:
            tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "anytime_eval_log" in tabs:
                rows = conn.execute(
                    "SELECT skill_id FROM anytime_eval_log WHERE skill_id IS NOT NULL"
                ).fetchall()
                for (skill,) in rows:
                    s = str(skill or "").strip()
                    if s and not s.startswith("audit"):
                        counts[s] += 1
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    for rec in _iter_jsonl(EVENTS):
        s = rec.get("top_skill") or rec.get("skill")
        if s:
            counts[str(s)] += 1
    return dict(counts)


def load_prior():
    if not PRIOR.exists():
        return {}
    try:
        data = json.loads(PRIOR.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    mp = data.get("marginal_prior") or data.get("prior") or {}
    if not isinstance(mp, dict):
        return {}
    out = {}
    for k, v in mp.items():
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv > 0:
            out[str(k)] = fv
    return out


def xi_star(emp: dict, prior: dict) -> dict:
    # mismatch D = TV distance; xi* = D/(1+D) KT-style mixture weight toward empirical
    keys = set(emp) | set(prior)
    if not keys:
        return {"status": "insufficient_data", "n": 0, "ts": _now()}
    se = sum(emp.values())
    sp = sum(prior.values())
    if se <= 0:
        return {"status": "insufficient_data", "n": 0, "ts": _now()}
    e = {k: emp.get(k, 0.0) / se for k in keys}
    if sp <= 0:
        p = {k: 1.0 / len(keys) for k in keys}
    else:
        p = {k: prior.get(k, 0.0) / sp for k in keys}
        # fill missing
        z = sum(p.values())
        if z <= 0:
            p = {k: 1.0 / len(keys) for k in keys}
        else:
            p = {k: v / z for k, v in p.items()}
    tv = 0.5 * sum(abs(e[k] - p[k]) for k in keys)
    xi = tv / (1.0 + tv)
    mixed = {}
    for k in keys:
        mixed[k] = (1.0 - xi) * p[k] + xi * e[k]
    # entropy change
    def H(d):
        h = 0.0
        for v in d.values():
            if v > 0:
                h -= v * math.log(v)
        return h
    ranked = sorted(mixed, key=mixed.get, reverse=True)
    return {
        "ts": _now(),
        "status": "ok",
        "n_emp": int(se),
        "n_skills": len(keys),
        "tv_mismatch": tv,
        "xi_star": xi,
        "entropy_prior": H(p),
        "entropy_emp": H(e),
        "entropy_mixed": H(mixed),
        "top": ranked[:20],
        "weights": {k: mixed[k] for k in ranked[:80]},
    }


def run(out_path: Path | None = None) -> dict:
    out_path = out_path or OUT_PATH
    result = xi_star(load_counts(), load_prior())
    if result.get("status") != "insufficient_data":
        _atomic_write(out_path, result)
    return result


def _self_test() -> int:
    emp = {"a": 80.0, "b": 10.0, "c": 10.0}
    prior = {"a": 0.33, "b": 0.33, "c": 0.34}
    r = xi_star(emp, prior)
    assert r["status"] == "ok"
    assert 0.0 < r["xi_star"] < 1.0
    assert r["weights"]["a"] > r["weights"]["b"]
    empty = xi_star({}, {})
    assert empty["status"] == "insufficient_data"
    tmp = Path(tempfile.mkdtemp()) / ("skill-prior-weights_" + uuid.uuid4().hex + ".json")
    _atomic_write(tmp, r)
    json.loads(tmp.read_text())
    tmp.unlink(missing_ok=True)
    print("[adaptive-skill-weighting] --self-test PASS xi={:.3f} tv={:.3f}".format(r["xi_star"], r["tv_mismatch"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Adaptive xi* skill prior weighting")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[adaptive-skill-weighting] --self-test FAIL: {exc}")
            return 1
    try:
        print(json.dumps(run()))
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
