#!/usr/bin/env python3
"""Authority-at-commit-time: validate tool-call manifests before dispatch (shadow)."""
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

OUT_PATH = CACHE / "governance-validator-state.json"
POLICIES_PATH = CACHE / "policies.json"
PROPOSALS_PATH = CACHE / "proposals.json"

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


DEFAULT_POLICY = {
    "deny_unknown_tools": False,
    "stale_hours": 72,
    "blocked_tools": [],
    "require_ts": True,
}


def load_policy(path: Path) -> dict:
    if not path.exists():
        return dict(DEFAULT_POLICY)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(DEFAULT_POLICY)
        out = dict(DEFAULT_POLICY)
        out.update({k: data[k] for k in data if k in DEFAULT_POLICY})
        return out
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_POLICY)


def load_known_tools(db_path: Path) -> set:
    if not db_path.exists():
        return set()
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT tool_name FROM tool_review_log WHERE tool_name IS NOT NULL"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return {str(r[0]) for r in rows if r[0] and r[0] != "ue_blackbox"}


def parse_ts(ts):
    if not ts:
        return None
    s = str(ts).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def validate_manifest(m: dict, policy: dict, known: set, now=None):
    now = now or datetime.now(UTC)
    name = str(m.get("tool_name") or m.get("name") or "")
    reasons = []
    if not name:
        reasons.append("missing_name")
    if name in set(policy.get("blocked_tools") or []):
        reasons.append("blocked_tool")
    if policy.get("deny_unknown_tools") and name and name not in known:
        reasons.append("unknown_tool")
    ts = parse_ts(m.get("ts"))
    if policy.get("require_ts") and ts is None:
        reasons.append("missing_ts")
    elif ts is not None:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        age_h = (now - ts).total_seconds() / 3600.0
        if age_h > float(policy.get("stale_hours") or 72):
            reasons.append("stale_manifest")
    return {"name": name, "reject": bool(reasons), "reasons": reasons}


def load_recent_manifests(db_path: Path, limit=200):
    if not db_path.exists():
        return []
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT ts, tool_name, outcome FROM tool_review_log ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return [{"ts": ts, "tool_name": name, "outcome": outcome} for ts, name, outcome in rows]


def build_report(manifests, policy, known):
    if not manifests:
        return {
            "ts": _now(),
            "status": "insufficient_data",
            "n": 0,
            "rejection_rate": None,
            "rejected": 0,
        }
    decisions = [validate_manifest(m, policy, known) for m in manifests]
    rejected = sum(1 for d in decisions if d["reject"])
    n = len(decisions)
    return {
        "ts": _now(),
        "status": "ok",
        "n": n,
        "rejected": rejected,
        "rejection_rate": rejected / n if n else 0.0,
        "sample_rejects": [d for d in decisions if d["reject"]][:20],
        "policy": policy,
    }


def run(out_path=None, db_path=None, policy_path=None, proposals_path=None):
    dest = out_path or OUT_PATH
    db = db_path or LIFECYCLE_DB
    pol_p = policy_path or POLICIES_PATH
    prop_p = proposals_path or PROPOSALS_PATH
    try:
        policy = load_policy(pol_p)
        known = load_known_tools(db)
        manifests = load_recent_manifests(db)
        report = build_report(manifests, policy, known)
        _atomic_write_json(dest, report)
        # cache copies of policy snapshot + proposal summary (do not clobber live ledgers)
        try:
            if not pol_p.exists():
                _atomic_write_json(pol_p, policy)
        except Exception:
            pass
        try:
            _atomic_write_json(prop_p, {"ts": _now(), "n_manifests": report.get("n"), "rejection_rate": report.get("rejection_rate")})
        except Exception:
            pass
        return report
    except Exception as exc:
        err = {"ts": _now(), "status": "error", "error": str(exc), "n": 0}
        try:
            _atomic_write_json(dest, err)
        except Exception:
            pass
        return err


def _self_test():
    tmp = Path(tempfile.mkdtemp(prefix="govv-"))
    out = tmp / ("governance-validator-state_test_" + uuid.uuid4().hex + ".json")
    policy = dict(DEFAULT_POLICY)
    policy["blocked_tools"] = ["rm"]
    known = {"read_file"}
    now = datetime.now(UTC)
    d1 = validate_manifest({"tool_name": "rm", "ts": now.isoformat()}, policy, known, now=now)
    assert d1["reject"] is True
    d2 = validate_manifest({"tool_name": "read_file", "ts": now.isoformat()}, policy, known, now=now)
    assert d2["reject"] is False
    d3 = validate_manifest({"tool_name": "read_file"}, policy, known, now=now)
    assert d3["reject"] is True  # missing_ts
    empty = build_report([], policy, known)
    assert empty["status"] == "insufficient_data"
    r = run(out_path=out, db_path=tmp / "no.db", policy_path=tmp / "policies.json", proposals_path=tmp / "proposals.json")
    assert out.exists()
    json.loads(out.read_text())
    print("[governance-validator] --self-test PASS status={}".format(r.get("status")))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print("[governance-validator] --self-test FAIL:", exc)
            return 1
    report = run()
    print(json.dumps({"status": report.get("status"), "n": report.get("n"), "rejection_rate": report.get("rejection_rate")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
