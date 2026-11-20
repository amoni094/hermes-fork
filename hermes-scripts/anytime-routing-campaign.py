#!/usr/bin/env python3
"""N-arm routing campaign: frozen reference arm + signed primal integral.

Reads anytime_eval_runs from lifecycle.db (real rows only). Reference arm is
the lowest weighted SPI; relative SPI is reported against that freeze.
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

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
if os.environ.get("HERMES_ROOT"):
    _hermes_root = Path(os.environ["HERMES_ROOT"])
else:
    _hermes_root = (
        (_hermes_base / "profiles" / _hermes_profile)
        if _hermes_profile and "profiles" not in str(_hermes_base)
        else _hermes_base
    )
CACHE = _hermes_root / "cache"
OUT_PATH = CACHE / "anytime-routing-results.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(path))
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)


def _lifecycle_db() -> Path:
    env = os.environ.get("LIFECYCLE_DB", "").strip()
    if env:
        return Path(env)
    return _hermes_base / "memory-facts" / "lifecycle.db"


def _load_rows(db: Path):
    if not db.exists():
        return []
    conn = sqlite3.connect(str(db))
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "anytime_eval_runs" not in tables:
            return []
        return conn.execute(
            "SELECT arm_id, mean_score, spi_score, n_queries FROM anytime_eval_runs"
        ).fetchall()
    finally:
        conn.close()


def _weighted_spi(rows) -> float:
    num = 0.0
    den = 0.0
    for _arm, _mean, spi, nq in rows:
        nqi = int(nq or 0)
        spif = float(spi or 0.0)
        num += spif * nqi
        den += nqi
    if den <= 0:
        spis = [float(r[2] or 0.0) for r in rows]
        return (sum(spis) / len(spis)) if spis else 0.0
    return num / den


def campaign(db: Path | None = None, out_path: Path | None = None) -> dict:
    db = db or _lifecycle_db()
    out_path = out_path or OUT_PATH
    rows = _load_rows(db)
    n = len(rows)
    ts = _now()
    if n < 5:
        return {"status": "insufficient_data", "n": n, "ts": ts}

    by_arm = defaultdict(list)
    for arm_id, mean_score, spi_score, n_queries in rows:
        if arm_id is None:
            continue
        by_arm[str(arm_id)].append((arm_id, mean_score, spi_score, n_queries))

    if not by_arm:
        return {"status": "insufficient_data", "n": n, "ts": ts}

    stats = {}
    for arm_id, arows in by_arm.items():
        means = [float(r[1]) for r in arows if r[1] is not None]
        stats[arm_id] = {
            "mean_score": (sum(means) / len(means)) if means else 0.0,
            "weighted_spi": _weighted_spi(arows),
            "n_queries": sum(int(r[3] or 0) for r in arows),
        }

    reference_arm_id = min(stats, key=lambda a: (stats[a]["weighted_spi"], a))
    ref_spi = stats[reference_arm_id]["weighted_spi"]
    relative_spi = {
        arm_id: float(stats[arm_id]["weighted_spi"] - ref_spi) for arm_id in stats
    }
    non_ref = [a for a in relative_spi if a != reference_arm_id]
    if not non_ref:
        best_arm_id = reference_arm_id
    else:
        best_arm_id = max(non_ref, key=lambda a: (relative_spi[a], a))

    n_total_queries = sum(int(r[3] or 0) for r in rows)
    result = {
        "ts": ts,
        "n_arms": len(stats),
        "n_total_queries": n_total_queries,
        "reference_arm_id": reference_arm_id,
        "best_arm_id": best_arm_id,
        "relative_spi_scores": relative_spi,
        "n_rows_read": n,
        "status": "ok",
    }
    _atomic_write(out_path, result)
    return result


def _self_test() -> int:
    td = Path(tempfile.mkdtemp(prefix="anytime-routing-"))
    db = td / (f"eval-{uuid.uuid4().hex}.db")
    out = td / (f"anytime-routing-results-{uuid.uuid4().hex}.json")
    conn = sqlite3.connect(str(db))
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        conn.execute(
            """CREATE TABLE anytime_eval_runs (
              id INTEGER PRIMARY KEY, ts TEXT, arm_id TEXT,
              mean_score REAL, spi_score REAL, n_queries INTEGER,
              reference_frozen_at INTEGER)"""
        )
        now = _now()
        for _ in range(3):
            conn.execute(
                "INSERT INTO anytime_eval_runs(ts,arm_id,mean_score,spi_score,n_queries,reference_frozen_at) VALUES (?,?,?,?,?,?)",
                (now, "A", 0.9, 2.0, 10, 0),
            )
            conn.execute(
                "INSERT INTO anytime_eval_runs(ts,arm_id,mean_score,spi_score,n_queries,reference_frozen_at) VALUES (?,?,?,?,?,?)",
                (now, "B", 0.5, 5.0, 10, 0),
            )
        conn.commit()
    finally:
        conn.close()
    r = campaign(db=db, out_path=out)
    assert r["status"] == "ok", r
    assert r["best_arm_id"] == "B", r
    assert r["reference_arm_id"] == "A", r
    assert r["n_rows_read"] == 6, r
    assert out.exists(), out
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["best_arm_id"] == "B", data
    try:
        db.unlink(missing_ok=True)
        out.unlink(missing_ok=True)
        out.with_name(out.name + ".lock").unlink(missing_ok=True)
        td.rmdir()
    except OSError:
        pass
    print("[anytime-routing-campaign] --self-test PASS best=B")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f"[anytime-routing-campaign] --self-test FAIL: {exc}")
            sys.exit(1)
    try:
        r = campaign()
        print(json.dumps(r))
    except Exception as e:
        print(json.dumps({"status": "error", "reason": str(e)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
