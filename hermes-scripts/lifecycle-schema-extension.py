#!/usr/bin/env python3
"""Add episode DAG and step snapshot tables to lifecycle.db (idempotent)."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import sqlite3
import sys

LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'

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
    """CREATE TABLE IF NOT EXISTS anytime_eval_runs (
      id INTEGER PRIMARY KEY, ts TEXT, arm_id TEXT,
      mean_score REAL, spi_score REAL, n_queries INTEGER,
      reference_frozen_at INTEGER)""",
    """CREATE TABLE IF NOT EXISTS skill_kl_history (
      id INTEGER PRIMARY KEY, ts TEXT, skill_name TEXT,
      posterior_prob REAL, prior_prob REAL, kl_contrib REAL, net_score REAL)""",
    """CREATE TABLE IF NOT EXISTS output_violations (
      id INTEGER PRIMARY KEY, ts TEXT, output_hash TEXT, violation_type TEXT)""",
    """CREATE TABLE IF NOT EXISTS hallucination_events (
      id INTEGER PRIMARY KEY, ts TEXT, composite_ue REAL, high_ue INTEGER, query_hash TEXT)""",
    """CREATE TABLE IF NOT EXISTS trajectory_audits (
      id INTEGER PRIMARY KEY, ts TEXT, episode_id TEXT, step_count INTEGER, quality_score REAL)""",
    """CREATE TABLE IF NOT EXISTS cbf_log(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      raw_signal REAL,
      safe_signal REAL,
      constrained INTEGER DEFAULT 0,
      emergency_stop INTEGER DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS delegation_audit (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      episode_id TEXT,
      subtask_count INTEGER,
      success_rate REAL,
      audit_flags TEXT)""",
)


def apply_schema(db_path: Path) -> list:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
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
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        if table not in ("episode_dag_edges", "step_state_snapshots", "anytime_eval_runs", "skill_kl_history", "output_violations", "hallucination_events", "trajectory_audits", "cbf_log", "delegation_audit"):
            raise ValueError("unknown table")
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        return cols
    finally:
        conn.close()


def self_test() -> dict:
    import tempfile, uuid
    p = Path(tempfile.gettempdir()) / (f"test-lifecycle-{uuid.uuid4().hex}.db")
    try:
        if p.exists():
            p.unlink()
        names = apply_schema(p)
        assert "episode_dag_edges" in names, names
        assert "step_state_snapshots" in names, names
        assert "cbf_log" in names, names
        assert "delegation_audit" in names, names
        ecols = table_columns(p, "episode_dag_edges")
        scols = table_columns(p, "step_state_snapshots")
        ccols = table_columns(p, "cbf_log")
        for c in ("edge_id", "parent_episode_id", "child_episode_id", "edge_type", "created_at"):
            assert c in ecols, ecols
        for c in ("snapshot_id", "episode_id", "step_num", "state_json", "timestamp"):
            assert c in scols, scols
        for c in ("id", "ts", "raw_signal", "safe_signal", "constrained", "emergency_stop"):
            assert c in ccols, ccols
        # idempotent
        apply_schema(p)
        out = {"self_test": "PASS", "tables": names, "edge_cols": ecols, "snap_cols": scols, "cbf_cols": ccols}
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
    ap.add_argument("--apply", action="store_true")
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
