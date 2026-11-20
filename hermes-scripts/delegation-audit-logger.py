#!/usr/bin/env python3
"""Audit delegation decisions from lifecycle / routing logs."""
from __future__ import annotations
import argparse, json, math, os, random, sqlite3, sys, time, uuid, zlib
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
    os.replace(tmp, path)

def _lifecycle_db() -> Path:
    return _hermes_root / 'memory-facts' / 'lifecycle.db'

def _connect(db: Path | None = None) -> sqlite3.Connection:
    path = db or _lifecycle_db()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn

OUT_PATH = CACHE / 'delegation-audit-report.json'


def extract_events():
    events = []
    jsonl = CACHE / 'routing-events.jsonl'
    if jsonl.exists():
        try:
            for i, line in enumerate(jsonl.read_text(encoding='utf-8').splitlines()):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tool = str(rec.get('tool') or rec.get('tool_name') or '')
                if 'delegate' in tool.lower() or rec.get('delegated') or rec.get('subtask_count'):
                    suc = rec.get('success')
                    if suc is None:
                        suc = rec.get('top_score')
                    if suc is None:
                        continue
                    events.append({
                        'episode_id': str(rec.get('episode_id') or rec.get('ts') or i),
                        'subtask_count': int(rec.get('subtask_count') or rec.get('n_results') or 1),
                        'success': float(suc),
                    })
        except OSError:
            pass
    try:
        conn = _connect()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'episodes' in tables:
            {r[1] for r in conn.execute('PRAGMA table_info(episodes)')}
            # best-effort
            q = 'SELECT * FROM episodes LIMIT 500'
            for row in conn.execute(q):
                d = dict(row)
                blob = json.dumps(d).lower()
                if 'delegate' in blob:
                    events.append({
                        'episode_id': str(d.get('id') or d.get('ts') or len(events)),
                        'subtask_count': int(d.get('subtask_count') or 1),
                        'success': float(d.get('success') or 0),
                    })
        conn.close()
    except Exception:
        pass
    return events


def audit(events):
    n = len(events)
    if n == 0:
        return {
            'ts': _now(),
            'n_events': 0,
            'n': 0,
            'status': 'insufficient_data',
            'delegation_rate': None,
            'avg_subtasks_per_delegation': None,
            'success_rate': None,
            'flags': ['no_delegation_events'],
        }
    sub = [e['subtask_count'] for e in events]
    suc = [1.0 if e['success'] >= 0.5 else 0.0 for e in events]
    flags = []
    avg_sub = sum(sub) / n
    suc_rate = sum(suc) / n
    if avg_sub > 8:
        flags.append('high_fanout')
    if suc_rate < 0.4:
        flags.append('low_success')
    return {
        'ts': _now(),
        'n_events': n,
        'delegation_rate': 1.0,  # among extracted delegation events
        'avg_subtasks_per_delegation': avg_sub,
        'success_rate': suc_rate,
        'flags': flags,
        'events_sample': events[:20],
    }


def persist(report, events):
    if report.get('status') == 'insufficient_data':
        return report
    _atomic_write(OUT_PATH, {k: v for k, v in report.items() if k != 'events_sample'})
    return report


def _self_test() -> int:
    events = [
        {'episode_id': 'e1', 'subtask_count': 2, 'success': 1.0},
        {'episode_id': 'e2', 'subtask_count': 3, 'success': 0.0},
        {'episode_id': 'e3', 'subtask_count': 1, 'success': 1.0},
    ]
    r = audit(events)
    assert r['n_events'] == 3
    assert abs(r['avg_subtasks_per_delegation'] - 2.0) < 1e-9
    assert abs(r['success_rate'] - 2 / 3) < 1e-9
    empty = audit([])
    assert empty.get('status') == 'insufficient_data'
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    _atomic_write(tmp, r)
    tmp.unlink(missing_ok=True)
    print('[delegation-audit-logger] --self-test PASS')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[delegation-audit-logger] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        events = extract_events()
        r = audit(events)
        persist(r, events)
        print(json.dumps({k: r[k] for k in r if k != 'events_sample'}))
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
