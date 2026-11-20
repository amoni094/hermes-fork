#!/usr/bin/env python3
"""Turn-level behavior stats collector.

Records per-turn behavior into anytime_eval_log and turn-behavior.jsonl
for conformal martingale change detection. Fail-open. Stdlib only.
"""
from __future__ import annotations

import os
from pathlib import Path


def _hermes_home() -> Path:
    """True ~/.hermes: strip a trailing profiles/<name> suffix."""
    env = os.environ.get('HERMES_HOME', '').strip()
    p = Path(env) if env else Path.home() / '.hermes'
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


def _profile_name() -> str:
    profile = os.environ.get('HERMES_PROFILE', 'fork').strip()
    if profile:
        return profile
    raw = os.environ.get('HERMES_HOME', '').strip()
    if raw:
        p = Path(raw)
        if p.parent.name == 'profiles':
            return p.name
    if (_hermes_home() / 'profiles' / 'fork').exists():
        return 'fork'
    return ''


def _hermes_root() -> Path:
    base = _hermes_home()
    profile = _profile_name()
    return (base / 'profiles' / profile) if profile else base


def _paths() -> dict:
    base = _hermes_home()
    root = _hermes_root()
    cache = root / 'cache'
    return {
        'base': base,
        'root': root,
        'jsonl': cache / 'turn-behavior.jsonl',
        'state': cache / 'turn-behavior-collector-state.json',
        'db': base / 'memory-facts' / 'lifecycle.db',
    }


_hermes_base = _hermes_home()
_hermes_profile = _profile_name()
_hermes_root_path = _hermes_root()

import argparse
import fcntl
import json
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC

_P0 = _paths()
CACHE = _P0['root'] / 'cache'
OUT_PATH = _P0['jsonl']
LIFECYCLE_DB = _P0['db']
STATE_PATH = _P0['state']

# session -> set of tool names (process-local entropy proxy)
_SESSION_TOOLS: dict = {}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            with open(str(path), 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, default=str) + '\n')
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def _ensure_log_table(conn) -> bool:
    tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return 'anytime_eval_log' in tabs


def record_turn(tool_name: str = '', result=None, session_id: str = '', turn_id: str = '',
                db_path: Path | None = None, jsonl_path: Path | None = None, **kwargs) -> dict | None:
    sid = str(session_id or '')
    tname = str(tool_name or '')
    tools = _SESSION_TOOLS.setdefault(sid, set())
    if tname:
        tools.add(tname)
    n_tools = max(1, len(tools))
    entropy = 1.0 / float(n_tools)
    success = 1.0 if result is not None else 0.0
    token_estimate = len(str(result)) // 4 if result is not None else 0
    rec = {
        'ts': _now(),
        'session_id': sid,
        'turn_id': str(turn_id or kwargs.get('tool_call_id') or ''),
        'tool_name': tname,
        'skill_entropy': float(entropy),
        'success': bool(result is not None),
        'token_estimate': int(token_estimate),
    }
    live = _paths()
    _append_jsonl(Path(jsonl_path) if jsonl_path is not None else live['jsonl'], rec)
    dbp = Path(db_path) if db_path is not None else live['db']
    if dbp.exists():
        conn = None
        try:
            conn = _connect(dbp)
            if _ensure_log_table(conn):
                meta = json.dumps({
                    'turn_id': rec['turn_id'],
                    'skill_entropy': rec['skill_entropy'],
                    'token_estimate': rec['token_estimate'],
                    'success': rec['success'],
                })
                conn.execute(
                    'INSERT INTO anytime_eval_log (ts, session_id, skill_id, eval_score, quality_tier) '
                    'VALUES (?,?,?,?,?)',
                    (rec['ts'], sid, tname, float(success), meta),
                )
                conn.commit()
        except sqlite3.Error:
            pass
        finally:
            if conn is not None:
                conn.close()
    return rec


def on_post_tool_call(tool_name: str = '', args=None, result=None, session_id: str = '',
                      turn_id: str = '', **kwargs):
    try:
        return record_turn(
            tool_name=tool_name, result=result, session_id=session_id,
            turn_id=turn_id or str(kwargs.get('tool_call_id') or ''), **kwargs
        )
    except Exception:
        return None


def backfill(db_path: Path, jsonl_path: Path, limit: int = 200) -> dict:
    """Batch: copy recent anytime_eval_log rows into jsonl if jsonl is behind (idempotent skip)."""
    if not db_path.exists():
        return {'status': 'insufficient_data', 'reason': 'missing_db', 'written': 0}
    conn = None
    written = 0
    try:
        conn = _connect(db_path)
        if not _ensure_log_table(conn):
            return {'status': 'insufficient_data', 'reason': 'no_table', 'written': 0}
        n = conn.execute('SELECT COUNT(*) FROM anytime_eval_log').fetchone()[0]
        rows = conn.execute(
            'SELECT ts, session_id, skill_id, eval_score, quality_tier '
            'FROM anytime_eval_log ORDER BY id DESC LIMIT ?',
            (int(limit),),
        ).fetchall()
        # daily backfill is a no-op pump when hooks already write; just report counts
        return {'status': 'ok', 'log_rows': int(n), 'sampled': len(rows), 'written': written}
    except sqlite3.Error as exc:
        return {'status': 'error', 'reason': str(exc), 'written': 0}
    finally:
        if conn is not None:
            conn.close()


def _self_test() -> int:
    old_home = os.environ.get('HERMES_HOME')
    old_prof = os.environ.get('HERMES_PROFILE')
    try:
        os.environ['HERMES_HOME'] = str(Path.home() / '.hermes' / 'profiles' / 'fork')
        os.environ.pop('HERMES_PROFILE', None)
        assert _hermes_home() == Path.home() / '.hermes', _hermes_home()
        assert _profile_name() == 'fork', _profile_name()
        os.environ['HERMES_HOME'] = str(Path.home() / '.hermes')
        os.environ['HERMES_PROFILE'] = 'fork'
        assert _hermes_home() == Path.home() / '.hermes'
        assert _profile_name() == 'fork'
    finally:
        if old_home is None:
            os.environ.pop('HERMES_HOME', None)
        else:
            os.environ['HERMES_HOME'] = old_home
        if old_prof is None:
            os.environ.pop('HERMES_PROFILE', None)
        else:
            os.environ['HERMES_PROFILE'] = old_prof

    td = Path(tempfile.mkdtemp(prefix='tbc-'))
    try:
        db = td / 'lc.db'
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute(
            'CREATE TABLE anytime_eval_log (id INTEGER PRIMARY KEY, ts TEXT, session_id TEXT, '
            'skill_id TEXT, eval_score REAL, quality_tier TEXT)'
        )
        conn.commit()
        conn.close()
        out = td / ('turn-behavior_test_' + uuid.uuid4().hex + '.jsonl')
        rec = record_turn(
            tool_name='terminal', result={'ok': True}, session_id='s-test',
            turn_id='t1', db_path=db, jsonl_path=out,
        )
        assert rec is not None
        assert rec['success'] is True
        assert abs(rec['skill_entropy'] - 1.0) < 1e-9
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        n = conn.execute('SELECT COUNT(*) FROM anytime_eval_log').fetchone()[0]
        conn.close()
        assert n == 1, n
        lines = out.read_text(encoding='utf-8').splitlines()
        assert len(lines) == 1
        rec2 = record_turn(
            tool_name='read_file', result=None, session_id='s-test',
            turn_id='t2', db_path=db, jsonl_path=out,
        )
        assert rec2['success'] is False
        assert abs(rec2['skill_entropy'] - 0.5) < 1e-9
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        n = conn.execute('SELECT COUNT(*) FROM anytime_eval_log').fetchone()[0]
        conn.close()
        assert n == 2, n
        bf = backfill(td / 'nope.db', out)
        assert bf.get('status') == 'insufficient_data'
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    print('[turn-behavior-collector] --self-test PASS')
    return 0


def main() -> None:
    live = _paths()
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--db', default=str(live['db']))
    ap.add_argument('--out', default=str(live['jsonl']))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[turn-behavior-collector] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = backfill(Path(args.db), Path(args.out))
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
