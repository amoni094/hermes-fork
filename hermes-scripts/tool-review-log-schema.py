#!/usr/bin/env python3
"""Create tool_review_log and anytime_eval_log tables in lifecycle.db."""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_true_home = _hermes_base
if _true_home.parent.name == 'profiles':
    _true_home = _true_home.parent.parent

import argparse
import json
import sqlite3
import sys
import tempfile
import uuid

LIFECYCLE_DB = _true_home / 'memory-facts' / 'lifecycle.db'

DDL = (
    """CREATE TABLE IF NOT EXISTS tool_review_log (
      id INTEGER PRIMARY KEY, ts TEXT, session_id TEXT, tool_name TEXT,
      latency_ms REAL, outcome TEXT, score REAL, notes TEXT)""",
    """CREATE TABLE IF NOT EXISTS anytime_eval_log (
      id INTEGER PRIMARY KEY, ts TEXT, session_id TEXT, skill_id TEXT,
      eval_score REAL, quality_tier TEXT)""",
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


def self_test() -> dict:
    p = Path(tempfile.gettempdir()) / ('test-tool-review-%s.db' % uuid.uuid4().hex)
    try:
        if p.exists():
            p.unlink()
        names = apply_schema(p)
        assert 'tool_review_log' in names, names
        assert 'anytime_eval_log' in names, names
        conn = sqlite3.connect(str(p), timeout=30)
        try:
            conn.execute(
                'INSERT INTO tool_review_log(ts, session_id, tool_name, '
                'latency_ms, outcome, score, notes) VALUES (?,?,?,?,?,?,?)',
                ('2026-01-01T00:00:00+00:00', 's1', 'read_file', 12.5, 'ok', 0.9, 'n'),
            )
            conn.execute(
                'INSERT INTO anytime_eval_log(ts, session_id, skill_id, '
                'eval_score, quality_tier) VALUES (?,?,?,?,?)',
                ('2026-01-01T00:00:00+00:00', 's1', 'skill-x', 0.7, 'mid'),
            )
            conn.commit()
            tr = conn.execute('SELECT tool_name, score FROM tool_review_log').fetchall()
            ae = conn.execute('SELECT skill_id, eval_score FROM anytime_eval_log').fetchall()
        finally:
            conn.close()
        assert tr == [('read_file', 0.9)], tr
        assert ae[0][0] == 'skill-x' and abs(ae[0][1] - 0.7) < 1e-9, ae
        apply_schema(p)
        return {'self_test': 'PASS', 'tables': names}
    finally:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--db', default=str(LIFECYCLE_DB))
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        print('[tool-review-log-schema] --self-test PASS')
        sys.exit(0 if r.get('self_test') == 'PASS' else 1)
    if not args.apply:
        print(json.dumps({'ok': False, 'error': 'pass --apply or --self-test'}))
        sys.exit(2)
    names = apply_schema(Path(args.db))
    print(json.dumps({'ok': True, 'db': args.db, 'tables': names}, indent=2))


if __name__ == '__main__':
    main()
