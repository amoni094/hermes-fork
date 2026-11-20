#!/usr/bin/env python3
"""Kalman-filter request throttle for expensive tasks (Albireo-style).

Persists a 10-dim KF state per task_id in a dedicated cache SQLite DB
(not lifecycle.db). Invoke when predicted observation variance exceeds theta.
Stdlib only. Profile-aware. Default action is --run (cron-safe).
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sqlite3
import sys
import tempfile
import uuid
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
OUT_PATH = CACHE / "task-kalman-throttle.json"
STATE_DB = CACHE / "task-kf-state.db"
LIFECYCLE_DB = _hermes_base / "memory-facts" / "lifecycle.db"
DIM = 10
THETA = 0.12
DT = 1.0
Q_POS = 1e-4
Q_VEL = 1e-5
R_OBS = 0.05
NAIVE_EVERY = 1.0


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    tmp = path.with_name(path.name + ".tmp")
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _clip01(x: float) -> float:
    if x != x or x == float("inf") or x == float("-inf"):
        return 0.0
    return max(0.0, min(1.0, float(x)))


def connect_state(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS task_kf_state ("
        "task_id TEXT PRIMARY KEY,"
        "x_json TEXT NOT NULL,"
        "p_json TEXT NOT NULL,"
        "n INTEGER NOT NULL,"
        "last_invoke INTEGER NOT NULL,"
        "updated_at TEXT NOT NULL"
        ")"
    )
    return conn


def _new_state() -> tuple:
    x = [0.5, 0.0, 0.5, 0.0, 0.5, 0.0, 0.5, 0.0, 0.0, 0.0]
    # velocity priors stay tight: unobserved vel P=1 would re-inflate pos P every predict
    p = [1.0, 0.01] * 5
    return x, p


def _clamp_state(x: list, p: list) -> tuple:
    if len(x) != DIM or len(p) != DIM:
        return _new_state()
    pp = list(p)
    for k in range(1, DIM, 2):
        pp[k] = min(max(float(pp[k]), 0.0), 0.05)
    for k in range(0, DIM, 2):
        pp[k] = min(max(float(pp[k]), 0.0), 10.0)
    return list(x), pp


def predict(x: list, p: list, dt: float = DT) -> tuple:
    """Block-diagonal constant-velocity: 5 (pos,vel) pairs. Diagonal P only."""
    xp = list(x)
    pp = list(p)
    for k in range(0, DIM, 2):
        pos, vel = x[k], x[k + 1]
        xp[k] = pos + vel * dt
        xp[k + 1] = vel
        # P' = F P F^T + Q with diagonal P approximation
        ppos, pvel = p[k], p[k + 1]
        pp[k] = ppos + (dt * dt) * pvel + Q_POS
        pp[k + 1] = pvel + Q_VEL
    return xp, pp


def update_obs(x: list, p: list, z_map: dict, r: float = R_OBS) -> tuple:
    """z_map: index -> observation. Scalar Kalman on those indices. P decreases."""
    r = max(float(r), 1e-3)
    xp = list(x)
    pp = list(p)
    for idx, z in z_map.items():
        i = int(idx)
        if i < 0 or i >= DIM:
            continue
        try:
            zv = float(z)
        except (TypeError, ValueError):
            continue
        Pi = max(pp[i], 0.0)
        s = Pi + r
        if s <= 0:
            continue
        k = Pi / s
        xp[i] = xp[i] + k * (zv - xp[i])
        pp[i] = (1.0 - k) * Pi
        if i % 2 == 0 and i + 1 < DIM:
            # posterior variance of a measured position must drop
            pass
    return xp, pp


def decision_variance(p: list) -> float:
    # success pos (0) + quality pos (6)
    return float(max(p[0], 0.0) + max(p[6], 0.0))


def should_invoke(p: list, theta: float = THETA) -> bool:
    return decision_variance(p) > float(theta)


def obs_from_row(score, latency_ms, outcome) -> dict:
    z = {}
    try:
        if score is not None:
            z[0] = _clip01(float(score))
            z[6] = _clip01(float(score))
    except (TypeError, ValueError):
        pass
    try:
        if latency_ms is not None:
            z[2] = _clip01(float(latency_ms) / 5000.0)
    except (TypeError, ValueError):
        pass
    if outcome is not None:
        ok = 1.0 if str(outcome).lower() in ("ok", "success", "1", "true") else 0.0
        z[0] = ok
        z[4] = 1.0  # invoked
    return z


def load_tool_rows(db_path: Path, limit: int = 8000) -> list:
    if not db_path.exists():
        return []
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "tool_review_log" not in tabs:
            return []
        return conn.execute(
            "SELECT tool_name, latency_ms, outcome, score FROM tool_review_log "
            "WHERE tool_name IS NOT NULL ORDER BY id ASC LIMIT ?",
            (limit,),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()


def step_task(conn: sqlite3.Connection, task_id: str, z_map: dict, invoke: bool) -> dict:
    row = conn.execute(
        "SELECT x_json, p_json, n, last_invoke FROM task_kf_state WHERE task_id=?",
        (task_id,),
    ).fetchone()
    if row:
        try:
            x = list(json.loads(row[0]))
            p = list(json.loads(row[1]))
            x, p = _clamp_state(x, p)
        except (json.JSONDecodeError, TypeError):
            x, p = _new_state()
        n = int(row[2] or 0)
        last_inv = int(row[3] or 0)
        if len(x) != DIM or len(p) != DIM:
            x, p = _new_state()
    else:
        x, p = _new_state()
        n, last_inv = 0, 0
    x, p = predict(x, p)
    x, p = update_obs(x, p, z_map)
    inv = bool(invoke)
    n += 1
    last_inv = last_inv + 1 if inv else last_inv
    ts = _now()
    conn.execute(
        "INSERT INTO task_kf_state(task_id, x_json, p_json, n, last_invoke, updated_at) "
        "VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(task_id) DO UPDATE SET "
        "x_json=excluded.x_json, p_json=excluded.p_json, n=excluded.n, "
        "last_invoke=excluded.last_invoke, updated_at=excluded.updated_at",
        (task_id, json.dumps(x), json.dumps(p), n, last_inv, ts),
    )
    return {
        "task_id": task_id,
        "x": x,
        "p": p,
        "n": n,
        "invoke": inv,
        "variance": decision_variance(p),
        "last_invoke": last_inv,
    }


def run(life_db: Path, state_db: Path, out_path: Path, theta: float = THETA) -> dict:
    rows = load_tool_rows(life_db)
    if not rows:
        return {"status": "insufficient_data", "n": 0, "ts": _now()}
    conn = connect_state(state_db)
    decisions = []
    invoke_n = 0
    naive_n = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        for tool, lat, outcome, score in rows:
            naive_n += 1
            tid = str(tool)
            z = obs_from_row(score, lat, outcome)
            # predict-only variance for the decision, using current stored P
            row = conn.execute(
                "SELECT p_json FROM task_kf_state WHERE task_id=?", (tid,)
            ).fetchone()
            if row:
                try:
                    p_now = list(json.loads(row[0]))
                    p_now = _clamp_state([0.0] * DIM, p_now)[1]
                except (json.JSONDecodeError, TypeError):
                    p_now = _new_state()[1]
            else:
                p_now = _new_state()[1]
            _, p_pred = predict([0.0] * DIM, p_now)
            inv = should_invoke(p_pred, theta)
            if not inv:
                z[8] = 1.0  # skip_prob observation
            else:
                z[8] = 0.0
                invoke_n += 1
            st = step_task(conn, tid, z, inv)
            decisions.append(
                {
                    "task_id": tid,
                    "invoke": st["invoke"],
                    "variance": st["variance"],
                    "n": st["n"],
                }
            )
        conn.commit()
    finally:
        conn.close()
    ratio = (invoke_n / naive_n) if naive_n else 1.0
    # collapse per-task last decision
    last = {}
    for d in decisions:
        last[d["task_id"]] = d
    payload = {
        "ts": _now(),
        "status": "ok",
        "theta": theta,
        "n_events": naive_n,
        "n_tasks": len(last),
        "invoke_count": invoke_n,
        "naive_count": naive_n,
        "invoke_ratio": ratio,
        "kill_test": {
            "invoke_ratio": ratio,
            "reject_if_ratio_gt": 0.90,
            "reject_throttle": bool(ratio > 0.90),
        },
        "tasks": list(last.values())[:80],
    }
    _atomic_write(out_path, payload)
    payload["written"] = str(out_path)
    return payload


def _self_test() -> int:
    x, p = _new_state()
    xp, pp = predict(x, p)
    assert pp[0] >= p[0]
    _x2, p2 = update_obs(xp, pp, {0: 0.9, 6: 0.9})
    assert p2[0] < pp[0], (p2[0], pp[0])
    # high variance → invoke
    assert should_invoke([1.0] * DIM, 0.12) is True
    # low variance → skip
    assert should_invoke([0.01] * DIM, 0.12) is False

    td = Path(tempfile.mkdtemp(prefix="tkf-"))
    try:
        db = td / "lc.db"
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE tool_review_log (id INTEGER PRIMARY KEY, ts TEXT, session_id TEXT, "
            "tool_name TEXT, latency_ms REAL, outcome TEXT, score REAL, notes TEXT)"
        )
        for i in range(20):
            conn.execute(
                "INSERT INTO tool_review_log (ts, session_id, tool_name, latency_ms, outcome, score) "
                "VALUES (?,?,?,?,?,?)",
                (_now(), "s", "delegate_task", 100.0, "ok", 0.9),
            )
        conn.commit()
        conn.close()
        state = td / "kf.db"
        out = td / ("task-kalman-throttle_test_" + uuid.uuid4().hex + ".json")
        live = run(db, state, out, theta=0.12)
        assert live.get("status") == "ok", live
        assert out.exists()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["n_events"] == 20
        sconn = sqlite3.connect(str(state), timeout=30)
        ntab = sconn.execute(
            "SELECT COUNT(*) FROM task_kf_state"
        ).fetchone()[0]
        sconn.close()
        assert ntab >= 1
        missing = run(td / "nope.db", td / "kf2.db", td / "nope.json")
        assert missing.get("status") == "insufficient_data"
        assert not (td / "nope.json").exists()
    finally:
        import shutil

        shutil.rmtree(td, ignore_errors=True)
    print("[task-kalman-throttle] --self-test PASS")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Kalman task throttle")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--db", default=str(LIFECYCLE_DB))
    ap.add_argument("--state-db", default=str(STATE_DB))
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--theta", type=float, default=THETA)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f"[task-kalman-throttle] --self-test FAIL: {exc}")
            sys.exit(1)
    try:
        result = run(Path(args.db), Path(args.state_db), Path(args.out), theta=float(args.theta))
        slim = {k: result[k] for k in result if k != "tasks"}
        print(json.dumps(slim, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
