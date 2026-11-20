#!/usr/bin/env python3
"""Filter tool-call args using Gamma from gamma-state.json."""
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

GAMMA_PATH = CACHE / "gamma-state.json"

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


def load_gamma(path=None):
    p = path or GAMMA_PATH
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return set(data.get("Gamma") or [])


def filter_call(call, gamma=None):
    gamma = gamma if gamma is not None else load_gamma()
    name = str((call or {}).get("name") or "")
    if not gamma:
        return {"ok": False, "status": "insufficient_data", "name": name, "args": {}}
    if name not in gamma:
        return {"ok": False, "reason": "undefined_reference", "name": name, "args": {}}
    args_in = (call or {}).get("args") or {}
    kept = {}
    if isinstance(args_in, dict):
        for k, v in args_in.items():
            if isinstance(v, str) and v.startswith("$") and v[1:] not in gamma:
                continue
            kept[k] = v
    return {"ok": True, "name": name, "args": kept}


def run():
    g = load_gamma()
    report = {"ts": _now(), "status": "ok" if g else "insufficient_data", "n_symbols": len(g)}
    return report


def _self_test():
    tmp = Path(tempfile.mkdtemp(prefix="fgamma-"))
    gp = tmp / ("gamma-state_test_" + uuid.uuid4().hex + ".json")
    _atomic_write_json(gp, {"Gamma": ["read_file", "terminal"]})
    g = load_gamma(gp)
    assert "read_file" in g
    assert filter_call({"name": "read_file", "args": {}}, g)["ok"] is True
    assert filter_call({"name": "nope"}, g)["ok"] is False
    assert filter_call({"name": "x"}, set())["status"] == "insufficient_data"
    print("[filter-tool-schema-by-gamma] --self-test PASS")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print("[filter-tool-schema-by-gamma] --self-test FAIL:", exc)
            return 1
    print(json.dumps(run(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
