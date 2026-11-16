#!/usr/bin/env python3
"""Allocate eval budget by per-skill disagreement and coverage saturation (UCB)."""
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


OUT_PATH = CACHE / "skill-ucb-state.json"
CALIB = CACHE / "calibration-log.jsonl"
C_UCB = 1.0


def load_skill_obs():
    obs = defaultdict(list)
    db = LIFECYCLE_DB
    if db.exists():
        conn = _connect(db)
        try:
            tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "anytime_eval_log" in tabs:
                rows = conn.execute(
                    "SELECT skill_id, eval_score FROM anytime_eval_log "
                    "WHERE skill_id IS NOT NULL"
                ).fetchall()
                for skill, score in rows:
                    s = str(skill or "").strip()
                    if not s or s.startswith("audit"):
                        continue
                    try:
                        q = float(score)
                    except (TypeError, ValueError):
                        continue
                    if math.isfinite(q):
                        obs[s].append(_clip01(q))
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    for rec in _iter_jsonl(CALIB, max_rows=50000):
        if rec.get("scope") == UE_SENTINEL:
            continue
        skill = rec.get("scope") or rec.get("tool_name")
        if not skill:
            continue
        s = str(skill).strip()
        if not s:
            continue
        conf = rec.get("predicted_confidence")
        try:
            q = float(conf)
        except (TypeError, ValueError):
            continue
        if math.isfinite(q):
            obs[s].append(_clip01(q))
    return dict(obs)


def variance(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    return sum((x - m) ** 2 for x in xs) / (n - 1)


def allocate(obs: dict, c=C_UCB) -> dict:
    if not obs:
        return {"status": "insufficient_data", "n": 0, "ts": _now(), "skills": {}}
    t = sum(len(v) for v in obs.values())
    logt = math.log(max(t, 2))
    skills = {}
    for name, xs in obs.items():
        n = len(xs)
        mu = sum(xs) / n if n else 0.0
        disagr = variance(xs)
        cover = n / t if t else 0.0
        bonus = c * math.sqrt(logt / n) if n else float("inf")
        ucb = mu + bonus if math.isfinite(bonus) else 1.0
        # disagreement-weighted allocation score
        score = disagr + (0.15 * bonus if math.isfinite(bonus) else 1.0)
        skills[name] = {
            "n": n,
            "mean": mu,
            "disagreement": disagr,
            "coverage": cover,
            "ucb": ucb if math.isfinite(ucb) else 1.0,
            "alloc_score": score if math.isfinite(score) else 1.0,
        }
    ranked = sorted(skills, key=lambda k: skills[k]["alloc_score"], reverse=True)
    under = [k for k, v in skills.items() if v["coverage"] < 0.02]
    high_d = [k for k, v in skills.items() if v["disagreement"] > 0.01]
    return {
        "ts": _now(),
        "status": "ok",
        "n_obs": t,
        "n_skills": len(skills),
        "c_ucb": c,
        "top_alloc": ranked[:15],
        "undersampled": under[:20],
        "high_disagreement": high_d[:20],
        "skills": {k: skills[k] for k in ranked[:80]},
    }


def run(out_path: Path | None = None) -> dict:
    out_path = out_path or OUT_PATH
    result = allocate(load_skill_obs())
    if result.get("status") != "insufficient_data":
        _atomic_write(out_path, result)
    return result


def _self_test() -> int:
    obs = {
        "rare": [0.4, 0.9],
        "stable": [0.7] * 40,
        "noisy": [0.1, 0.9, 0.2, 0.8, 0.3, 0.7],
    }
    r = allocate(obs)
    assert r["status"] == "ok"
    assert "noisy" in r["high_disagreement"]
    assert r["skills"]["stable"]["disagreement"] < r["skills"]["noisy"]["disagreement"]
    empty = allocate({})
    assert empty["status"] == "insufficient_data"
    tmp = Path(tempfile.mkdtemp()) / ("skill-ucb-state_" + uuid.uuid4().hex + ".json")
    _atomic_write(tmp, r)
    json.loads(tmp.read_text())
    tmp.unlink(missing_ok=True)
    print("[skill-disagreement-allocation] --self-test PASS top={}".format(r["top_alloc"][:3]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Skill disagreement UCB allocator")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[skill-disagreement-allocation] --self-test FAIL: {exc}")
            return 1
    try:
        print(json.dumps(run()))
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
