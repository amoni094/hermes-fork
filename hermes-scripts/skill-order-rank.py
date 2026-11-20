#!/usr/bin/env python3
"""Pairwise skill/tool pass-order ranking from session traces.

Empirical rank of (s_i before s_j) from anytime_eval_log + calibration-log.
JSON schema: skill_pair, success_count, total_count, rank.
Stdlib only. Profile-aware. Default action is --run (cron-safe).
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import sqlite3
import statistics
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
OUT_PATH = CACHE / "skill-order-rank.json"
LIFECYCLE_DB = _hermes_base / "memory-facts" / "lifecycle.db"
CALIBRATION_LOG = CACHE / "calibration-log.jsonl"
KILL_STD_PP = 5.0
LAPLACE = 1.0
MAX_CAL_BYTES = 4_000_000
MAX_SEQ = 40
MIN_PAIR_N = 3


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


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def pair_rank(success_count: int, total_count: int) -> float:
    if total_count < 0:
        return 0.0
    return _clip01((success_count + LAPLACE) / (total_count + 2.0 * LAPLACE))


def _session_success(score, extra) -> int:
    try:
        if score is not None and float(score) >= 0.5:
            return 1
    except (TypeError, ValueError):
        pass
    if isinstance(extra, dict):
        if extra.get("success") is True:
            return 1
        if extra.get("success") is False:
            return 0
        try:
            if float(extra.get("eval_score", 0) or 0) >= 0.5:
                return 1
        except (TypeError, ValueError):
            pass
    return 0


def load_eval_sessions(db_path: Path) -> list:
    """Return list of (session_id, sequence[str], success:int)."""
    out = []
    if not db_path.exists():
        return out
    conn = None
    try:
        conn = _connect(db_path)
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "anytime_eval_log" not in tabs:
            return out
        rows = conn.execute(
            "SELECT session_id, ts, skill_id, eval_score, quality_tier "
            "FROM anytime_eval_log ORDER BY session_id, ts"
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()
    buckets = defaultdict(list)
    for sid, ts, skill, score, tier in rows:
        if not sid or not skill:
            continue
        extra = {}
        if isinstance(tier, str) and tier.startswith("{"):
            try:
                extra = json.loads(tier)
            except json.JSONDecodeError:
                extra = {}
        elif isinstance(tier, dict):
            extra = tier
        buckets[str(sid)].append((str(ts or ""), str(skill), score, extra))
    for sid, items in buckets.items():
        items.sort(key=lambda r: r[0])
        seq = []
        for _ts, skill, _sc, _ex in items:
            if skill not in seq:
                seq.append(skill)
            if len(seq) >= MAX_SEQ:
                break
        if len(seq) < 2:
            continue
        last = items[-1]
        ok = _session_success(last[2], last[3])
        out.append((sid, seq, ok))
    return out


def load_cal_sessions(log_path: Path, max_bytes: int = MAX_CAL_BYTES) -> list:
    if not log_path.exists():
        return []
    try:
        size = log_path.stat().st_size
    except OSError:
        return []
    buckets = defaultdict(list)
    try:
        with open(log_path, "rb") as fh:
            if size > max_bytes:
                fh.seek(max(0, size - max_bytes))
                fh.readline()
            for raw in fh:
                try:
                    line = raw.decode("utf-8", "replace")
                    rec = json.loads(line)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                sid = rec.get("session_id")
                tool = rec.get("tool_name") or rec.get("skill_id") or rec.get("skill_name")
                if not sid or not tool:
                    continue
                if rec.get("scope") == "ue_blackbox":
                    continue
                buckets[str(sid)].append((str(rec.get("ts") or ""), str(tool), rec))
    except OSError:
        return []
    out = []
    for sid, items in buckets.items():
        items.sort(key=lambda r: r[0])
        seq = []
        for _ts, tool, _rec in items:
            if tool not in seq:
                seq.append(tool)
            if len(seq) >= MAX_SEQ:
                break
        if len(seq) < 2:
            continue
        last = items[-1][2]
        outcome = last.get("actual_outcome")
        try:
            ok = 1 if (outcome is None and float(last.get("predicted_confidence") or 0) >= 0.5) or float(outcome or 0) >= 0.5 else 0
        except (TypeError, ValueError):
            ok = 0
        out.append((sid, seq, ok))
    return out


def accumulate_pairs(sessions: list) -> dict:
    """pair -> {success_count, total_count}."""
    pairs = {}
    for _sid, seq, ok in sessions:
        n = len(seq)
        for i in range(n):
            for j in range(i + 1, n):
                key = (seq[i], seq[j])
                rec = pairs.setdefault(key, {"success_count": 0, "total_count": 0})
                rec["total_count"] += 1
                rec["success_count"] += int(ok)
    return pairs


def pairs_to_records(pairs: dict) -> list:
    recs = []
    for (a, b), st in pairs.items():
        recs.append(
            {
                "skill_pair": [a, b],
                "success_count": int(st["success_count"]),
                "total_count": int(st["total_count"]),
                "rank": pair_rank(int(st["success_count"]), int(st["total_count"])),
            }
        )
    recs.sort(key=lambda r: (-r["rank"], -r["total_count"], r["skill_pair"][0], r["skill_pair"][1]))
    return recs


def recommended_order(records: list, k: int = 12) -> list:
    """Score nodes by weighted log-odds of appearing earlier in successful pairs."""
    score = defaultdict(float)
    for rec in records:
        if rec["total_count"] < MIN_PAIR_N:
            continue
        a, b = rec["skill_pair"]
        w = math.log(rec["total_count"] + 1.0)
        r = rec["rank"]
        score[a] += w * (r - 0.5)
        score[b] -= w * (r - 0.5)
    ranked = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))
    return [name for name, _s in ranked[:k]]


def batch_std_pp(sessions: list, n_batches: int = 10) -> dict:
    """Kill-test: std of success rate for the same pair over independent batches, in pp."""
    if len(sessions) < n_batches * 2:
        return {"status": "insufficient_data", "n": len(sessions), "std_pp": None, "reject_hard_core": False}
    batches = [[] for _ in range(n_batches)]
    for i, sess in enumerate(sessions):
        batches[i % n_batches].append(sess)
    # pick the globally most frequent pair
    global_pairs = accumulate_pairs(sessions)
    if not global_pairs:
        return {"status": "insufficient_data", "n": len(sessions), "std_pp": None, "reject_hard_core": False}
    top = max(global_pairs.items(), key=lambda kv: kv[1]["total_count"])[0]
    rates = []
    for batch in batches:
        p = accumulate_pairs(batch).get(top)
        if not p or p["total_count"] <= 0:
            continue
        rates.append(p["success_count"] / p["total_count"])
    if len(rates) < 3:
        return {"status": "insufficient_data", "n": len(sessions), "std_pp": None, "reject_hard_core": False}
    std_pp = float(statistics.pstdev(rates) * 100.0)
    return {
        "status": "ok",
        "pair": list(top),
        "n_batches_used": len(rates),
        "std_pp": std_pp,
        "reject_hard_core": bool(std_pp > KILL_STD_PP),
    }


def run(db_path: Path, cal_path: Path, out_path: Path) -> dict:
    sessions = load_eval_sessions(db_path) + load_cal_sessions(cal_path)
    if not sessions:
        return {"status": "insufficient_data", "n": 0, "ts": _now()}
    pairs = accumulate_pairs(sessions)
    if not pairs:
        return {"status": "insufficient_data", "n": len(sessions), "ts": _now()}
    records = pairs_to_records(pairs)
    kill = batch_std_pp(sessions)
    payload = {
        "ts": _now(),
        "status": "ok",
        "n_sessions": len(sessions),
        "n_pairs": len(records),
        "pairs": records[:500],
        "top3_orderings": recommended_order(records, 8)[:3],
        "recommended_order": recommended_order(records),
        "kill_test": kill,
        "schema": {
            "skill_pair": "(s_i, s_j)",
            "success_count": "int",
            "total_count": "int",
            "rank": "float",
        },
    }
    _atomic_write(out_path, payload)
    payload["written"] = str(out_path)
    return payload


def _self_test() -> int:
    # Deterministic pair ranks
    assert abs(pair_rank(9, 10) - (10 / 12)) < 1e-9
    assert 0.0 <= pair_rank(0, 0) <= 1.0
    sess = [
        ("s1", ["A", "B", "C"], 1),
        ("s2", ["A", "B", "C"], 1),
        ("s3", ["C", "B", "A"], 0),
        ("s4", ["A", "C"], 1),
    ]
    recs = pairs_to_records(accumulate_pairs(sess))
    ab = next(r for r in recs if r["skill_pair"] == ["A", "B"])
    assert ab["success_count"] == 2 and ab["total_count"] == 2, ab
    order = recommended_order(recs)
    assert order[0] == "A", order

    td = Path(tempfile.mkdtemp(prefix="sor-"))
    try:
        db = td / "lc.db"
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE anytime_eval_log (id INTEGER PRIMARY KEY, ts TEXT, "
            "session_id TEXT, skill_id TEXT, eval_score REAL, quality_tier TEXT)"
        )
        rows = [
            ("t1", "S1", "read_file", 1.0, '{"success": true}'),
            ("t2", "S1", "patch", 1.0, '{"success": true}'),
            ("t3", "S2", "patch", 0.0, '{"success": false}'),
            ("t4", "S2", "read_file", 0.0, '{"success": false}'),
            ("t5", "S3", "read_file", 1.0, '{"success": true}'),
            ("t6", "S3", "search_files", 1.0, '{"success": true}'),
        ]
        for ts, sid, sk, sc, qt in rows:
            conn.execute(
                "INSERT INTO anytime_eval_log (ts, session_id, skill_id, eval_score, quality_tier) "
                "VALUES (?,?,?,?,?)",
                (ts, sid, sk, sc, qt),
            )
        conn.commit()
        conn.close()
        cal = td / "cal.jsonl"
        cal.write_text("", encoding="utf-8")
        out = td / ("skill-order-rank_test_" + uuid.uuid4().hex + ".json")
        live = run(db, cal, out)
        assert live.get("status") == "ok", live
        assert out.exists()
        payload = json.loads(out.read_text(encoding="utf-8"))
        json.loads(json.dumps(payload))
        assert payload["n_pairs"] >= 1
        missing = run(td / "nope.db", td / "nope.jsonl", td / "nope.json")
        assert missing.get("status") == "insufficient_data", missing
        assert not (td / "nope.json").exists()
        # empty string / malformed JSON in cal
        bad = td / "bad.jsonl"
        bad.write_text("{not json\n\n", encoding="utf-8")
        r2 = run(db, bad, td / ("skill-order-rank_test_" + uuid.uuid4().hex + ".json"))
        assert r2.get("status") == "ok", r2
    finally:
        import shutil

        shutil.rmtree(td, ignore_errors=True)
    print("[skill-order-rank] --self-test PASS")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Pairwise skill order ranking")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--db", default=str(LIFECYCLE_DB))
    ap.add_argument("--cal", default=str(CALIBRATION_LOG))
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f"[skill-order-rank] --self-test FAIL: {exc}")
            sys.exit(1)
    try:
        result = run(Path(args.db), Path(args.cal), Path(args.out))
        slim = {k: result[k] for k in result if k != "pairs"}
        slim["n_pairs_emitted"] = len(result.get("pairs") or [])
        print(json.dumps(slim, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
