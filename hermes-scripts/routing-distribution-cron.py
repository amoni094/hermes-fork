#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env) if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    cur = p
    for _ in range(4):
        if (cur / "hermes-scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return p


_hermes_base = _hermes_home()
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)

"""Daily classifier distribution over recent user messages."""

import importlib.util
import sqlite3
import sys
import time
from collections import Counter
from datetime import UTC, datetime


TIERS = ("fast", "math", "longctx", "tooluse", "reason", "elite")


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _db() -> Path:
    env = os.environ.get("ROUTING_METRICS_DB", "").strip()
    if env:
        return Path(env)
    return _hermes_root / "state.db"


def _user_messages(days: int = 7) -> list[str]:
    path = _db()
    cutoff = time.time() - days * 86400
    conn = sqlite3.connect(str(path), timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=5000")
        rows = conn.execute(
            "SELECT content FROM messages "
            "WHERE role = 'user' AND timestamp >= ? AND content IS NOT NULL AND content != '' "
            "AND COALESCE(active, 1) = 1",
            (cutoff,),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for (content,) in rows:
        text = str(content or "").strip()
        if not text:
            continue
        if text.startswith("[CONTEXT COMPACTION") or text.startswith("[STILL IN PROGRESS"):
            continue
        out.append(text[:500])
    return out


def main() -> int:
    ts = _now_iso()
    clf = _load("model_tier_classifier_dist", _hermes_base / "hermes-scripts" / "model-tier-classifier.py")
    queries = _user_messages(7)
    counts: Counter[str] = Counter()
    for q in queries:
        try:
            d = clf.classify({"query": q, "turn_index": 0})
        except Exception:
            d = {}
        tier = str((d or {}).get("tier") or "unknown")
        counts[tier] += 1
    n = len(queries)
    pct = {t: (100.0 * counts.get(t, 0) / n) if n else 0.0 for t in TIERS}

    alerts = []
    if pct["fast"] > 55:
        alerts.append("ALERT: routing too aggressive (cost OK but check accuracy)")
        print("ALERT: routing too aggressive (cost OK but check accuracy)")
    if pct["reason"] < 30:
        alerts.append("ALERT: reason tier underused")
        print("ALERT: reason tier underused")
    if pct["elite"] > 20:
        alerts.append("ALERT: elite tier overused (cost spike)")
        print("ALERT: elite tier overused (cost spike)")
    if pct["elite"] < 1:
        alerts.append("ALERT: elite tier never firing (security/audit queries not routing)")
        print("ALERT: elite tier never firing (security/audit queries not routing)")

    payload = {
        "ts": ts,
        "n": n,
        "counts": dict(counts),
        "pct": pct,
        "alerts": alerts,
    }
    try:
        mdb = _load("routing_metrics_db", _hermes_base / "hermes-scripts" / "routing-metrics-db.py")
        mdb.write_metric("tier_distribution", payload, source="cron")
    except Exception as exc:
        print("WARN: routing_metrics write failed:", type(exc).__name__, file=sys.stderr)

    print(
        f"TIER_DIST ts={ts} fast={pct['fast']:.1f}% math={pct['math']:.1f}% "
        f"reason={pct['reason']:.1f}% elite={pct['elite']:.1f}% (N={n} queries)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
