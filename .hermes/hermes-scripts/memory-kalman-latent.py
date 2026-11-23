#!/usr/bin/env python3
"""memory-kalman-latent.py — 1D Kalman filter for scalar numeric memory facts.

Murphy / Jurafsky: scalar Kalman (predict + update) for calibration scores,
routing weights, retention z-scores.

working-memory.py cmd_record_latency is an EMA, not a Kalman filter with
monotonic posterior variance. This script is the actual 1D Kalman.

Hard core: after an observation (Q not applied during update),
  P' = P R / (P + R)  < P    (posterior variance decreases)

Stdlib only (no numpy).

Usage:
  python3 memory-kalman-latent.py --update --key routing_weight --z 0.42
  python3 memory-kalman-latent.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


def profile_root() -> Path:
    hp = os.environ.get("HERMES_PROFILE", "").strip()
    if hp:
        cand = Path.home() / ".hermes" / "profiles" / hp
        if cand.is_dir():
            return cand
    hh = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    if hh.name != ".hermes" and hh.parent.name == "profiles":
        return hh
    return hermes_home()


def cache_dir() -> Path:
    d = profile_root() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return cache_dir() / "memory-kalman.db"


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS kalman_scalar (
            key TEXT PRIMARY KEY,
            x REAL NOT NULL,
            P REAL NOT NULL,
            Q REAL NOT NULL,
            R REAL NOT NULL,
            n INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    return conn


def predict(x: float, P: float, Q: float) -> tuple[float, float]:
    return x, P + Q


def update(x: float, P: float, z: float, R: float) -> tuple[float, float, float]:
    """Return (x_post, P_post, K). P_post < P when P>0, R>0."""
    R = max(R, 1e-3)  # ADV-008: floor R prevents near-degenerate K≈1 (1e-3 = reasonable min noise)
    P = max(P, 0.0)   # ensure non-negative variance
    S = P + R
    if S <= 0:
        return x, P, 0.0
    K = P / S
    x_post = x + K * (z - x)
    P_post = (1.0 - K) * P
    return x_post, P_post, K


def step(key: str, z: float, Q: float = 1e-4, R: float = 0.05,
         path: Path | None = None) -> dict:
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT x, P, Q, R, n FROM kalman_scalar WHERE key=?", (key,)
        ).fetchone()
        if row:
            x, P, Qs, Rs, n = row
            Q, R = float(Qs), float(Rs)
        else:
            x, P, n = z, 1.0, 0
        x_pred, P_pred = predict(x, P, Q)
        x_post, P_post, K = update(x_pred, P_pred, z, R)
        ts = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO kalman_scalar(key, x, P, Q, R, n, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
              x=excluded.x, P=excluded.P, n=excluded.n, updated_at=excluded.updated_at
            """,
            (key, x_post, P_post, Q, R, n + 1, ts),
        )
        conn.commit()
        return {
            "key": key, "x": x_post, "P": P_post, "K": K, "n": n + 1,
            "P_pred": P_pred, "z": z,
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def self_test() -> int:
    x, P = 0.0, 1.0
    R = 0.2
    prev_P = P
    for z in (0.5, 0.4, 0.45, 0.42):
        # update without extra Q to isolate monotonicity of posterior
        x, P, K = update(x, P, z, R)
        assert P < prev_P, (P, prev_P)
        assert P > 0
        prev_P = P
    # Closed form P_n = 1 / (1/P0 + n/R) when Q=0
    P0 = 1.0
    n = 4
    expected = 1.0 / (1.0 / P0 + n / R)
    assert abs(P - expected) < 1e-12, (P, expected)
    import tempfile
    td = Path(tempfile.mkdtemp()) / "k.db"
    r1 = step("w", 0.2, Q=0.0, R=0.1, path=td)
    r2 = step("w", 0.3, Q=0.0, R=0.1, path=td)
    assert r2["P"] < r1["P"]
    print("PASS memory-kalman-latent self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--key", default="default")
    ap.add_argument("--z", type=float, default=None)
    ap.add_argument("--Q", type=float, default=1e-4)
    ap.add_argument("--R", type=float, default=0.05)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        if args.z is None:
            print(json.dumps({"ok": False, "error": "need --z"}))
            return 0
        R_safe = max(args.R, 1e-6)  # ADV-008: refuse R<=0
        Q_safe = max(args.Q, 0.0)
        print(json.dumps(step(args.key, args.z, Q=Q_safe, R=R_safe), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
