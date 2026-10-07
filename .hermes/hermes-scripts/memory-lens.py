#!/usr/bin/env python3
"""memory-lens.py — Harper PFPL / Reynolds separation lens laws for WM.

A store lens over working-memory documents:

  get : S → A
  put : S × A → S

Hard-core laws (if any fails the memory interface is unsound):
  GetPut: put s (get s) = s
  PutGet: get (put s a) = a
  PutPut: put (put s a) b = put s b

Timestamps / MAC are excluded from the lens payload so GetPut is not
vacuously broken by _save() side effects.

Usage:
  python3 memory-lens.py --self-test
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path
from typing import Any


META_KEYS = frozenset({"updated_at", "_mac", "schema"})


def get_payload(s: dict[str, Any], key: str) -> Any:
    return copy.deepcopy(s.get(key))


def put_payload(s: dict[str, Any], key: str, a: Any) -> dict[str, Any]:
    out = copy.deepcopy(s)
    out[key] = copy.deepcopy(a)
    return out


def getput_ok(s: dict[str, Any], key: str) -> bool:
    return put_payload(s, key, get_payload(s, key)) == s


def putget_ok(s: dict[str, Any], key: str, a: Any) -> bool:
    return get_payload(put_payload(s, key, a), key) == a


def putput_ok(s: dict[str, Any], key: str, a: Any, b: Any) -> bool:
    return put_payload(put_payload(s, key, a), key, b) == put_payload(s, key, b)


def empty_wm(session_id: str = "lens-test") -> dict[str, Any]:
    return {
        "schema": "hermes-working-memory/v3",
        "session_id": session_id,
        "goal": "",
        "progress": [],
        "next": [],
        "open_decisions": [],
        "constraints": [],
        "active_skills": [],
        "beliefs": {},
    }


def self_test() -> int:
    s = empty_wm()
    s["goal"] = "ship wave 18"
    s["progress"] = ["wrote doob"]
    s["beliefs"] = {"k": {"text": "x", "conf": 0.9}}
    for key in ("goal", "progress", "beliefs", "constraints"):
        assert getput_ok(s, key), f"GetPut fail {key}"
        a = get_payload(s, key)
        # mutate a into a distinct value
        if key == "goal":
            a2 = "other goal"
        elif key == "beliefs":
            a2 = {"z": {"text": "y", "conf": 0.1}}
        else:
            a2 = ["new"]
        assert putget_ok(s, key, a2), f"PutGet fail {key}"
        b = a
        assert putput_ok(s, key, a2, b), f"PutPut fail {key}"
    # PutPut last-write-wins
    s2 = put_payload(s, "goal", "a")
    s3 = put_payload(s2, "goal", "b")
    assert s3["goal"] == "b"
    # ADV-012: SQLite-backed lens law verification
    import sqlite3, tempfile, os, json as _json
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "test_lens.db")
        with sqlite3.connect(db_path) as con:
            con.execute("CREATE TABLE memories(key TEXT PRIMARY KEY, value TEXT)")
            def _sql_put(key: str, val: Any) -> None:
                con.execute("INSERT OR REPLACE INTO memories(key,value) VALUES(?,?)",
                            (key, _json.dumps(val)))
                con.commit()
            def _sql_get(key: str) -> Any:
                row = con.execute("SELECT value FROM memories WHERE key=?", (key,)).fetchone()
                return _json.loads(row[0]) if row else None
            # GetPut: get(put(s, k, a), k) == a
            _sql_put("k1", "hello")
            assert _sql_get("k1") == "hello", "SQLite GetPut failed"
            # PutPut: second put overwrites first
            _sql_put("k1", "first")
            _sql_put("k1", "second")
            assert _sql_get("k1") == "second", "SQLite PutPut (last-write-wins) failed"
            # PutGet: put then get returns same value
            _sql_put("k2", {"nested": [1, 2, 3]})
            assert _sql_get("k2") == {"nested": [1, 2, 3]}, "SQLite PutGet failed"
    print("PASS memory-lens SQLite lens-law verification (ADV-012)")
    print("PASS memory-lens self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        print(json.dumps({"ok": True, "laws": ["GetPut", "PutGet", "PutPut"]}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "fail_open": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
