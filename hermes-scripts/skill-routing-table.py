#!/usr/bin/env python3
"""Condition-to-skill routing table with selection entropy."""
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


OUT_PATH = CACHE / "routing-conditions.json"
EVENTS = CACHE / "routing-events.jsonl"


def _bucket_hour(ts) -> str:
    s = str(ts or "")
    # ISO ...T HH
    if "T" in s and len(s) >= 13:
        try:
            h = int(s.split("T", 1)[1][:2])
            return f"h{(h // 6) * 6:02d}-{(h // 6) * 6 + 6:02d}" 
        except ValueError:
            return "h_unknown"
    return "h_unknown"


def _bucket_qlen(n) -> str:
    try:
        v = int(n)
    except (TypeError, ValueError):
        return "q_unknown"
    if v < 8:
        return "q_short"
    if v < 40:
        return "q_med"
    return "q_long"


def _prefix(skill: str) -> str:
    if not skill:
        return "other"
    if "-" in skill:
        return skill.split("-", 1)[0]
    return skill[:12]


def shannon(counts) -> float:
    tot = float(sum(counts))
    if tot <= 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c > 0:
            p = c / tot
            h -= p * math.log(p)
    return h


def load_events():
    rows = []
    for rec in _iter_jsonl(EVENTS):
        skill = rec.get("top_skill") or rec.get("skill")
        if not skill:
            continue
        rows.append({
            "skill": str(skill),
            "score": rec.get("top_score", rec.get("score")),
            "qlen": rec.get("query_len"),
            "ts": rec.get("ts"),
        })
    db = LIFECYCLE_DB
    if db.exists():
        conn = _connect(db)
        try:
            tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "anytime_eval_log" in tabs:
                erows = conn.execute(
                    "SELECT ts, skill_id, eval_score FROM anytime_eval_log "
                    "WHERE skill_id IS NOT NULL LIMIT 20000"
                ).fetchall()
                for ts, skill, score in erows:
                    s = str(skill or "").strip()
                    if not s or s.startswith("audit"):
                        continue
                    rows.append({"skill": s, "score": score, "qlen": None, "ts": ts})
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    return rows


def build_table(rows) -> dict:
    if len(rows) < 10:
        return {"status": "insufficient_data", "n": len(rows), "ts": _now(), "conditions": {}}
    cond = defaultdict(Counter)
    scores = defaultdict(lambda: defaultdict(list))
    global_c = Counter()
    for rec in rows:
        skill = rec["skill"]
        hour = _bucket_hour(rec.get("ts"))
        qlen = _bucket_qlen(rec.get("qlen"))
        pref = _prefix(skill)
        keys = [hour, qlen, pref, hour + "|" + qlen]
        for k in keys:
            cond[k][skill] += 1
            if rec.get("score") is not None:
                try:
                    scores[k][skill].append(float(rec["score"]))
                except (TypeError, ValueError):
                    pass
        global_c[skill] += 1
    table = {}
    nmse_num = nmse_den = 0
    for k, ctr in cond.items():
        tot = sum(ctr.values())
        best = ctr.most_common(1)[0][0]
        h = shannon(ctr.values())
        # conditional routing error vs best mean-score skill if available
        sk_scores = scores.get(k) or {}
        best_q = None
        if sk_scores:
            means = {s: sum(vs) / len(vs) for s, vs in sk_scores.items() if vs}
            if means:
                best_q = max(means, key=means.get)
                if best_q != best:
                    nmse_num += 1
                nmse_den += 1
        table[k] = {
            "n": tot,
            "best_skill": best,
            "best_quality_skill": best_q,
            "entropy": h,
            "top": ctr.most_common(5),
        }
    entropy = shannon(global_c.values())
    acc = None
    if nmse_den:
        acc = 1.0 - (nmse_num / nmse_den)
    return {
        "ts": _now(),
        "status": "ok",
        "n": len(rows),
        "n_conditions": len(table),
        "skill_selection_entropy": entropy,
        "skill_conditional_accuracy": acc,
        "skill_conditional_nmse": (nmse_num / nmse_den) if nmse_den else None,
        "n_skills": len(global_c),
        "conditions": table,
    }


def run(out_path: Path | None = None) -> dict:
    out_path = out_path or OUT_PATH
    result = build_table(load_events())
    if result.get("status") != "insufficient_data":
        _atomic_write(out_path, result)
    return result


def _self_test() -> int:
    rows = []
    for i in range(30):
        rows.append({"skill": "alpha" if i % 3 else "beta", "score": 0.9 if i % 3 else 0.2,
                     "qlen": 4 if i < 10 else 50, "ts": f"2026-01-01T0{i % 9}:00:00Z"})
    r = build_table(rows)
    assert r["status"] == "ok", r
    assert r["skill_selection_entropy"] > 0
    assert "q_short" in r["conditions"]
    empty = build_table([])
    assert empty["status"] == "insufficient_data"
    tmp = Path(tempfile.mkdtemp()) / ("routing-conditions_" + uuid.uuid4().hex + ".json")
    _atomic_write(tmp, r)
    json.loads(tmp.read_text())
    tmp.unlink(missing_ok=True)
    print("[skill-routing-table] --self-test PASS H={:.3f} n={}".format(r["skill_selection_entropy"], r["n"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Condition->skill routing table")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f"[skill-routing-table] --self-test FAIL: {exc}")
            return 1
    try:
        print(json.dumps(run()))
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
