#!/usr/bin/env python3
"""Evaluating the Effect of the Order of Optimization Passes.

Tests whether reordering skill/tool dispatch sequence affects outcome quality.
Stdlib only. Profile-aware. Shadow-safe.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import fcntl
import json
import sqlite3
import statistics
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC
from itertools import permutations

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'pass-ordering-state.json'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'
SENSITIVITY_THRESHOLD = 0.1


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _connect(db_path: Path):
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def load_arm_scores(db_path: Path) -> dict:
    """arm_id -> list of spi_score."""
    out = {}
    if not db_path.exists():
        return out
    conn = None
    try:
        conn = _connect(db_path)
        tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'anytime_eval_runs' not in tabs:
            return out
        rows = conn.execute('SELECT arm_id, spi_score FROM anytime_eval_runs').fetchall()
        for arm_id, spi in rows:
            if arm_id is None:
                continue
            try:
                score = float(spi)
            except (TypeError, ValueError):
                continue
            if score != score:
                continue
            out.setdefault(str(arm_id), []).append(score)
    except sqlite3.Error:
        return {}
    finally:
        if conn is not None:
            conn.close()
    return out


def arm_means(arm_scores: dict) -> dict:
    means = {}
    for arm, scores in arm_scores.items():
        if scores:
            means[arm] = float(statistics.mean(scores))
    return means


def permutation_quality(order, means: dict) -> float:
    """Anytime position-weighted cumulative quality.

    Earlier passes contribute more (interruptible / prefix-observed).
    weight at position i (0-based) = n - i.
    """
    n = len(order)
    if n == 0:
        return 0.0
    total = 0.0
    for i, arm in enumerate(order):
        total += float(means.get(arm, 0.0)) * float(n - i)
    return total


def evaluate_orderings(means: dict) -> dict:
    arms = sorted(means.keys())
    if not arms:
        return {
            'status': 'insufficient_data',
            'n': 0,
            'best_ordering': [],
            'worst_ordering': [],
            'ordering_sensitivity': 0.0,
            'permutation_scores': {},
            'ordering_matters': False,
        }
    perm_scores = {}
    best_score = None
    worst_score = None
    best_order = list(arms)
    worst_order = list(arms)
    scores_list = []
    for perm in permutations(arms):
        key = '>'.join(perm)
        sc = permutation_quality(perm, means)
        perm_scores[key] = sc
        scores_list.append(sc)
        if best_score is None or sc > best_score:
            best_score = sc
            best_order = list(perm)
        if worst_score is None or sc < worst_score:
            worst_score = sc
            worst_order = list(perm)
    mean_sc = float(statistics.mean(scores_list)) if scores_list else 0.0
    std_sc = float(statistics.pstdev(scores_list)) if len(scores_list) > 1 else 0.0
    if abs(mean_sc) < 1e-12:
        # mean~0 with nonzero spread still means order changes cumulative quality
        sensitivity = 0.0 if std_sc == 0.0 else 1.0
    else:
        sensitivity = std_sc / abs(mean_sc)
    return {
        'status': 'ok',
        'n_arms': len(arms),
        'n_permutations': len(perm_scores),
        'best_ordering': best_order,
        'worst_ordering': worst_order,
        'best_score': best_score,
        'worst_score': worst_score,
        'ordering_sensitivity': float(sensitivity),
        'permutation_scores': perm_scores,
        'ordering_matters': bool(sensitivity > SENSITIVITY_THRESHOLD),
        'arm_means': means,
    }


def run(db_path: Path, out_path: Path) -> dict:
    arm_scores = load_arm_scores(db_path)
    means = arm_means(arm_scores)
    result = evaluate_orderings(means)
    result['ts'] = _now()
    if result.get('status') == 'insufficient_data':
        return result
    payload = {
        'ts': result['ts'],
        'best_ordering': result['best_ordering'],
        'ordering_sensitivity': result['ordering_sensitivity'],
        'permutation_scores': result['permutation_scores'],
        'ordering_matters': result['ordering_matters'],
        'n_arms': result.get('n_arms'),
        'worst_ordering': result.get('worst_ordering'),
    }
    _atomic_write(out_path, payload)
    result['written'] = str(out_path)
    return result


def _self_test() -> int:
    means = {'arm1': 0.9, 'arm2': 0.5, 'arm3': 0.3}
    r = evaluate_orderings(means)
    assert r['best_ordering'] != r['worst_ordering'], r
    assert r['ordering_sensitivity'] > 0.0, r
    assert r['best_ordering'][0] == 'arm1', r
    assert r['worst_ordering'][0] == 'arm3', r
    td = Path(tempfile.mkdtemp(prefix='opo-'))
    try:
        db = td / 'lc.db'
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute(
            'CREATE TABLE anytime_eval_runs (id INTEGER PRIMARY KEY, ts TEXT, arm_id TEXT, '
            'mean_score REAL, spi_score REAL, n_queries INTEGER, reference_frozen_at INTEGER)'
        )
        for arm, spi in (('X', 0.9), ('Y', 0.5), ('Z', 0.3)):
            conn.execute(
                'INSERT INTO anytime_eval_runs (ts, arm_id, mean_score, spi_score, n_queries, reference_frozen_at) '
                'VALUES (?,?,?,?,?,?)',
                (_now(), arm, spi, spi, 10, 1),
            )
        conn.commit()
        conn.close()
        out = td / ('pass-ordering-state_test_' + uuid.uuid4().hex + '.json')
        live = run(db, out)
        assert live.get('status') == 'ok', live
        assert out.exists()
        payload = json.loads(out.read_text(encoding='utf-8'))
        assert payload['best_ordering'] != payload.get('worst_ordering', [])
        assert payload['ordering_sensitivity'] > 0.0
        missing = run(td / 'nope.db', td / 'nope.json')
        assert missing.get('status') == 'insufficient_data', missing
        assert not (td / 'nope.json').exists()
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    print('[optimization-pass-ordering] --self-test PASS')
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description='Evaluating the Effect of the Order of Optimization Passes')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--db', default=str(LIFECYCLE_DB))
    ap.add_argument('--out', default=str(OUT_PATH))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[optimization-pass-ordering] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = run(Path(args.db), Path(args.out))
        print(json.dumps({k: result[k] for k in result if k != 'permutation_scores'} | {
            'n_permutations': len(result.get('permutation_scores') or {})
        }, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
