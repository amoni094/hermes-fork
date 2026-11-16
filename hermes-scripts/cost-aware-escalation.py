#!/usr/bin/env python3
"""Cost-aware escalation thresholds for low-confidence skill results."""
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


OUT_PATH = CACHE / "escalation-state.json"
CALIB = CACHE / "calibration-log.jsonl"
LATENCY = CACHE / "skill-latency.jsonl"
ALPHA = 0.05
CONF_THRESH = 0.5
COST_CAP = 1.0  # relative budget; escalate fraction target


def load_items():
    lat = {}
    for rec in _iter_jsonl(LATENCY):
        tn = rec.get("tool_name")
        ms = rec.get("elapsed_ms")
        if not tn:
            continue
        try:
            v = float(ms)
        except (TypeError, ValueError):
            continue
        if math.isfinite(v) and v >= 0:
            lat.setdefault(str(tn), []).append(v)
    mean_lat = {k: sum(v) / len(v) for k, v in lat.items() if v}
    items = []
    for rec in _iter_jsonl(CALIB, max_rows=80000):
        if rec.get("scope") == UE_SENTINEL:
            continue
        skill = rec.get("scope") or rec.get("tool_name")
        if not skill:
            continue
        try:
            conf = float(rec.get("predicted_confidence"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(conf):
            continue
        outcome = rec.get("actual_outcome")
        label = None
        if outcome is True or outcome == 1 or outcome == "1" or outcome == "success":
            label = 1
        elif outcome is False or outcome == 0 or outcome == "0" or outcome == "fail":
            label = 0
        cost = mean_lat.get(str(skill), 1.0)
        items.append({"skill": str(skill), "conf": _clip01(conf), "label": label, "cost": cost})
    return items


def policy(items, thresh=CONF_THRESH, alpha=ALPHA) -> dict:
    if len(items) < 20:
        return {"status": "insufficient_data", "n": len(items), "ts": _now()}
    n = len(items)
    esc = [it for it in items if it["conf"] < thresh]
    [it for it in items if it["conf"] >= thresh]
    esc_rate = len(esc) / n
    mean_cost = sum(it["cost"] for it in items) / n
    esc_cost = sum(it["cost"] for it in esc) / n if n else 0.0
    labeled = [it for it in items if it["label"] is not None]
    fp = fn = 0
    nlab = len(labeled)
    for it in labeled:
        pred_pos = it["conf"] >= thresh
        true_pos = it["label"] == 1
        if pred_pos and not true_pos:
            fp += 1
        if (not pred_pos) and true_pos:
            fn += 1
    err = ((fp + fn) / nlab) if nlab else None
    # tune threshold toward alpha if labels exist
    tuned = thresh
    if nlab >= 30:
        # scan a few thresholds
        best = thresh
        best_gap = 1e9
        for t in (0.3, 0.4, 0.5, 0.6, 0.7):
            efp = efn = 0
            for it in labeled:
                pred_pos = it["conf"] >= t
                true_pos = it["label"] == 1
                if pred_pos and not true_pos:
                    efp += 1
                if (not pred_pos) and true_pos:
                    efn += 1
            e = (efp + efn) / nlab
            gap = abs(e - alpha)
            if gap < best_gap:
                best_gap = gap
                best = t
        tuned = best
    ok = True if err is None else (err <= alpha + 0.02)
    return {
        "ts": _now(),
        "status": "ok",
        "n": n,
        "n_labeled": nlab,
        "threshold": thresh,
        "tuned_threshold": tuned,
        "alpha": alpha,
        "escalation_rate": esc_rate,
        "mean_cost": mean_cost,
        "escalation_cost_share": esc_cost,
        "error_rate": err,
        "kill_test_pass": ok,
        "n_escalated": len(esc),
    }


def run(out_path: Path | None = None) -> dict:
    out_path = out_path or OUT_PATH
    result = policy(load_items())
    if result.get("status") != "insufficient_data":
        _atomic_write(out_path, result)
    return result


def _self_test() -> int:
    items = []
    for i in range(80):
        conf = 0.9 if i < 50 else 0.2
        label = 1 if i < 50 else 0
        items.append({"skill": "s", "conf": conf, "label": label, "cost": 1.0})
    r = policy(items, thresh=0.5, alpha=0.05)
    assert r["status"] == "ok"
    assert r["escalation_rate"] > 0
    assert r["error_rate"] is not None
    empty = policy([])
    assert empty["status"] == "insufficient_data"
    tmp = Path(tempfile.mkdtemp()) / ("escalation-state_" + uuid.uuid4().hex + ".json")
    _atomic_write(tmp, r)
    json.loads(tmp.read_text())
    tmp.unlink(missing_ok=True)
    print("[cost-aware-escalation] --self-test PASS rate={:.3f} err={}".format(r["escalation_rate"], r["error_rate"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Cost-aware escalation policy")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[cost-aware-escalation] --self-test FAIL: {exc}")
            return 1
    try:
        print(json.dumps(run()))
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
