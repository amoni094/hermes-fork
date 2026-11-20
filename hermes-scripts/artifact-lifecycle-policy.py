#!/usr/bin/env python3
"""Store vs regenerate cost policy for Hermes artifacts.

Cost model: C_store_full, C_store_IR, C_regen over a TTL window.
Reads fact_lifecycle (+ cache file sizes). Never invents access counts.
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
OUT_PATH = CACHE / "artifact_cost_policy.json"
LIFECYCLE_DB = _hermes_base / "memory-facts" / "lifecycle.db"

STORE_BYTE_DAY = 1.0
REGEN_PER_BYTE = 40.0
IR_STORE_FACTOR = 0.15
IR_REGEN_FACTOR = 0.40
TTL_DAYS_DEFAULT = 30.0
KILL_REDUCTION = 0.30


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


def _age_days(ts, now: datetime) -> float:
    if not ts:
        return TTL_DAYS_DEFAULT
    try:
        t = str(ts).replace("Z", "+00:00")
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return max(1.0 / 24.0, (now - dt).total_seconds() / 86400.0)
    except Exception:
        return TTL_DAYS_DEFAULT


def costs(size_bytes: float, access_count: float, age_days: float, ttl_days: float = TTL_DAYS_DEFAULT) -> dict:
    size = max(0.0, float(size_bytes))
    acc = max(0.0, float(access_count))
    age = max(1.0 / 24.0, float(age_days))
    ttl = max(1.0, float(ttl_days))
    rate = acc / age
    e_hits = rate * ttl
    regen_unit = size * REGEN_PER_BYTE
    c_store_full = size * STORE_BYTE_DAY * ttl
    c_regen = regen_unit * e_hits
    c_store_ir = size * IR_STORE_FACTOR * STORE_BYTE_DAY * ttl + regen_unit * IR_REGEN_FACTOR * e_hits
    options = {
        "store_full": c_store_full,
        "store_IR": c_store_ir,
        "regenerate": c_regen,
    }
    action = min(options.keys(), key=lambda k: options[k])
    # priority: higher expected hits first
    priority = float(e_hits)
    return {
        "action": action,
        "ttl_days": ttl,
        "priority": priority,
        "costs": options,
        "e_hits": e_hits,
        "size_bytes": size,
        "access_count": acc,
        "age_days": age,
    }


def load_facts(db_path: Path, now: datetime) -> list:
    if not db_path.exists():
        return []
    conn = None
    out = []
    try:
        conn = _connect(db_path)
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "fact_lifecycle" not in tabs:
            return []
        cols = {r[1] for r in conn.execute("PRAGMA table_info(fact_lifecycle)")}
        # required
        if "memory_id" not in cols:
            return []
        q = "SELECT memory_id, access_count, fact_text, last_accessed, valid_from FROM fact_lifecycle"
        rows = conn.execute(q).fetchall()
        for mid, acc, text, last, vf in rows:
            size = len(text.encode("utf-8")) if isinstance(text, str) else 0
            age = _age_days(last or vf, now)
            try:
                ac = float(acc or 0)
            except (TypeError, ValueError):
                ac = 0.0
            rec = costs(size, ac, age)
            rec["artifact_id"] = str(mid)
            rec["source"] = "fact_lifecycle"
            out.append(rec)
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()
    return out


def load_cache_files(cache_dir: Path, now: datetime, limit: int = 200) -> list:
    if not cache_dir.is_dir():
        return []
    out = []
    try:
        files = [p for p in cache_dir.iterdir() if p.is_file() and p.suffix in {".json", ".jsonl"}]
    except OSError:
        return []
    files.sort(key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)
    for p in files[:limit]:
        try:
            st = p.stat()
        except OSError:
            continue
        size = float(st.st_size)
        age = max(1.0 / 24.0, (now.timestamp() - st.st_mtime) / 86400.0)
        # access_count unknown — do not invent; use 0
        rec = costs(size, 0.0, age)
        # cache JSON is live system state, not regenerable model output
        ir_c = rec["costs"]["store_IR"]
        full_c = rec["costs"]["store_full"]
        rec["action"] = "store_IR" if ir_c <= full_c else "store_full"
        rec["artifact_id"] = p.name
        rec["source"] = "cache_file"
        out.append(rec)
    return out


def policy_from(items: list) -> dict:
    policy = {}
    for rec in items:
        aid = rec.get("artifact_id")
        if not aid:
            continue
        policy[aid] = {
            "action": rec["action"],
            "ttl_days": rec["ttl_days"],
            "priority": rec["priority"],
        }
    return policy


def aggregate_cost(items: list, action_field: str | None = None) -> float:
    total = 0.0
    for rec in items:
        act = rec["action"] if action_field is None else action_field
        total += float(rec["costs"].get(act, 0.0))
    return total


def run(db_path: Path, cache_dir: Path, out_path: Path) -> dict:
    now = datetime.now(UTC)
    items = load_facts(db_path, now) + load_cache_files(cache_dir, now)
    if not items:
        return {"status": "insufficient_data", "n": 0, "ts": _now()}
    policy = policy_from(items)
    baseline = aggregate_cost(items, "store_full")
    chosen = aggregate_cost(items, None)
    reduction = 0.0 if baseline <= 0 else (baseline - chosen) / baseline
    payload = {
        "ts": _now(),
        "status": "ok",
        "n": len(items),
        "policy": policy,
        "baseline_store_all": baseline,
        "chosen_cost": chosen,
        "reduction": reduction,
        "kill_test": {
            "required_reduction": KILL_REDUCTION,
            "observed_reduction": reduction,
            "reject_model": bool(reduction < KILL_REDUCTION),
        },
        "action_counts": {
            "store_full": sum(1 for r in items if r["action"] == "store_full"),
            "store_IR": sum(1 for r in items if r["action"] == "store_IR"),
            "regenerate": sum(1 for r in items if r["action"] == "regenerate"),
        },
    }
    _atomic_write(out_path, payload)
    payload["written"] = str(out_path)
    return payload


def _self_test() -> int:
    # High access, large regen → store_full
    hot = costs(1000, access_count=100, age_days=1.0, ttl_days=30)
    assert hot["action"] == "store_full", hot
    # Zero access → regenerate (never pay storage)
    cold = costs(1000, access_count=0, age_days=30, ttl_days=30)
    assert cold["action"] == "regenerate", cold
    # Medium access, large object → IR often wins
    mid = costs(10_000_000, access_count=2, age_days=10, ttl_days=30)
    assert mid["action"] in ("store_IR", "regenerate", "store_full"), mid

    td = Path(tempfile.mkdtemp(prefix="alp-"))
    try:
        db = td / "lc.db"
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE fact_lifecycle (memory_id TEXT, fact_text TEXT, fact_type TEXT, "
            "volatility_class TEXT, valid_from TEXT, valid_to TEXT, superseded_by TEXT, "
            "access_count INTEGER, last_accessed TEXT, interference_count INTEGER, "
            "last_interfered TEXT, retention_score REAL)"
        )
        conn.execute(
            "INSERT INTO fact_lifecycle (memory_id, fact_text, access_count, last_accessed) "
            "VALUES (?,?,?,?)",
            ("a1", "x" * 200, 50, _now()),
        )
        conn.execute(
            "INSERT INTO fact_lifecycle (memory_id, fact_text, access_count, last_accessed) "
            "VALUES (?,?,?,?)",
            ("a2", "y" * 20, 0, "2020-01-01T00:00:00+00:00"),
        )
        conn.commit()
        conn.close()
        cdir = td / "cache"
        cdir.mkdir()
        (cdir / "blob.json").write_text("{}", encoding="utf-8")
        out = td / ("artifact_cost_policy_test_" + uuid.uuid4().hex + ".json")
        live = run(db, cdir, out)
        assert live.get("status") == "ok", live
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert "a1" in payload["policy"] and "a2" in payload["policy"]
        assert payload["policy"]["a2"]["action"] in ("regenerate", "store_IR", "store_full")
        missing = run(td / "nope.db", td / "no-cache", td / "nope.json")
        assert missing.get("status") == "insufficient_data"
        assert not (td / "nope.json").exists()
    finally:
        import shutil

        shutil.rmtree(td, ignore_errors=True)
    print("[artifact-lifecycle-policy] --self-test PASS")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Artifact store vs regenerate policy")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--db", default=str(LIFECYCLE_DB))
    ap.add_argument("--cache", default=str(CACHE))
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f"[artifact-lifecycle-policy] --self-test FAIL: {exc}")
            sys.exit(1)
    try:
        result = run(Path(args.db), Path(args.cache), Path(args.out))
        slim = {k: result[k] for k in result if k != "policy"}
        slim["n_policy"] = len(result.get("policy") or {})
        print(json.dumps(slim, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
