#!/usr/bin/env python3
"""Log delegation episode outcomes to lifecycle.db and jsonl."""
from __future__ import annotations

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone

CACHE = _hermes_root / 'cache'
OUT_JSONL = CACHE / 'delegation-outcomes.jsonl'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_outcome(episode_id, subtask_count, success_rate, flags='[]', token_cost=0,
                db_path=None, jsonl_path=None) -> dict:
    ts = _now()
    db_path = Path(db_path) if db_path is not None else LIFECYCLE_DB
    jsonl_path = Path(jsonl_path) if jsonl_path is not None else OUT_JSONL
    audit_flags = flags if isinstance(flags, str) else json.dumps(flags)
    rec = {
        'ts': ts,
        'episode_id': str(episode_id),
        'subtask_count': int(subtask_count),
        'success_rate': float(success_rate),
        'audit_flags': audit_flags,
        'token_cost_estimate': int(token_cost or 0),
        'quality_proxy': float(success_rate),
    }
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            'INSERT INTO delegation_audit(ts, episode_id, subtask_count, success_rate, audit_flags) '
            'VALUES (?,?,?,?,?)',
            (ts, rec['episode_id'], rec['subtask_count'], rec['success_rate'], audit_flags),
        )
        conn.commit()
    finally:
        conn.close()
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with open(jsonl_path, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(rec) + '\n')
    return rec


def _self_test() -> int:
    import shutil
    td = Path(tempfile.mkdtemp(prefix='dol-%s-' % uuid.uuid4().hex[:8]))
    try:
        db = td / 'lifecycle.db'
        conn = sqlite3.connect(str(db))
        conn.execute(
            'CREATE TABLE delegation_audit ('
            'id INTEGER PRIMARY KEY, ts TEXT, episode_id TEXT, '
            'subtask_count INTEGER, success_rate REAL, audit_flags TEXT)'
        )
        conn.commit()
        conn.close()
        jsonl = td / 'delegation-outcomes.jsonl'
        rec = log_outcome(
            episode_id='ep-test',
            subtask_count=3,
            success_rate=0.8,
            flags='[]',
            token_cost=12,
            db_path=db,
            jsonl_path=jsonl,
        )
        conn = sqlite3.connect(str(db))
        rows = conn.execute('SELECT episode_id, subtask_count, success_rate FROM delegation_audit').fetchall()
        conn.close()
        assert len(rows) == 1, rows
        assert rows[0][0] == 'ep-test'
        assert rows[0][1] == 3
        assert abs(rows[0][2] - 0.8) < 1e-9
        lines = jsonl.read_text(encoding='utf-8').splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed['episode_id'] == 'ep-test'
        assert parsed['token_cost_estimate'] == 12
        assert abs(parsed['quality_proxy'] - 0.8) < 1e-9
        print('[delegate-outcome-logger] --self-test PASS')
        return 0
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--episode-id')
    ap.add_argument('--subtask-count', type=int)
    ap.add_argument('--success-rate', type=float)
    ap.add_argument('--flags', default='[]')
    ap.add_argument('--token-cost', type=int, default=0)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print('[delegate-outcome-logger] --self-test FAIL: %s' % exc)
            sys.exit(1)
    try:
        if not args.episode_id or args.subtask_count is None or args.success_rate is None:
            print(json.dumps({'status': 'error', 'reason': 'missing required args'}))
            return
        rec = log_outcome(
            episode_id=args.episode_id,
            subtask_count=args.subtask_count,
            success_rate=args.success_rate,
            flags=args.flags,
            token_cost=args.token_cost,
        )
        print(json.dumps(rec))
    except Exception:
        pass


if __name__ == '__main__':
    main()
