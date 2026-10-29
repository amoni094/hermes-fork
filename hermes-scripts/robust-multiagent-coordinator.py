#!/usr/bin/env python3
"""Robust consensus via trimmed mean with minimal communication."""
from __future__ import annotations

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import random
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'multiagent-coord-result.json'
CONSENSUS_PATH = CACHE / 'multiagent-consensus.json'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))


def trimmed_mean(xs, trim=0.10):
    xs = [float(x) for x in xs]
    n = len(xs)
    if n == 0:
        return 0.0
    k = int(n * trim)
    ys = sorted(xs)
    core = ys[k:n - k] if n - 2 * k > 0 else ys
    return sum(core) / len(core)


def coordinate(worker_results, trim=0.10):
    vals = []
    for r in worker_results:
        if isinstance(r, dict):
            v = r.get('value', r.get('score', r.get('result')))
        else:
            v = r
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            continue
    agg = trimmed_mean(vals, trim=trim)
    return {
        'ts': _now(),
        'n_workers': len(vals),
        'trim': trim,
        'aggregate': agg,
        'raw_mean': (sum(vals) / len(vals)) if vals else 0.0,
        'values': vals,
    }


def simulate_round(n=10, rng=None):
    rng = rng or random.Random(0)
    vals = [rng.gauss(0.7, 0.03) for _ in range(n - 2)] + [0.05, 1.4]
    return [{'id': i, 'value': v} for i, v in enumerate(vals)]


def _robust_rate(rates):
    n = len(rates)
    if n == 0:
        return 0.0
    if n >= 10:
        ys = sorted(rates)
        core = ys[1:-1]
        return sum(core) / len(core)
    return sum(rates) / n


def read_outcomes(db_path=None, n=20, out_path=None) -> dict:
    db = Path(db_path) if db_path is not None else LIFECYCLE_DB
    dest = Path(out_path) if out_path is not None else CONSENSUS_PATH
    if not db.exists():
        return {'status': 'insufficient_data', 'n': 0}
    try:
        conn = sqlite3.connect(str(db))
        try:
            tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'delegation_audit' not in tabs:
                return {'status': 'insufficient_data', 'n': 0}
            rows = conn.execute(
                'SELECT success_rate FROM delegation_audit ORDER BY ts DESC LIMIT ?',
                (int(n),),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return {'status': 'insufficient_data', 'n': 0}
    rates = []
    for row in rows:
        try:
            rates.append(float(row[0]))
        except (TypeError, ValueError):
            continue
    nobs = len(rates)
    if nobs < 5:
        return {'status': 'insufficient_data', 'n': nobs}
    mean_sr = sum(rates) / nobs
    robust_sr = _robust_rate(rates)
    consensus = robust_sr >= 0.75
    result = {
        'ts': _now(),
        'mean_success_rate': mean_sr,
        'robust_rate': robust_sr,
        'consensus_threshold': consensus,
        'n_episodes': nobs,
    }
    _atomic_write(dest, result)
    return result


def _self_test() -> int:
    workers = simulate_round(n=10, rng=random.Random(1))
    r = coordinate(workers)
    assert r['n_workers'] == 10
    assert abs(r['aggregate'] - 0.7) < abs(r['raw_mean'] - 0.7) + 0.05
    tmp = Path(tempfile.gettempdir()) / ('coord-%s.json' % uuid.uuid4().hex)
    _atomic_write(tmp, r)
    tmp.unlink(missing_ok=True)

    td = Path(tempfile.mkdtemp(prefix='rmc-%s-' % uuid.uuid4().hex[:8]))
    try:
        db = td / 'lifecycle.db'
        conn = sqlite3.connect(str(db))
        conn.execute(
            'CREATE TABLE delegation_audit ('
            'id INTEGER PRIMARY KEY, ts TEXT, episode_id TEXT, '
            'subtask_count INTEGER, success_rate REAL, audit_flags TEXT)'
        )
        for i in range(3):
            conn.execute(
                'INSERT INTO delegation_audit(ts, episode_id, subtask_count, success_rate, audit_flags) '
                'VALUES (?,?,?,?,?)',
                ('2026-10-28T12:00:%02d' % i, 'e%d' % i, 2, 0.9, '[]'),
            )
        conn.commit()
        low = read_outcomes(db_path=db, out_path=td / 'c1.json')
        assert low.get('status') == 'insufficient_data'
        assert low.get('n') == 3
        for i in range(3, 8):
            conn.execute(
                'INSERT INTO delegation_audit(ts, episode_id, subtask_count, success_rate, audit_flags) '
                'VALUES (?,?,?,?,?)',
                ('2026-10-28T12:01:%02d' % i, 'e%d' % i, 2, 0.8, '[]'),
            )
        conn.commit()
        conn.close()
        outp = td / 'multiagent-consensus.json'
        ok = read_outcomes(db_path=db, out_path=outp)
        assert ok.get('n_episodes') >= 5, ok
        assert 'mean_success_rate' in ok
        assert 'robust_rate' in ok
        assert 'consensus_threshold' in ok
        loaded = json.loads(outp.read_text(encoding='utf-8'))
        assert loaded['n_episodes'] == ok['n_episodes']
        print('[robust-multiagent-coordinator] --self-test PASS agg=%.3f raw=%.3f n_ep=%s' % (
            r['aggregate'], r['raw_mean'], ok['n_episodes']))
        return 0
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--read-outcomes', action='store_true')
    ap.add_argument('--n', type=int, default=10)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print('[robust-multiagent-coordinator] --self-test FAIL: %s' % exc)
            sys.exit(1)
    if args.read_outcomes:
        r = read_outcomes()
        print(json.dumps(r))
        sys.exit(0)
    r = coordinate(simulate_round(n=args.n))
    _atomic_write(OUT_PATH, r)
    print(json.dumps({k: r[k] for k in r if k != 'values'}))


if __name__ == '__main__':
    main()
