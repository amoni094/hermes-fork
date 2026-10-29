#!/usr/bin/env python3
"""Add episode DAG and step snapshot tables to lifecycle.db (idempotent)."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import sqlite3
import sys

LIFECYCLE_DB = Path("/var/home/rainbow/.hermes/memory-facts/lifecycle.db")

DDL = (
    """CREATE TABLE IF NOT EXISTS episode_dag_edges(
      edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
      parent_episode_id TEXT NOT NULL,
      child_episode_id TEXT NOT NULL,
      edge_type TEXT DEFAULT 'spawn',
      created_at TEXT DEFAULT (datetime('now')))""",
    """CREATE TABLE IF NOT EXISTS step_state_snapshots(
      snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
      episode_id TEXT NOT NULL,
      step_num INTEGER NOT NULL,
      state_json TEXT,
      timestamp TEXT DEFAULT (datetime('now')))""",
    """CREATE TABLE IF NOT EXISTS cbf_log(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      raw_signal REAL,
      safe_signal REAL,
      constrained INTEGER DEFAULT 0,
      emergency_stop INTEGER DEFAULT 0)""",
)


def apply_schema(db_path: Path) -> list:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        for stmt in DDL:
            cur.execute(stmt)
        conn.commit()
        names = [
            r[0]
            for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1"
            ).fetchall()
        ]
        return names
    finally:
        conn.close()


def table_columns(db_path: Path, table: str) -> list:
    conn = sqlite3.connect(str(db_path))
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(%s)" % table).fetchall()]
        return cols
    finally:
        conn.close()


def self_test() -> dict:
    p = Path("/tmp/test-lifecycle.db")
    try:
        if p.exists():
            p.unlink()
        names = apply_schema(p)
        assert "episode_dag_edges" in names, names
        assert "step_state_snapshots" in names, names
        ecols = table_columns(p, "episode_dag_edges")
        scols = table_columns(p, "step_state_snapshots")
        for c in ("edge_id", "parent_episode_id", "child_episode_id", "edge_type", "created_at"):
            assert c in ecols, ecols
        for c in ("snapshot_id", "episode_id", "step_num", "state_json", "timestamp"):
            assert c in scols, scols
        # idempotent
        apply_schema(p)
        out = {"self_test": "PASS", "tables": names, "edge_cols": ecols, "snap_cols": scols}
        return out
    finally:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--db", default=str(LIFECYCLE_DB))
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r.get("self_test") == "PASS" else 1)
    names = apply_schema(Path(args.db))
    print(json.dumps({"ok": True, "db": args.db, "tables": names}, indent=2))


if __name__ == "__main__":
    main()
