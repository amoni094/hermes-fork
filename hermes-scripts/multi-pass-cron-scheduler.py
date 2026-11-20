#!/usr/bin/env python3
"""Multi-pass heuristic ordering of cron jobs."""
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

OUT_PATH = CACHE / 'cron-schedule-optimized.json'
JOBS = _hermes_root / 'cron' / 'jobs.json'


def load_jobs():
    if not JOBS.exists():
        return []
    try:
        data = json.loads(JOBS.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []
    jobs = data.get('jobs', data) if isinstance(data, dict) else data
    if isinstance(jobs, dict):
        jobs = list(jobs.values())
    return jobs if isinstance(jobs, list) else []


def days_since(ts):
    if not ts:
        return 30.0
    try:
        # support Z and offsets
        t = str(ts).replace('Z', '+00:00')
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        return max(0.0, (now - dt).total_seconds() / 86400.0)
    except Exception:
        return 30.0


def score_job(j):
    streak = int(j.get('failure_streak') or 0)
    days = days_since(j.get('last_run_at'))
    return streak * 10.0 + days * 2.0


def cache_outputs(j):
    script = str(j.get('script') or '')
    # heuristic: stem as cache identity
    return Path(script).stem


def optimize(jobs):
    ranked = []
    for j in jobs:
        if not isinstance(j, dict):
            continue
        ranked.append({
            'id': j.get('id') or j.get('name'),
            'name': j.get('name'),
            'priority': score_job(j),
            'failure_streak': int(j.get('failure_streak') or 0),
            'days_since_last_run': days_since(j.get('last_run_at')),
            'script': j.get('script'),
        })
    ranked.sort(key=lambda x: x['priority'], reverse=True)
    # dependency conflicts: same cache identity
    by_out = defaultdict(list)
    for r in ranked:
        by_out[cache_outputs(r)].append(r['id'])
    conflicts = [{'output_key': k, 'jobs': v} for k, v in by_out.items() if len(v) > 1]
    return {
        'ts': _now(),
        'order': ranked,
        'conflicts': conflicts[:50],
        'n_jobs': len(ranked),
    }


def _self_test() -> int:
    now = datetime.now(UTC).isoformat()
    jobs = [
        {'id': 'hot', 'name': 'hot', 'failure_streak': 5, 'last_run_at': now, 'script': 'a.py'},
        {'id': 'cold', 'name': 'cold', 'failure_streak': 0, 'last_run_at': '2020-01-01T00:00:00+00:00', 'script': 'b.py'},
        {'id': 'ok', 'name': 'ok', 'failure_streak': 0, 'last_run_at': now, 'script': 'a.py'},
    ]
    r = optimize(jobs)
    assert r['order'][0]['id'] in ('hot', 'cold')
    assert r['order'][0]['priority'] >= r['order'][-1]['priority']
    assert any(c for c in r['conflicts'])
    _atomic_write(OUT_PATH, r)
    print('[multi-pass-cron-scheduler] --self-test PASS top={}'.format(r['order'][0]['id']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[multi-pass-cron-scheduler] --self-test FAIL: {exc}')
            sys.exit(1)
    r = optimize(load_jobs())
    _atomic_write(OUT_PATH, r)
    print(json.dumps({'n_jobs': r['n_jobs'], 'n_conflicts': len(r['conflicts']), 'top': (r['order'][0]['id'] if r['order'] else None)}))


if __name__ == '__main__':
    main()
