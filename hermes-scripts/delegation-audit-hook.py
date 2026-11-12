#!/usr/bin/env python3
"""Log delegate_task pre-call audits to JSONL and lifecycle.db.

Plugin-compatible: register(ctx) + on_post_tool_call. Fail-open.
Pre-call logging: success_rate is NULL until a later outcome writer fills it.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)
_true_home = _hermes_base
if _true_home.parent.name == 'profiles':
    _true_home = _true_home.parent.parent

import argparse
import fcntl
import json
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone

CACHE = _hermes_root / 'cache'
OUT_JSONL = CACHE / 'delegation-outcomes.jsonl'
LIFECYCLE_DB = _true_home / 'memory-facts' / 'lifecycle.db'

DDL = (
    'CREATE TABLE IF NOT EXISTS delegation_audit ('
    'id INTEGER PRIMARY KEY, ts TEXT, episode_id TEXT, '
    'subtask_count INTEGER, success_rate REAL, audit_flags TEXT)'
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _subtask_count(args) -> int:
    if not isinstance(args, dict):
        if isinstance(args, str) and args.strip():
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                return 0
        else:
            return 0
    if not isinstance(args, dict):
        return 0
    tasks = args.get('tasks')
    if isinstance(tasks, list):
        return len(tasks)
    if isinstance(tasks, dict):
        return len(tasks)
    if tasks:
        return 1
    return 0


def _append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    line = json.dumps(rec) + '\n'
    with open(str(lock), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            with open(str(path), 'a', encoding='utf-8') as fh:
                fh.write(line)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def log_pre_call(episode_id, subtask_count, db_path=None, jsonl_path=None,
                 audit_flags=None) -> dict:
    ts = _now()
    db_path = Path(db_path) if db_path is not None else LIFECYCLE_DB
    jsonl_path = Path(jsonl_path) if jsonl_path is not None else OUT_JSONL
    flags = audit_flags if audit_flags is not None else '["pre_call"]'
    if not isinstance(flags, str):
        flags = json.dumps(flags)
    rec = {
        'ts': ts,
        'episode_id': str(episode_id or ''),
        'subtask_count': int(subtask_count),
        'success_rate': None,
        'audit_flags': flags,
    }
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        try:
            conn.execute(DDL)
            conn.execute(
                'INSERT INTO delegation_audit(ts, episode_id, subtask_count, '
                'success_rate, audit_flags) VALUES (?,?,?,?,?)',
                (ts, rec['episode_id'], rec['subtask_count'], None, flags),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass
    try:
        _append_jsonl(jsonl_path, rec)
    except Exception:
        pass
    return rec


def on_post_tool_call(tool_name='', args=None, result=None, session_id='',
                      **kwargs):
    try:
        if tool_name != 'delegate_task':
            return None
        n = _subtask_count(args)
        episode_id = str(session_id or kwargs.get('task_id') or '')
        return log_pre_call(episode_id, n)
    except Exception:
        return None


def register(ctx) -> None:
    try:
        ctx.register_hook('post_tool_call', on_post_tool_call)
    except Exception:
        pass


def _self_test() -> int:
    import shutil
    td = Path(tempfile.mkdtemp(prefix='dah-%s-' % uuid.uuid4().hex[:8]))
    try:
        db = td / 'lifecycle.db'
        jsonl = td / 'delegation-outcomes.jsonl'
        rec = log_pre_call(
            episode_id='ep-test',
            subtask_count=4,
            db_path=db,
            jsonl_path=jsonl,
        )
        assert rec['success_rate'] is None, rec
        conn = sqlite3.connect(str(db))
        try:
            rows = conn.execute(
                'SELECT episode_id, subtask_count, success_rate, audit_flags '
                'FROM delegation_audit'
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 1, rows
        assert rows[0][0] == 'ep-test'
        assert rows[0][1] == 4
        assert rows[0][2] is None
        lines = jsonl.read_text(encoding='utf-8').splitlines()
        assert len(lines) == 1, lines
        parsed = json.loads(lines[0])
        assert parsed['episode_id'] == 'ep-test'
        assert parsed['subtask_count'] == 4
        assert parsed['success_rate'] is None
        n = _subtask_count({'tasks': [{'a': 1}, {'b': 2}, {'c': 3}]})
        assert n == 3, n
        n0 = _subtask_count(None)
        assert n0 == 0
        n_bad = _subtask_count('not-json')
        assert n_bad == 0
        out = on_post_tool_call('read_file', {'path': 'x'}, None, 'sid')
        assert out is None
        print('[delegation-audit-hook] --self-test PASS')
        return 0
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print('[delegation-audit-hook] --self-test FAIL: %s' % exc)
            sys.exit(1)
    print(json.dumps({'ok': True, 'mode': 'idle', 'hint': 'use as post_tool_call hook'}))


if __name__ == '__main__':
    main()
