#!/usr/bin/env python3
"""Dual-gate integrity checker: tool whitelist + output schema."""
from __future__ import annotations
import argparse, json, math, os, random, sqlite3, sys, time, zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    tmp.rename(path)

def _lifecycle_db() -> Path:
    cands = [
        Path.home() / '.hermes' / 'memory-facts' / 'lifecycle.db',
        _hermes_base / 'memory-facts' / 'lifecycle.db',
        _hermes_root / 'memory-facts' / 'lifecycle.db',
    ]
    for c in cands:
        if c.exists():
            return c
    p = cands[0]
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _connect(db: Path | None = None) -> sqlite3.Connection:
    path = db or _lifecycle_db()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute('PRAGMA journal_mode=WAL')
    conn.row_factory = sqlite3.Row
    return conn

OUT_PATH = CACHE / 'authguard-result.json'
WHITELIST = {
    'research': {'web_search', 'web_extract', 'read_file', 'search_files'},
    'script': {'read_file', 'patch', 'terminal', 'execute_code'},
    'review': {'read_file', 'search_files', 'terminal'},
    'default': {'read_file', 'search_files', 'terminal', 'execute_code', 'web_search'},
}
ERROR_MARKERS = ('traceback', 'exception:', 'error:', 'permission denied')


def gate1(tool_name, task_type='default'):
    allowed = WHITELIST.get(task_type) or WHITELIST['default']
    ok = tool_name in allowed
    return ok, ([] if ok else ['tool_not_whitelisted:' + str(tool_name)])


def gate2(output):
    issues = []
    if output is None or (isinstance(output, str) and not output.strip()):
        issues.append('empty_output')
        return False, issues
    text = output if isinstance(output, str) else json.dumps(output)
    low = text.lower()
    if any(m in low for m in ERROR_MARKERS):
        issues.append('error_string_in_output')
    return len(issues) == 0, issues


def check(tool_name, output, task_type='default'):
    g1, v1 = gate1(tool_name, task_type)
    g2, v2 = gate2(output)
    viol = v1 + v2
    payload = {
        'gate1_pass': g1,
        'gate2_pass': g2,
        'violations': viol,
        'tool_name': tool_name,
        'task_type': task_type,
        'ts': _now(),
    }
    return payload


def persist(payload):
    _atomic_write(OUT_PATH, payload)
    if not payload['violations']:
        return payload
    try:
        conn = _connect()
        conn.execute(
            'CREATE TABLE IF NOT EXISTS authguard_violations ('
            'id INTEGER PRIMARY KEY, ts TEXT, gate TEXT, '
            'tool_name TEXT, violation_detail TEXT)'
        )
        ts = payload['ts']
        for v in payload['violations']:
            gate = 'gate1' if v.startswith('tool_not') else 'gate2'
            conn.execute(
                'INSERT INTO authguard_violations(ts, gate, tool_name, violation_detail) VALUES (?,?,?,?)',
                (ts, gate, payload.get('tool_name') or '', v),
            )
        conn.commit()
        conn.close()
    except Exception:
        pass
    try:
        shadow = Path.home() / '.hermes' / 'cache' / 'shadow' / 'authguard-result.json'
        _atomic_write(shadow, payload)
    except Exception:
        pass
    return payload


def _self_test() -> int:
    ok = check('read_file', {'content': 'hello'}, 'research')
    assert ok['gate1_pass'] and ok['gate2_pass']
    bad = check('os_system', '', 'research')
    assert not bad['gate1_pass'] and not bad['gate2_pass']
    persist(bad)
    print('[authguard-integrity-checker] --self-test PASS')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--tool', default='read_file')
    ap.add_argument('--output', default='ok')
    ap.add_argument('--task-type', default='default')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[authguard-integrity-checker] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        persist(check(args.tool, args.output, args.task_type))
    except Exception:
        pass


if __name__ == '__main__':
    main()
