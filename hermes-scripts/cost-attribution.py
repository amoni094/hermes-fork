#!/usr/bin/env python3
"""Exact-ish attribution of memory-injection cost vs workflow depth.

Fits linear model cost = a + b * depth from anytime_eval_log token_estimate
and delegation_audit.subtask_count. Writes workflow-cost-ledger.json.
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
from collections import defaultdict
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
OUT_PATH = CACHE / "workflow-cost-ledger.json"
LIFECYCLE_DB = _hermes_base / "memory-facts" / "lifecycle.db"
UNIT_PRICE = 3.0e-6  # relative $/token unit; not a billed price
MAE_REJECT = 0.15
MAX_DEPTH = 6
WINDOW_CAP_DEFAULT = 32


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


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def fit_ols(xs: list, ys: list) -> dict:
    n = min(len(xs), len(ys))
    if n < 2:
        return {"status": "insufficient_data", "n": n, "a": None, "b": None}
    sx = sy = sxx = sxy = 0.0
    for i in range(n):
        x = float(xs[i])
        y = float(ys[i])
        sx += x
        sy += y
        sxx += x * x
        sxy += x * y
    det = n * sxx - sx * sx
    if abs(det) < 1e-12:
        mean_y = sy / n
        return {"status": "ok", "n": n, "a": mean_y, "b": 0.0, "degenerate": True}
    b = (n * sxy - sx * sy) / det
    a = (sy - b * sx) / n
    return {"status": "ok", "n": n, "a": float(a), "b": float(b), "degenerate": False}


def predict(a: float, b: float, depth: float) -> float:
    return float(a) + float(b) * float(depth)


def mae_rel(ys: list, yhat: list) -> float | None:
    if not ys:
        return None
    acc = 0.0
    denom = 0.0
    n = 0
    for y, yh in zip(ys, yhat):
        acc += abs(float(y) - float(yh))
        denom += abs(float(y))
        n += 1
    if n == 0:
        return None
    if denom <= 1e-12:
        return 0.0 if acc == 0 else 1.0
    return acc / denom


def parse_token(tier) -> float | None:
    extra = {}
    if isinstance(tier, str) and tier.startswith("{"):
        try:
            extra = json.loads(tier)
        except json.JSONDecodeError:
            return None
    elif isinstance(tier, dict):
        extra = tier
    else:
        return None
    v = extra.get("token_estimate")
    try:
        if v is None:
            return None
        fv = float(v)
        if fv < 0:
            return None
        return fv
    except (TypeError, ValueError):
        return None


def load_eval_points(db_path: Path) -> list:
    """(depth, tokens, session_id). Depth = 1-based order within session, capped."""
    if not db_path.exists():
        return []
    conn = None
    try:
        conn = _connect(db_path)
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "anytime_eval_log" not in tabs:
            return []
        rows = conn.execute(
            "SELECT session_id, ts, quality_tier FROM anytime_eval_log "
            "ORDER BY session_id, ts"
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()
    buckets = defaultdict(list)
    for sid, ts, tier in rows:
        if not sid:
            continue
        tok = parse_token(tier)
        if tok is None:
            continue
        buckets[str(sid)].append((str(ts or ""), tok))
    pts = []
    for sid, items in buckets.items():
        items.sort(key=lambda r: r[0])
        cum = 0.0
        for i, (_ts, tok) in enumerate(items, start=1):
            depth = min(i, MAX_DEPTH)
            cum += tok
            pts.append((depth, cum, sid))
    return pts


def load_delegation_points(db_path: Path) -> list:
    if not db_path.exists():
        return []
    conn = None
    try:
        conn = _connect(db_path)
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "delegation_audit" not in tabs:
            return []
        rows = conn.execute(
            "SELECT episode_id, subtask_count, success_rate FROM delegation_audit "
            "WHERE subtask_count IS NOT NULL"
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()
    pts = []
    for eid, sc, sr in rows:
        try:
            depth = min(MAX_DEPTH, max(1, int(sc)))
        except (TypeError, ValueError):
            continue
        try:
            # proxy tokens: subtasks * unit; do not invent success
            tokens = float(depth) * 200.0
            if sr is not None:
                tokens = tokens * (0.5 + 0.5 * float(sr))
        except (TypeError, ValueError):
            tokens = float(depth) * 200.0
        pts.append((depth, tokens, str(eid or "")))
    return pts


def stratify(pts: list) -> dict:
    buckets = {d: [] for d in range(1, MAX_DEPTH + 1)}
    for depth, tokens, _sid in pts:
        d = int(max(1, min(MAX_DEPTH, depth)))
        buckets[d].append(float(tokens))
    out = {}
    for d, ys in buckets.items():
        if not ys:
            continue
        out[str(d)] = {
            "n": len(ys),
            "mean_tokens": sum(ys) / len(ys),
            "mean_cost_units": (sum(ys) / len(ys)) * UNIT_PRICE,
        }
    return out


def cap_recommendation(b: float, window: int = WINDOW_CAP_DEFAULT) -> dict:
    """Cap retrieval window when marginal depth cost dominates."""
    if b is None:
        return {"retrieval_window_size": window, "max_depth": MAX_DEPTH, "reason": "unfitted"}
    # if each extra depth costs > 10% of a 2k-token baseline, shrink window
    baseline = 2000.0
    if b > 0.10 * baseline:
        return {
            "retrieval_window_size": max(8, window // 2),
            "max_depth": max(2, MAX_DEPTH - 2),
            "reason": "high_marginal_depth_cost",
            "b": b,
        }
    return {
        "retrieval_window_size": window,
        "max_depth": MAX_DEPTH,
        "reason": "marginal_ok",
        "b": b,
    }


def run(db_path: Path, out_path: Path) -> dict:
    pts = load_eval_points(db_path)
    src = "anytime_eval_log"
    if len(pts) < 8:
        extra = load_delegation_points(db_path)
        pts = pts + extra
        src = "eval+delegation" if pts else src
    if len(pts) < 2:
        return {"status": "insufficient_data", "n": len(pts), "ts": _now()}
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    fit = fit_ols(xs, ys)
    if fit.get("status") != "ok":
        return {"status": "insufficient_data", "n": len(pts), "ts": _now()}
    yhat = [predict(fit["a"], fit["b"], x) for x in xs]
    rel = mae_rel(ys, yhat)
    vectors = []
    for (depth, tokens, sid), yh in list(zip(pts, yhat))[-80:]:
        mem_cost = max(0.0, float(yh)) * UNIT_PRICE
        vectors.append(
            {
                "run_id": sid,
                "depth": depth,
                "tokens": tokens,
                "predicted_tokens": yh,
                "memory_cost_units": mem_cost,
            }
        )
    rec = cap_recommendation(fit["b"])
    payload = {
        "ts": _now(),
        "status": "ok",
        "source": src,
        "n": len(pts),
        "model": {"a": fit["a"], "b": fit["b"], "form": "a + b*depth"},
        "mae_rel": rel,
        "unit_price": UNIT_PRICE,
        "by_depth": stratify(pts),
        "recommendation": rec,
        "controllable_parameters": ["retrieval_window_size", "max_depth"],
        "kill_test": {
            "mae_rel": rel,
            "reject_if_gt": MAE_REJECT,
            "reject_model": bool(rel is not None and rel > MAE_REJECT),
        },
        "vectors": vectors,
    }
    _atomic_write(out_path, payload)
    payload["written"] = str(out_path)
    return payload


def _self_test() -> int:
    xs = [1, 2, 3, 4, 5, 6]
    ys = [10 + 5 * x for x in xs]
    fit = fit_ols(xs, ys)
    assert fit["status"] == "ok"
    assert abs(fit["a"] - 10) < 1e-6, fit
    assert abs(fit["b"] - 5) < 1e-6, fit
    yhat = [predict(fit["a"], fit["b"], x) for x in xs]
    assert mae_rel(ys, yhat) < 1e-9
    assert fit_ols([1], [1])["status"] == "insufficient_data"

    td = Path(tempfile.mkdtemp(prefix="cat-"))
    try:
        db = td / "lc.db"
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE anytime_eval_log (id INTEGER PRIMARY KEY, ts TEXT, session_id TEXT, "
            "skill_id TEXT, eval_score REAL, quality_tier TEXT)"
        )
        for s in range(6):
            for t in range(1, 5):
                conn.execute(
                    "INSERT INTO anytime_eval_log (ts, session_id, skill_id, eval_score, quality_tier) "
                    "VALUES (?,?,?,?,?)",
                    (
                        "t%02d" % t,
                        "S%d" % s,
                        "tool",
                        1.0,
                        json.dumps({"token_estimate": 100 * t, "success": True}),
                    ),
                )
        conn.commit()
        conn.close()
        out = td / ("workflow-cost-ledger_test_" + uuid.uuid4().hex + ".json")
        live = run(db, out)
        assert live.get("status") == "ok", live
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["model"]["b"] is not None
        assert "retrieval_window_size" in payload["recommendation"]
        missing = run(td / "nope.db", td / "nope.json")
        assert missing.get("status") == "insufficient_data"
        assert not (td / "nope.json").exists()
    finally:
        import shutil

        shutil.rmtree(td, ignore_errors=True)
    print("[cost-attribution] --self-test PASS")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Memory-injection cost attribution")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--db", default=str(LIFECYCLE_DB))
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f"[cost-attribution] --self-test FAIL: {exc}")
            sys.exit(1)
    try:
        result = run(Path(args.db), Path(args.out))
        slim = {k: result[k] for k in result if k != "vectors"}
        print(json.dumps(slim, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
