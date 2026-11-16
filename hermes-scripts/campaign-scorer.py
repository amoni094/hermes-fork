#!/usr/bin/env python3
"""Anytime campaign scorer: signed primal integral, NSPI, ranking stability."""
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

OUT_PATH = CACHE / "campaign-metrics.json"


def _f(v, default=0.0) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def nspi(qualities, quality_range: float, T=None) -> float:
    qs = [_f(q) for q in qualities]
    n = len(qs)
    if n == 0:
        return 0.0
    Tval = float(n if T is None else T)
    qr = _f(quality_range)
    if Tval <= 0 or qr <= 0:
        return 0.0
    baseline = qs[0]
    acc = 0.0
    for t, q in enumerate(qs):
        acc += (q - baseline) * (1.0 - (t / Tval))
    val = acc / (Tval * qr)
    if not math.isfinite(val):
        return 0.0
    return max(-1.0, min(1.0, val))


def signed_primal(qualities, ref: float, dts=None) -> float:
    qs = [_f(q) for q in qualities]
    if not qs:
        return 0.0
    if dts is None:
        dts = [1.0] * len(qs)
    acc = 0.0
    for q, dt in zip(qs, dts):
        acc += (q - float(ref)) * _f(dt, 1.0)
    return acc


def kendall_tau(order_a, order_b) -> float:
    pos_a = {x: i for i, x in enumerate(order_a)}
    pos_b = {x: i for i, x in enumerate(order_b)}
    keys = [k for k in order_a if k in pos_b]
    n = len(keys)
    if n < 2:
        return 0.0
    conc = disc = 0
    for i in range(n):
        for j in range(i + 1, n):
            a = pos_a[keys[i]] - pos_a[keys[j]]
            b = pos_b[keys[i]] - pos_b[keys[j]]
            if a * b > 0:
                conc += 1
            elif a * b < 0:
                disc += 1
    denom = conc + disc
    return ((conc - disc) / denom) if denom else 0.0


def rank_keys(scores: dict, reverse=True):
    return sorted(scores, key=lambda k: (scores[k], k), reverse=reverse)


def max_position_shift(order_a, order_b) -> int:
    pos_b = {x: i for i, x in enumerate(order_b)}
    shift = 0
    for i, k in enumerate(order_a):
        if k in pos_b:
            shift = max(shift, abs(i - pos_b[k]))
    return shift


def load_arm_series(db: Path) -> dict:
    if not db.exists():
        return {}
    conn = _connect(db)
    try:
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "anytime_eval_runs" not in tabs:
            return {}
        rows = conn.execute(
            "SELECT arm_id, mean_score, spi_score, n_queries, ts FROM anytime_eval_runs ORDER BY id"
        ).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        conn.close()
    series = defaultdict(list)
    for arm, mean, spi, nq, ts in rows:
        if not arm:
            continue
        q = mean if mean is not None else spi
        if q is None:
            continue
        series[str(arm)].append(_f(q))
    return dict(series)


def score_campaign(series: dict) -> dict:
    nonempty = {k: v for k, v in series.items() if v}
    if len(nonempty) < 2:
        return {"status": "insufficient_data", "n_arms": len(nonempty), "ts": _now()}
    all_q = [q for vs in nonempty.values() for q in vs]
    qr = max(all_q) - min(all_q)
    arms = {}
    mean_scores = {}
    nspi_scores = {}
    for arm, qs in nonempty.items():
        mean_s = sum(qs) / len(qs)
        nspi_s = nspi(qs, qr if qr > 0 else 1.0)
        ref0 = qs[0]
        spi0 = signed_primal(qs, ref0)
        arms[arm] = {
            "mean_score": mean_s,
            "nspi": nspi_s,
            "spi_vs_start": spi0,
            "n_evals": len(qs),
            "last": qs[-1],
        }
        mean_scores[arm] = mean_s
        nspi_scores[arm] = nspi_s
    mean_rank = rank_keys(mean_scores)
    nspi_rank = rank_keys(nspi_scores)
    # freeze reference at first-half max, then re-freeze at final max
    half_ref = {}
    final_ref = {}
    for arm, qs in nonempty.items():
        mid = max(1, len(qs) // 2)
        half_ref[arm] = max(qs[:mid])
        final_ref[arm] = max(qs)
    r = max(half_ref.values())
    r_prime = max(final_ref.values())
    spi_r = {arm: signed_primal(qs, r) for arm, qs in nonempty.items()}
    spi_rp = {arm: signed_primal(qs, r_prime) for arm, qs in nonempty.items()}
    rank_r = rank_keys(spi_r)
    rank_rp = rank_keys(spi_rp)
    shift = max_position_shift(rank_r, rank_rp)
    tau = kendall_tau(rank_r, rank_rp)
    rejected = shift > 1
    return {
        "ts": _now(),
        "status": "ok",
        "n_arms": len(nonempty),
        "quality_range": qr,
        "arms": arms,
        "rank_mean": mean_rank,
        "rank_nspi": nspi_rank,
        "rank_spi_frozen": rank_r,
        "rank_spi_refreeze": rank_rp,
        "reference_frozen": r,
        "reference_refrozen": r_prime,
        "kendall_tau_refreeze": tau,
        "max_position_shift": shift,
        "kill_test_reject": rejected,
        "kill_test": "reject if ranking moves >1 position after r -> r'=final max",
    }


def run(out_path: Path | None = None) -> dict:
    out_path = out_path or OUT_PATH
    series = load_arm_series(LIFECYCLE_DB)
    result = score_campaign(series)
    if result.get("status") != "insufficient_data":
        _atomic_write(out_path, result)
    return result


def _self_test() -> int:
    n = 21
    series = {
        "A": [i / 20.0 for i in range(n)],
        "B": [0.5] * n,
        "C": [1.0 - i / 20.0 for i in range(n)],
        "D": [0.2 + 0.6 * (i / 20.0) for i in range(n)],
        "E": [0.8 - 0.1 * (i / 20.0) for i in range(n)],
    }
    r = score_campaign(series)
    assert r["status"] == "ok", r
    assert r["rank_nspi"][0] in ("A", "D"), r["rank_nspi"]
    assert r["arms"]["A"]["nspi"] > 0
    assert abs(r["arms"]["B"]["nspi"]) < 0.02
    assert r["arms"]["C"]["nspi"] < 0
    assert -1.0 <= r["kendall_tau_refreeze"] <= 1.0
    empty = score_campaign({})
    assert empty["status"] == "insufficient_data"
    tmp = Path(tempfile.mkdtemp()) / ("campaign-metrics_" + uuid.uuid4().hex + ".json")
    _atomic_write(tmp, r)
    loaded = json.loads(tmp.read_text(encoding="utf-8"))
    assert loaded["n_arms"] == 5
    tmp.unlink(missing_ok=True)
    tmp.with_name(tmp.name + ".lock").unlink(missing_ok=True)
    print("[campaign-scorer] --self-test PASS nspi_rank={} shift={} tau={:.3f}".format(
        r["rank_nspi"], r["max_position_shift"], r["kendall_tau_refreeze"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Anytime campaign scorer (NSPI + ranking)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[campaign-scorer] --self-test FAIL: {exc}")
            return 1
    try:
        result = run()
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
