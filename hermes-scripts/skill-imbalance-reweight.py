#!/usr/bin/env python3
"""Imbalance-aware reweighting of rare skill routing scores."""
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


OUT_FREQ = CACHE / "skill-frequency.json"
OUT_W = CACHE / "skill-cost-weights.json"


def load_freq():
    freq = Counter()
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
                        freq[s] += 1
            if "delegation_audit" in tabs:
                cols = {r[1] for r in conn.execute("PRAGMA table_info(delegation_audit)")}
                if "tool_name" in cols:
                    rows = conn.execute(
                        "SELECT tool_name FROM delegation_audit WHERE tool_name IS NOT NULL"
                    ).fetchall()
                    for (name,) in rows:
                        s = str(name or "").strip()
                        if s:
                            freq[s] += 1
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    events = CACHE / "routing-events.jsonl"
    for rec in _iter_jsonl(events):
        s = rec.get("top_skill") or rec.get("skill")
        if s:
            freq[str(s)] += 1
    return dict(freq)


def reweight(freq: dict) -> tuple:
    if not freq:
        empty = {"status": "insufficient_data", "n": 0, "ts": _now()}
        return empty, empty
    n_tot = sum(freq.values())
    items = sorted(freq.items(), key=lambda kv: (kv[1], kv[0]))
    # rare = bottom quintile among positive counts
    q = max(1, len(items) // 5)
    rare = [k for k, _ in items[:q]]
    weights = {}
    for k, c in freq.items():
        # IRW: N / (n_classes * n_k), clipped
        w = n_tot / (max(len(freq), 1) * max(c, 1))
        w = math.sqrt(w)
        weights[k] = w
    mx = max(weights.values()) or 1.0
    weights = {k: v / mx for k, v in weights.items()}
    rare_mass = sum(freq[k] for k in rare) / n_tot if n_tot else 0.0
    freq_out = {
        "ts": _now(),
        "status": "ok",
        "n_events": n_tot,
        "n_skills": len(freq),
        "rare_skills": rare,
        "rare_mass": rare_mass,
        "freq": dict(items[:80]),
    }
    w_out = {
        "ts": _now(),
        "status": "ok",
        "scheme": "sqrt_irw",
        "n_skills": len(weights),
        "rare_boosted": rare,
        "weights": {k: weights[k] for k, _ in items[:80]},
    }
    return freq_out, w_out


def run(freq_path: Path | None = None, w_path: Path | None = None) -> dict:
    freq_path = freq_path or OUT_FREQ
    w_path = w_path or OUT_W
    freq_out, w_out = reweight(load_freq())
    if freq_out.get("status") != "insufficient_data":
        _atomic_write(freq_path, freq_out)
        _atomic_write(w_path, w_out)
    return {"frequency": freq_out, "weights": w_out}


def _self_test() -> int:
    freq = {"common": 100, "mid": 20, "rare_a": 2, "rare_b": 1, "rare_c": 1}
    f, w = reweight(freq)
    assert f["status"] == "ok"
    assert w["weights"]["rare_a"] > w["weights"]["common"]
    empty_f, _ = reweight({})
    assert empty_f["status"] == "insufficient_data"
    td = Path(tempfile.mkdtemp())
    fp = td / ("skill-frequency_" + uuid.uuid4().hex + ".json")
    wp = td / ("skill-cost-weights_" + uuid.uuid4().hex + ".json")
    _atomic_write(fp, f)
    _atomic_write(wp, w)
    json.loads(fp.read_text())
    fp.unlink(missing_ok=True)
    wp.unlink(missing_ok=True)
    print("[skill-imbalance-reweight] --self-test PASS rare={}".format(f["rare_skills"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Imbalance-aware skill reweighting")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[skill-imbalance-reweight] --self-test FAIL: {exc}")
            return 1
    try:
        print(json.dumps(run()))
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
