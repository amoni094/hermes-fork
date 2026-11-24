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

import json
import sqlite3
from typing import Any


DDL = """
CREATE TABLE IF NOT EXISTS routing_metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    metric      TEXT NOT NULL,
    value_json  TEXT NOT NULL,
    source      TEXT
);
CREATE INDEX IF NOT EXISTS idx_routing_metrics_metric_ts ON routing_metrics(metric, ts);
"""


def db_path() -> Path:
    env = os.environ.get("ROUTING_METRICS_DB", "").strip()
    if env:
        return Path(env)
    return _hermes_root / "state.db"


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
    except sqlite3.Error:
        pass
    conn.executescript(DDL)
    return conn


def write_metric(metric: str, value: dict, source: str = "cron") -> int:
    payload = json.dumps(value, ensure_ascii=False, default=str)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "INSERT INTO routing_metrics (metric, value_json, source) VALUES (?, ?, ?)",
            (str(metric), payload, str(source or "cron")),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    raw = d.get("value_json")
    try:
        d["value"] = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        d["value"] = {}
    return d


def read_latest(metric: str, n: int = 10) -> list[dict]:
    n = max(1, int(n or 10))
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, ts, metric, value_json, source FROM routing_metrics "
            "WHERE metric = ? ORDER BY id DESC LIMIT ?",
            (str(metric), n),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def read_range(metric: str, since_iso: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, ts, metric, value_json, source FROM routing_metrics "
            "WHERE metric = ? AND ts >= ? ORDER BY ts ASC, id ASC",
            (str(metric), str(since_iso)),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    rows = read_latest("precision_audit", 1)
    print(rows)
