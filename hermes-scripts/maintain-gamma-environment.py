#!/usr/bin/env python3
"""Decode-time Gamma environment: declared symbols for constrained tool calls."""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import random
import sqlite3
import statistics
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
_lifecycle_home = _hermes_base.parent.parent if _hermes_base.parent.name == "profiles" else _hermes_base
LIFECYCLE_DB = _lifecycle_home / "memory-facts" / "lifecycle.db"
CACHE = _hermes_root / "cache"

OUT_PATH = CACHE / "gamma-state.json"

def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    tmp = path.with_name(path.name + ".tmp")
    payload = json.dumps(obj, indent=2) + "\n"
    with open(str(lock_path), "a", encoding="utf-8") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _connect(db: Path):
    conn = sqlite3.connect(str(db), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


SENTINEL_SKIP = frozenset({"ue_blackbox", ""})


def collect_gamma(db_path: Path, extra_names=None):
    names = set()
    if extra_names:
        names.update(str(x) for x in extra_names if x)
    if db_path.exists():
        conn = _connect(db_path)
        try:
            rows = conn.execute(
                "SELECT DISTINCT tool_name FROM tool_review_log WHERE tool_name IS NOT NULL"
            ).fetchall()
        except sqlite3.Error:
            rows = []
        try:
            rows2 = conn.execute(
                "SELECT DISTINCT skill_id FROM anytime_eval_log WHERE skill_id IS NOT NULL"
            ).fetchall()
        except sqlite3.Error:
            rows2 = []
        finally:
            conn.close()
        for (n,) in rows + rows2:
            if n and n not in SENTINEL_SKIP:
                names.add(str(n))
    skills_dir = _hermes_root / "skills"
    if skills_dir.is_dir():
        for p in skills_dir.rglob("SKILL.md"):
            names.add(p.parent.name)
    declared = sorted(names)
    return {
        "ts": _now(),
        "status": "ok" if declared else "insufficient_data",
        "n_symbols": len(declared),
        "Gamma": declared,
        "by_kind": {"tools_and_skills": declared},
    }


def mask_call(call: dict, gamma: set) -> dict:
    """Drop arguments / names not in Gamma. Undefined-reference filter."""
    name = str(call.get("name") or call.get("tool") or "")
    if name not in gamma:
        return {"ok": False, "reason": "undefined_reference", "name": name, "args": {}}
    args_in = call.get("args") or call.get("parameters") or {}
    kept = {}
    dropped = []
    if isinstance(args_in, dict):
        for k, v in args_in.items():
            if isinstance(v, str) and v.startswith("$") and v[1:] not in gamma:
                dropped.append(v)
                continue
            kept[k] = v
    return {"ok": True, "name": name, "args": kept, "dropped": dropped}


def run(out_path=None, db_path=None, extra_names=None):
    dest = out_path or OUT_PATH
    db = db_path or LIFECYCLE_DB
    try:
        state = collect_gamma(db, extra_names=extra_names)
        _atomic_write_json(dest, state)
        return state
    except Exception as exc:
        err = {"ts": _now(), "status": "error", "error": str(exc), "n_symbols": 0, "Gamma": []}
        try:
            _atomic_write_json(dest, err)
        except Exception:
            pass
        return err


def _self_test():
    tmp = Path(tempfile.mkdtemp(prefix="gamma-"))
    out = tmp / ("gamma-state_test_" + uuid.uuid4().hex + ".json")
    db = tmp / "empty.db"
    run(out_path=out, db_path=db, extra_names=["read_file", "terminal", "search_files"])
    assert out.exists()
    data = json.loads(out.read_text())
    g = set(data["Gamma"])
    assert "read_file" in g
    ok = mask_call({"name": "read_file", "args": {"path": "x"}}, g)
    assert ok["ok"] is True
    bad = mask_call({"name": "not_a_tool_" + uuid.uuid4().hex, "args": {}}, g)
    assert bad["ok"] is False
    ghost = mask_call({"name": "read_file", "args": {"ref": "$MissingSymbol"}}, g)
    assert "MissingSymbol" not in str(ghost["args"])
    empty = collect_gamma(tmp / "no-such.db", extra_names=[])
    # skills dir may still populate Gamma on a live profile; empty extra+missing db must not crash
    assert "Gamma" in empty and isinstance(empty["Gamma"], list)
    none = mask_call({"name": "x", "args": {}}, set())
    assert none["ok"] is False
    print("[maintain-gamma-environment] --self-test PASS n=%d" % data["n_symbols"])
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print("[maintain-gamma-environment] --self-test FAIL:", exc)
            return 1
    state = run()
    print(json.dumps({"status": state.get("status"), "n_symbols": state.get("n_symbols")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
