#!/usr/bin/env python3
"""MeshHeal data pump: backfill tool_review_log from delegation_audit.

Inserts scored rows (up to 300 per run) for audit episodes that have no
matching tool_review_log session_id. Stdlib only. INSERT-only.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC

LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'
BATCH = 300


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def backfill(db_path: Path, limit: int = BATCH) -> dict:
    if not db_path.exists():
        return {'status': 'insufficient_data', 'reason': 'missing_db', 'inserted': 0}
    conn = None
    inserted = 0
    try:
        conn = _connect(db_path)
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'delegation_audit' not in tabs or 'tool_review_log' not in tabs:
            return {'status': 'insufficient_data', 'reason': 'missing_tables', 'inserted': 0}
        rows = conn.execute(
            'SELECT d.id, d.ts, d.episode_id, d.subtask_count, d.success_rate, d.audit_flags '
            'FROM delegation_audit d '
            'WHERE NOT EXISTS (SELECT 1 FROM tool_review_log t WHERE t.session_id = d.episode_id) '
            'ORDER BY d.id LIMIT ?',
            (int(limit),),
        ).fetchall()
        if not rows:
            n = conn.execute('SELECT COUNT(*) FROM tool_review_log').fetchone()[0]
            return {'status': 'ok', 'inserted': 0, 'reason': 'caught_up', 'tool_review_log_rows': int(n)}
        for _id, ts, episode_id, subtask_count, success_rate, audit_flags in rows:
            try:
                score = float(success_rate) if success_rate is not None else 0.0
            except (TypeError, ValueError):
                score = 0.0
            if score != score:
                score = 0.0
            score = max(score, 0.0)
            score = min(score, 1.0)
            outcome = 'ok' if score >= 1.0 else ('partial' if score > 0.0 else 'fail')
            notes = json.dumps({
                'source': 'delegation_audit',
                'audit_id': _id,
                'subtask_count': subtask_count,
                'audit_flags': audit_flags or '',
            })
            conn.execute(
                'INSERT INTO tool_review_log (ts, session_id, tool_name, latency_ms, outcome, score, notes) '
                'VALUES (?,?,?,?,?,?,?)',
                (ts or _now(), str(episode_id or ''), 'delegate_task', None, outcome, score, notes),
            )
            inserted += 1
        conn.commit()
        n = conn.execute('SELECT COUNT(*) FROM tool_review_log').fetchone()[0]
        return {'status': 'ok', 'inserted': inserted, 'tool_review_log_rows': int(n)}
    except sqlite3.Error as exc:
        return {'status': 'error', 'reason': str(exc), 'inserted': inserted}
    finally:
        if conn is not None:
            conn.close()


def _self_test() -> int:
    td = Path(tempfile.mkdtemp(prefix='trs-'))
    try:
        db = td / 'lc.db'
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute(
            'CREATE TABLE delegation_audit (id INTEGER PRIMARY KEY, ts TEXT, episode_id TEXT, '
            'subtask_count INTEGER, success_rate REAL, audit_flags TEXT)'
        )
        conn.execute(
            'CREATE TABLE tool_review_log (id INTEGER PRIMARY KEY, ts TEXT, session_id TEXT, '
            'tool_name TEXT, latency_ms REAL, outcome TEXT, score REAL, notes TEXT)'
        )
        conn.execute(
            'INSERT INTO delegation_audit (ts, episode_id, subtask_count, success_rate, audit_flags) '
            'VALUES (?,?,?,?,?)',
            (_now(), 'ep-synth-' + uuid.uuid4().hex[:8], 2, 1.0, ''),
        )
        conn.commit()
        conn.close()
        r = backfill(db, limit=300)
        assert r.get('inserted', 0) > 0, r
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        n = conn.execute('SELECT COUNT(*) FROM tool_review_log').fetchone()[0]
        conn.close()
        assert n > 0, n
        r2 = backfill(db, limit=300)
        assert r2.get('inserted') == 0, r2
        missing = backfill(td / 'nope.db')
        assert missing.get('status') == 'insufficient_data'
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    print('[tool-review-scorer] --self-test PASS')
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--db', default=str(LIFECYCLE_DB))
    ap.add_argument('--limit', type=int, default=BATCH)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[tool-review-scorer] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = backfill(Path(args.db), limit=int(args.limit))
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
