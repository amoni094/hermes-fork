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

"""Weekly implicit routing outcome signals from state.db / ATOF."""

import importlib.util
import json
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from statistics import mean


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


def _atof_escalation(days: int = 7) -> tuple[int, int] | None:
    """Return (escalated_turns, total_turns) if ATOF files carry tier fields."""
    cutoff = time.time() - days * 86400
    roots = [
        _hermes_root / "atof",
        _hermes_root / "cache" / "atof",
        _hermes_base / "relay",
    ]
    files = []
    for root in roots:
        if not root.exists():
            continue
        try:
            files.extend(root.rglob("*atof*.jsonl"))
            files.extend(root.rglob("events.jsonl"))
        except OSError:
            continue
    total = 0
    esc = 0
    seen = False
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            data = rec.get("data") if isinstance(rec.get("data"), dict) else rec
            if not isinstance(data, dict):
                continue
            if "escalated" not in data and "tier" not in data:
                continue
            ts = rec.get("ts") or rec.get("timestamp") or 0
            try:
                ts_f = float(ts)
            except (TypeError, ValueError):
                ts_f = 0.0
            if ts_f > 1e12:
                ts_f = ts_f / 1000.0
            if ts_f and ts_f < cutoff:
                continue
            seen = True
            total += 1
            if data.get("escalated") is True or data.get("escalated") == 1:
                esc += 1
    if not seen:
        return None
    return esc, total


def _model_switch_rate(conn: sqlite3.Connection, cutoff: float) -> float:
    rows = conn.execute(
        "SELECT session_id, COUNT(DISTINCT model) AS n "
        "FROM session_model_usage "
        "WHERE COALESCE(last_seen, first_seen, 0) >= ? "
        "GROUP BY session_id",
        (cutoff,),
    ).fetchall()
    if not rows:
        return 0.0
    switched = sum(1 for _, n in rows if int(n or 0) > 1)
    return switched / len(rows)


def _session_lengths(conn: sqlite3.Connection, cutoff: float, classify) -> dict[str, float]:
    rows = conn.execute(
        "SELECT session_id, content, timestamp FROM messages "
        "WHERE role = 'user' AND timestamp >= ? AND content IS NOT NULL AND content != '' "
        "AND COALESCE(active, 1) = 1 "
        "ORDER BY session_id, timestamp ASC",
        (cutoff,),
    ).fetchall()
    first: dict[str, str] = {}
    counts: dict[str, int] = defaultdict(int)
    for sid, content, _ts in rows:
        counts[sid] += 1
        if sid not in first:
            first[sid] = str(content or "")[:500]
    buckets: dict[str, list[int]] = defaultdict(list)
    for sid, q in first.items():
        try:
            d = classify({"query": q, "turn_index": 0})
        except Exception:
            d = {}
        tier = str((d or {}).get("tier") or "unknown")
        buckets[tier].append(counts[sid])
    return {t: (mean(v) if v else 0.0) for t, v in buckets.items()}


def main() -> int:
    ts = _now_iso()
    cutoff = time.time() - 7 * 86400
    atof = _atof_escalation(7)
    source = "atof"
    conn = sqlite3.connect(str(_db()), timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=5000")
        if atof is None:
            source = "model_switch"
            esc_rate = _model_switch_rate(conn, cutoff)
        else:
            esc, total = atof
            esc_rate = (esc / total) if total else 0.0
        clf = _load(
            "model_tier_classifier_out",
            _hermes_base / "hermes-scripts" / "model-tier-classifier.py",
        )
        lengths = _session_lengths(conn, cutoff, clf.classify)
    finally:
        conn.close()

    if esc_rate > 0.15:
        print("ALERT: escalation_rate > 0.15 -> fast tier under-routing")

    payload = {
        "ts": ts,
        "escalation_rate": esc_rate,
        "escalation_source": source,
        "session_len": lengths,
        "fast_session_len": float(lengths.get("fast") or 0.0),
        "reason_session_len": float(lengths.get("reason") or 0.0),
        "elite_session_len": float(lengths.get("elite") or 0.0),
    }
    try:
        mdb = _load("routing_metrics_db", _hermes_base / "hermes-scripts" / "routing-metrics-db.py")
        mdb.write_metric("outcome_signals", payload, source="cron")
    except Exception as exc:
        print("WARN: routing_metrics write failed:", type(exc).__name__, file=sys.stderr)

    print(
        f"OUTCOME_SIGNALS ts={ts} escalation_est={esc_rate*100:.1f}% "
        f"fast_session_len={payload['fast_session_len']:.1f} "
        f"reason_session_len={payload['reason_session_len']:.1f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
