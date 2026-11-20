#!/usr/bin/env python3
"""Rank skill outputs by counterfactual causal-impact proxy."""
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
    conn.row_factory = sqlite3.Row
    return conn

OUT_PATH = CACHE / 'causal-critique-ranking.json'


def impact(record):
    changes = record.get('state_changes') or record.get('writes') or []
    if isinstance(changes, int):
        n_changes = changes
    elif isinstance(changes, list):
        n_changes = len(changes)
    else:
        n_changes = 1 if changes else 0
    calls = record.get('tool_calls') or record.get('calls') or []
    if isinstance(calls, int):
        n_calls = calls
    elif isinstance(calls, list):
        n_calls = len(calls)
    else:
        n_calls = 1
    text = json.dumps(record)
    if any(k in text for k in ('write', 'create', 'http', 'api', 'insert')):
        n_changes = max(n_changes, 1)
    return n_changes / max(1, n_calls)


def rank(records):
    scored = []
    for rec in records:
        name = rec.get('skill') or rec.get('name') or rec.get('id') or 'unknown'
        ci = impact(rec)
        scored.append({'name': str(name), 'causal_impact': ci})
    scored.sort(key=lambda x: x['causal_impact'], reverse=True)
    return {
        'ts': _now(),
        'n': len(scored),
        'ranking': scored,
    }


def _self_test() -> int:
    recs = [
        {'skill': 'noop', 'state_changes': [], 'tool_calls': ['read']},
        {'skill': 'writer', 'state_changes': ['file_a', 'file_b'], 'tool_calls': ['write']},
        {'skill': 'api', 'state_changes': ['http'], 'tool_calls': ['get', 'post']},
    ]
    r = rank(recs)
    names = [x['name'] for x in r['ranking']]
    assert names[0] == 'writer', names
    assert r['ranking'][0]['causal_impact'] == 2.0
    _atomic_write(OUT_PATH, r)
    print(f'[causal-critique-ranker] --self-test PASS {names}')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[causal-critique-ranker] --self-test FAIL: {exc}')
            sys.exit(1)
    recs = [
        {'skill': 'search', 'state_changes': [], 'tool_calls': ['web_search']},
        {'skill': 'persist', 'state_changes': ['cache.json'], 'tool_calls': ['write']},
    ]
    r = rank(recs)
    _atomic_write(OUT_PATH, r)
    print(json.dumps(r))


if __name__ == '__main__':
    main()
