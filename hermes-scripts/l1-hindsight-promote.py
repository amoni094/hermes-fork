#!/usr/bin/env python3
"""l1-hindsight-promote.py — Promote high-quality hindsight_events to staging.md.

Reads hindsight_events where quality >= 0.7 and created_at is after the
last promoted cursor, then appends one bullet per row to
memory-facts/staging.md. Incremental via cache/hindsight-promote-state.json.

Usage:
  HERMES_HOME=~/.hermes HERMES_PROFILE=fork python3 l1-hindsight-promote.py
  python3 l1-hindsight-promote.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import time
import traceback
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

QUALITY_MIN = 0.7
BUSY_TIMEOUT_MS = 8000


def _true_base(p: Path) -> Path:
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


def cache_dir() -> Path:
    d = _hermes_root / 'cache'
    d.mkdir(parents=True, exist_ok=True)
    return d


def state_path() -> Path:
    return cache_dir() / 'hindsight-promote-state.json'


def staging_path() -> Path:
    # Shared L1 staging consumed by the existing hindsight_retain cron.
    return _true_base(_hermes_base) / 'memory-facts' / 'staging.md'


def hindsight_db_path() -> Path:
    base = _true_base(_hermes_base)
    for cand in (
        _hermes_root / 'hindsight.db',
        base / 'hindsight.db',
        Path.home() / '.hermes' / 'hindsight.db',
    ):
        if cand.is_file():
            return cand
    return base / 'hindsight.db'


def _atomic_write_json(dest: Path, data: dict) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(tmp, dest)


def _log(msg: str) -> None:
    print(f'[l1-hindsight-promote] {msg}', file=sys.stderr)


def load_state() -> dict:
    p = state_path()
    default = {'last_promoted_ts': 0.0, 'last_promoted_id': 0}
    if not p.is_file():
        return default
    try:
        raw = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        _log(f'state unreadable, starting at 0: {exc}')
        return default
    if not isinstance(raw, dict):
        return default
    try:
        ts = float(raw.get('last_promoted_ts') or 0.0)
    except (TypeError, ValueError):
        ts = 0.0
    try:
        rid = int(raw.get('last_promoted_id') or 0)
    except (TypeError, ValueError):
        rid = 0
    return {'last_promoted_ts': ts, 'last_promoted_id': rid}


def save_state(state: dict) -> None:
    try:
        _atomic_write_json(state_path(), state)
    except OSError as exc:
        _log(f'state write failed (fail-open): {exc}')


def tool_name_from_payload(payload: str) -> str:
    if not payload:
        return 'unknown'
    try:
        obj = json.loads(payload)
    except (json.JSONDecodeError, TypeError, UnicodeError):
        return 'unknown'
    if not isinstance(obj, dict):
        return 'unknown'
    name = obj.get('tool_name')
    if name is None:
        return 'unknown'
    s = str(name).replace('\n', ' ').replace('\r', ' ')
    return s or 'unknown'


def format_bullet(tool_name: str, session_id, quality, created_at) -> str:
    sid = str(session_id or '').replace('\n', ' ').replace('\r', ' ')
    try:
        q = float(quality)
    except (TypeError, ValueError):
        q = 0.0
    try:
        ts = float(created_at)
    except (TypeError, ValueError):
        ts = 0.0
    return f'- [{tool_name}] session={sid} quality={q} ts={ts}'


def fetch_rows(con: sqlite3.Connection, last_ts: float, last_id: int) -> list[tuple]:
    # Cursor is (created_at, id) so equal timestamps are not skipped.
    sql = (
        'SELECT id, session_id, payload, quality, created_at '
        'FROM hindsight_events '
        'WHERE quality >= ? AND ('
        'created_at > ? OR (created_at = ? AND id > ?)'
        ') ORDER BY created_at ASC, id ASC'
    )
    return list(con.execute(sql, (QUALITY_MIN, last_ts, last_ts, last_id)))


def promote(db_path: Path | None = None, staging: Path | None = None) -> dict:
    t0 = time.monotonic()
    dbp = db_path or hindsight_db_path()
    dest = staging or staging_path()
    state = load_state()
    last_ts = float(state.get('last_promoted_ts') or 0.0)
    last_id = int(state.get('last_promoted_id') or 0)
    n_written = 0
    if not dbp.is_file():
        report = {
            'n_written': 0,
            'last_promoted_ts': last_ts,
            'last_promoted_id': last_id,
            'duration': round(time.monotonic() - t0, 4),
            'note': f'missing db {dbp}',
        }
        return report
    try:
        con = sqlite3.connect(f'file:{dbp}?mode=ro', uri=True, timeout=BUSY_TIMEOUT_MS / 1000.0)
        con.execute(f'PRAGMA busy_timeout={BUSY_TIMEOUT_MS}')
    except sqlite3.Error as exc:
        _log(f'db open failed (fail-open): {exc}')
        return {
            'n_written': 0,
            'last_promoted_ts': last_ts,
            'last_promoted_id': last_id,
            'duration': round(time.monotonic() - t0, 4),
            'error': str(exc),
        }
    try:
        try:
            rows = fetch_rows(con, last_ts, last_id)
        except sqlite3.Error as exc:
            _log(f'select failed (fail-open): {exc}')
            return {
                'n_written': 0,
                'last_promoted_ts': last_ts,
                'last_promoted_id': last_id,
                'duration': round(time.monotonic() - t0, 4),
                'error': str(exc),
            }
    finally:
        try:
            con.close()
        except sqlite3.Error:
            pass

    if not rows:
        return {
            'n_written': 0,
            'last_promoted_ts': last_ts,
            'last_promoted_id': last_id,
            'duration': round(time.monotonic() - t0, 4),
        }

    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    new_ts = last_ts
    new_id = last_id
    for rid, session_id, payload, quality, created_at in rows:
        try:
            name = tool_name_from_payload(payload if isinstance(payload, str) else json.dumps(payload, default=str))
            lines.append(format_bullet(name, session_id, quality, created_at))
            n_written += 1
            try:
                cts = float(created_at)
            except (TypeError, ValueError):
                cts = last_ts
            rid_i = int(rid)
            if cts > new_ts or (cts == new_ts and rid_i > new_id):
                new_ts = cts
                new_id = rid_i
        except Exception as exc:
            _log(f'row skipped (fail-open): {exc}')

    if lines:
        try:
            with dest.open('a', encoding='utf-8', errors='replace') as fh:
                fh.write('\n'.join(lines) + '\n')
        except OSError as exc:
            _log(f'staging write failed (fail-open): {exc}')
            return {
                'n_written': 0,
                'last_promoted_ts': last_ts,
                'last_promoted_id': last_id,
                'duration': round(time.monotonic() - t0, 4),
                'error': str(exc),
            }
        save_state({'last_promoted_ts': new_ts, 'last_promoted_id': new_id})
        last_ts, last_id = new_ts, new_id

    return {
        'n_written': n_written,
        'last_promoted_ts': last_ts,
        'last_promoted_id': last_id,
        'staging': str(dest),
        'duration': round(time.monotonic() - t0, 4),
    }


def self_test() -> int:
    td = Path(tempfile.mkdtemp(prefix='hindsight-promote-'))
    dbp = td / 'hindsight.db'
    staging = td / 'memory-facts' / 'staging.md'
    con = sqlite3.connect(str(dbp))
    con.execute('PRAGMA journal_mode=WAL')
    con.execute(
        'CREATE TABLE hindsight_events ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, turn_idx INTEGER, '
        'event_type TEXT NOT NULL, payload TEXT DEFAULT \'{}\', quality REAL, '
        'created_at REAL)'
    )
    con.executemany(
        'INSERT INTO hindsight_events '
        '(session_id, turn_idx, event_type, payload, quality, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        [
            ('s1', 1, 'tool_call', json.dumps({'tool_name': 'web_search', 'success': True}), 1.0, 10.0),
            ('s2', 2, 'tool_call', json.dumps({'tool_name': 'fail_tool', 'success': False}), 0.0, 11.0),
            ('s3', 3, 'tool_call', json.dumps({'tool_name': 'read_file', 'success': True}), 0.85, 10.0),
            ('s4', 4, 'tool_call', json.dumps({'tool_name': 'later', 'success': True}), 0.9, 20.0),
        ],
    )
    con.commit()
    con.close()
    global _hermes_root, _hermes_base
    old_root, old_base = _hermes_root, _hermes_base
    ok = True
    try:
        _hermes_root = td
        _hermes_base = td
        (td / 'cache').mkdir(exist_ok=True)
        r1 = promote(db_path=dbp, staging=staging)
        text = staging.read_text(encoding='utf-8') if staging.is_file() else ''
        # quality 0.0 row must be excluded; 3 high-quality rows included
        if r1.get('n_written') != 3:
            print(f'SELF-TEST FAIL n_written={r1}', file=sys.stderr)
            ok = False
        if 'fail_tool' in text:
            print('SELF-TEST FAIL low-quality row leaked', file=sys.stderr)
            ok = False
        if text.count('- [') != 3:
            print(f'SELF-TEST FAIL bullet count {text!r}', file=sys.stderr)
            ok = False
        if 'web_search' not in text or 'read_file' not in text or 'later' not in text:
            print(f'SELF-TEST FAIL missing tools {text!r}', file=sys.stderr)
            ok = False
        # same-ts rows (id 1 and 3 at ts=10) must both appear — cursor uses id
        r2 = promote(db_path=dbp, staging=staging)
        if r2.get('n_written') != 0:
            print(f'SELF-TEST FAIL reprocess n_written={r2}', file=sys.stderr)
            ok = False
    finally:
        _hermes_root, _hermes_base = old_root, old_base
    if ok:
        print('SELF-TEST PASS read hindsight_events quality>=0.7 cursor=ok')
        return 0
    print('SELF-TEST FAIL', file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Promote hindsight_events into staging.md')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    try:
        report = promote()
        print(json.dumps(report, ensure_ascii=False, default=str))
        return 0
    except Exception as exc:
        _log(f'fatal caught (fail-open): {exc}')
        traceback.print_exc(file=sys.stderr)
        return 0


if __name__ == '__main__':
    sys.exit(main())
