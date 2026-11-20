#!/usr/bin/env python3
"""memory-access-recency.py — progressive disclosure score from recency + frequency.

claude-mem access-recency ranking (Wave 23-CM):

  disclosure_score = 0.6 * recency_weight + 0.4 * access_frequency_weight

recency_weight: 1.0 if last_accessed within 7 days, 0.5 if 7-30 days,
                0.1 if older or never.
access_frequency_weight: access_count / max(access_count), or 0.0 if max is 0.

Reads fact_lifecycle in lifecycle.db (shared path under _hermes_base).
Does not issue DDL. Missing DB / missing table / missing columns -> exit 0.

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone, timedelta, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

LIFECYCLE_DB = _hermes_base / "memory-facts" / "lifecycle.db"
RECENCY_RECENT_DAYS = 7
RECENCY_MID_DAYS = 30


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _parse_ts(raw) -> datetime | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                dt = None
        if dt is None:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def recency_weight(last_accessed, now: datetime | None = None) -> float:
    now = now or datetime.now(UTC)
    dt = _parse_ts(last_accessed)
    if dt is None:
        return 0.1
    age = now - dt
    if age <= timedelta(days=RECENCY_RECENT_DAYS):
        return 1.0
    if age <= timedelta(days=RECENCY_MID_DAYS):
        return 0.5
    return 0.1


def disclosure_score(recency_w: float, freq_w: float) -> float:
    s = 0.6 * float(recency_w) + 0.4 * float(freq_w)
    if s < 0.0:
        return 0.0
    if s > 1.0:
        return 1.0
    return s


def _open_db(path: Path):
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(str(path), timeout=30)
    except sqlite3.Error:
        return None
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    conn.row_factory = sqlite3.Row
    return conn


def _pick_table(conn: sqlite3.Connection) -> str | None:
    names = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    for cand in ("fact_lifecycle", "facts"):
        if cand in names:
            return cand
    return None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def score_rows(rows: list[dict], now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(UTC)
    max_count = 0
    for r in rows:
        try:
            c = int(r.get("access_count") or 0)
        except (TypeError, ValueError):
            c = 0
        max_count = max(max_count, c)
    out = []
    for r in rows:
        try:
            c = int(r.get("access_count") or 0)
        except (TypeError, ValueError):
            c = 0
        c = max(c, 0)
        freq_w = (c / max_count) if max_count > 0 else 0.0
        rec_w = recency_weight(r.get("last_accessed"), now=now)
        text = str(r.get("fact_text") or "")
        fid = r.get("memory_id")
        if fid is None:
            fid = r.get("fact_id")
        out.append(
            {
                "fact_id": str(fid) if fid is not None else "",
                "fact_text_preview": text[:80],
                "disclosure_score": round(disclosure_score(rec_w, freq_w), 6),
                "recency_weight": rec_w,
                "access_frequency_weight": round(freq_w, 6),
            }
        )
    out.sort(key=lambda x: (-x["disclosure_score"], x["fact_id"]))
    return out


def _load_prev_top(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(obj, dict):
        ids = obj.get("top10_ids")
        if isinstance(ids, list):
            return [str(x) for x in ids]
        scores = obj.get("scores")
        if isinstance(scores, list):
            return [str(x.get("fact_id") or "") for x in scores[:10]]
    if isinstance(obj, list):
        return [str(x.get("fact_id") or "") for x in obj[:10] if isinstance(x, dict)]
    return []


def run(db_path: Path, out_path: Path, alarm_path: Path) -> dict:
    empty_alarm = {
        "ts": _now(),
        "alarm": False,
        "changed": False,
        "top10_ids": [],
        "prev_top10_ids": [],
        "added": [],
        "removed": [],
    }
    if not db_path.exists():
        _atomic_write(out_path, [])
        empty_alarm["reason"] = "db_missing"
        _atomic_write(alarm_path, empty_alarm)
        return {"ok": True, "n": 0, "reason": "db_missing"}

    conn = _open_db(db_path)
    if conn is None:
        _atomic_write(out_path, [])
        empty_alarm["reason"] = "db_unreadable"
        _atomic_write(alarm_path, empty_alarm)
        return {"ok": True, "n": 0, "reason": "db_unreadable"}

    try:
        table = _pick_table(conn)
        if not table:
            _atomic_write(out_path, [])
            empty_alarm["reason"] = "schema_mismatch"
            _atomic_write(alarm_path, empty_alarm)
            return {"ok": True, "n": 0, "reason": "schema_mismatch"}
        cols = _columns(conn, table)
        id_col = "memory_id" if "memory_id" in cols else ("id" if "id" in cols else None)
        text_col = "fact_text" if "fact_text" in cols else ("text" if "text" in cols else None)
        if not id_col:
            _atomic_write(out_path, [])
            empty_alarm["reason"] = "schema_mismatch"
            _atomic_write(alarm_path, empty_alarm)
            return {"ok": True, "n": 0, "reason": "schema_mismatch"}
        has_access = "access_count" in cols
        has_last = "last_accessed" in cols
        select_cols = [id_col]
        if text_col:
            select_cols.append(text_col)
        if has_access:
            select_cols.append("access_count")
        if has_last:
            select_cols.append("last_accessed")
        sql = "SELECT " + ", ".join(select_cols) + " FROM " + table
        raw_rows = []
        for row in conn.execute(sql):
            d = dict(row)
            raw_rows.append(
                {
                    "memory_id": d.get(id_col),
                    "fact_text": d.get(text_col) if text_col else "",
                    "access_count": d.get("access_count", 0) if has_access else 0,
                    "last_accessed": d.get("last_accessed") if has_last else None,
                }
            )
    except sqlite3.Error:
        _atomic_write(out_path, [])
        empty_alarm["reason"] = "schema_mismatch"
        _atomic_write(alarm_path, empty_alarm)
        return {"ok": True, "n": 0, "reason": "schema_mismatch"}
    finally:
        try:
            conn.close()
        except Exception:
            pass

    scores = score_rows(raw_rows)
    prev_ids = _load_prev_top(out_path)
    top10 = [x["fact_id"] for x in scores[:10]]
    added = [i for i in top10 if i not in prev_ids]
    removed = [i for i in prev_ids if i not in top10]
    changed = bool(prev_ids) and bool(added or removed)
    alarm = {
        "ts": _now(),
        "alarm": changed,
        "changed": changed,
        "top10_ids": top10,
        "prev_top10_ids": prev_ids,
        "added": added,
        "removed": removed,
        "reason": "ok",
        "n": len(scores),
    }
    _atomic_write(out_path, scores)
    _atomic_write(alarm_path, alarm)
    return {"ok": True, "n": len(scores), "reason": "ok", "top10_changed": changed}


def _self_test() -> int:
    failures: list[str] = []
    uid = uuid.uuid4().hex
    td = Path(tempfile.mkdtemp(prefix="recency-" + uid[:8] + "-"))
    try:
        missing_db = td / "nope.db"
        out = td / f"scores_{uid}.json"
        alarm = td / f"alarm_{uid}.json"
        r = run(missing_db, out, alarm)
        if r.get("reason") != "db_missing":
            failures.append("missing db")
        if json.loads(out.read_text()) != []:
            failures.append("missing db should write empty scores")
        if json.loads(alarm.read_text()).get("top10_ids") != []:
            failures.append("missing db alarm not empty list")

        # empty table, max access_count = 0
        db = td / "lc.db"
        con = sqlite3.connect(str(db))
        con.execute('PRAGMA journal_mode=WAL')
        con.execute(
            "CREATE TABLE fact_lifecycle ("
            "memory_id TEXT PRIMARY KEY, fact_text TEXT, "
            "access_count INTEGER DEFAULT 0, last_accessed TEXT)"
        )
        now = datetime.now(UTC)
        recent = (now - timedelta(days=2)).isoformat()
        mid = (now - timedelta(days=14)).isoformat()
        old = (now - timedelta(days=90)).isoformat()
        con.executemany(
            "INSERT INTO fact_lifecycle(memory_id, fact_text, access_count, last_accessed) VALUES (?,?,?,?)",
            [
                ("a", "recent hot", 0, recent),
                ("b", "never", 0, None),
            ],
        )
        con.commit()
        con.close()
        r = run(db, out, alarm)
        scores = json.loads(out.read_text())
        by_id = {x["fact_id"]: x for x in scores}
        if abs(by_id["a"]["access_frequency_weight"]) > 1e-12:
            failures.append("max=0 freq should be 0, got " + str(by_id["a"]))
        if by_id["a"]["recency_weight"] != 1.0:
            failures.append("recent recency")
        if by_id["b"]["recency_weight"] != 0.1:
            failures.append("never recency")
        # expected disclosure: 0.6*1.0 + 0.4*0 = 0.6
        if abs(by_id["a"]["disclosure_score"] - 0.6) > 1e-6:
            failures.append("score a " + str(by_id["a"]["disclosure_score"]))

        con = sqlite3.connect(str(db))
        con.execute('PRAGMA journal_mode=WAL')
        con.execute("DELETE FROM fact_lifecycle")
        con.executemany(
            "INSERT INTO fact_lifecycle(memory_id, fact_text, access_count, last_accessed) VALUES (?,?,?,?)",
            [
                ("hot", "x" * 100, 10, recent),
                ("mid", "mid", 5, mid),
                ("old", "old", 0, old),
            ],
        )
        con.commit()
        con.close()
        out2 = td / f"scores2_{uid}.json"
        alarm2p = td / f"alarm2_{uid}.json"
        r = run(db, out2, alarm2p)
        scores = json.loads(out2.read_text())
        if scores[0]["fact_id"] != "hot":
            failures.append("sort " + scores[0]["fact_id"])
        if scores[0]["fact_text_preview"] != ("x" * 80):
            failures.append("preview length " + str(len(scores[0]["fact_text_preview"])))
        if abs(scores[0]["access_frequency_weight"] - 1.0) > 1e-9:
            failures.append("freq hot")
        if abs(scores[1]["access_frequency_weight"] - 0.5) > 1e-9:
            failures.append("freq mid")
        # first run vs empty prev: changed False (no prev)
        alarm1 = json.loads(alarm2p.read_text())
        if alarm1.get("changed") is not False:
            failures.append("first run changed should be false")
        # second run identical -> still write alarm, changed false
        run(db, out2, alarm2p)
        alarm2 = json.loads(alarm2p.read_text())
        if alarm2.get("top10_ids") != ["hot", "mid", "old"]:
            # sort by score then id; all three present
            if set(alarm2.get("top10_ids") or []) != {"hot", "mid", "old"}:
                failures.append("top10 " + str(alarm2.get("top10_ids")))
        if alarm2.get("added") != []:
            failures.append("second run added should be empty list")
        if alarm2.get("alarm") is not False:
            failures.append("second-run aggregator alarm should be false")

        # schema mismatch: no usable table
        db2 = td / "other.db"
        con = sqlite3.connect(str(db2))
        con.execute('PRAGMA journal_mode=WAL')
        con.execute("CREATE TABLE nope (x INTEGER)")
        con.commit()
        con.close()
        r = run(db2, td / f"s2_{uid}.json", td / f"a2_{uid}.json")
        if r.get("reason") != "schema_mismatch":
            failures.append("schema mismatch reason " + str(r))
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)

    if failures:
        print(json.dumps({"self_test": "FAIL", "failures": failures}))
        return 1
    print(json.dumps({"self_test": "PASS"}))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Access-recency disclosure scorer")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return _self_test()
    cache = _cache_dir()
    env_db = os.environ.get("LIFECYCLE_DB_PATH", "").strip()
    db = Path(env_db) if env_db else LIFECYCLE_DB
    result = run(db, cache / "access-recency-scores.json", cache / "access-recency-alarm.json")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e), "ts": _now()}))
        sys.exit(0)
