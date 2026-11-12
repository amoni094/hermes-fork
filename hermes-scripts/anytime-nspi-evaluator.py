#!/usr/bin/env python3
"""Anytime solver evaluation with normalized signed primal integral (NSPI).

NSPI = (integral of signed quality over time) / (T * quality_range), in [-1, 1].
An arm with monotonically improving quality must have NSPI > 0; a constant
arm has NSPI = 0.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import fcntl
import json
import math
import sqlite3
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'nspi-state.json'


def _true_home(base: Path) -> Path:
    p = Path(base)
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


LIFECYCLE_DB = _true_home(_hermes_base) / 'memory-facts' / 'lifecycle.db'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_float(v, default=0.0) -> float:
    try:
        x = float(v)
        if not math.isfinite(x):
            return default
        return x
    except (TypeError, ValueError):
        return default


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + '.lock') if path.suffix else path.with_name(path.name + '.lock')
    tmp = path.with_name(path.name + '.tmp')
    payload = json.dumps(obj, indent=2) + '\n'
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            tmp.write_text(payload, encoding='utf-8')
            tmp.replace(path)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def nspi(qualities, quality_range: float, T=None) -> float:
    """NSPI = sum((q[t]-q[0]) * (1 - t/T)) / (T * quality_range), clipped to [-1,1]."""
    qs = [_coerce_float(q) for q in qualities]
    n = len(qs)
    if n == 0:
        return 0.0
    Tval = float(n if T is None else T)
    qr = _coerce_float(quality_range)
    if Tval <= 0 or qr <= 0:
        return 0.0
    baseline = qs[0]
    acc = 0.0
    for t, q in enumerate(qs):
        acc += (q - baseline) * (1.0 - (t / Tval))
    val = acc / (Tval * qr)
    if not math.isfinite(val):
        return 0.0
    return max(-1.0, min(1.0, val))


def quality_range_of(arm_series: dict) -> float:
    vals = []
    for pts in arm_series.values():
        for q in pts:
            vals.append(_coerce_float(q))
    if not vals:
        return 0.0
    return max(vals) - min(vals)


def trend_of(qualities) -> str:
    if not qualities:
        return 'stable'
    first = _coerce_float(qualities[0])
    last = _coerce_float(qualities[-1])
    if last > first + 1e-9:
        return 'improving'
    if last < first - 1e-9:
        return 'degrading'
    return 'stable'


def evaluate_arms(arm_series: dict) -> dict:
    qr = quality_range_of(arm_series)
    arms = {}
    for arm_id, qs in arm_series.items():
        qlist = [_coerce_float(q) for q in qs]
        arms[str(arm_id)] = {
            'nspi': nspi(qlist, qr),
            'n_evals': len(qlist),
            'trend': trend_of(qlist),
        }
    return {'ts': _now(), 'arms': arms, 'quality_range': qr}


def _connect(db: Path):
    conn = sqlite3.connect(str(db), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.row_factory = sqlite3.Row
    return conn


def load_live_series(db: Path) -> dict:
    if not db.exists():
        return {}
    conn = _connect(db)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'anytime_eval_runs' not in tables:
            return {}
        cols = {r[1] for r in conn.execute('PRAGMA table_info(anytime_eval_runs)')}
        order = 'id' if 'id' in cols else 'ts'
        rows = conn.execute(
            'SELECT arm_id, mean_score, spi_score, ts FROM anytime_eval_runs ORDER BY %s' % order
        ).fetchall()
    finally:
        conn.close()
    series = defaultdict(list)
    for row in rows:
        arm = row['arm_id']
        if arm is None:
            continue
        q = row['mean_score']
        if q is None:
            q = row['spi_score']
        if q is None:
            continue
        series[str(arm)].append(_coerce_float(q))
    return dict(series)


def layer1_demo() -> dict:
    """3 arms A/B/C over 21 turns: A linear 0->1, B constant 0.5, C 1->0."""
    n = 21
    series = {
        'A': [i / 20.0 for i in range(n)],
        'B': [0.5] * n,
        'C': [1.0 - i / 20.0 for i in range(n)],
    }
    return evaluate_arms(series)


def run_live(out_path: Path) -> dict:
    series = load_live_series(LIFECYCLE_DB)
    nonempty = {k: v for k, v in series.items() if v}
    if not nonempty:
        return {'status': 'insufficient_data', 'n': 0, 'ts': _now(), 'arms': {}}
    state = evaluate_arms(nonempty)
    state['status'] = 'ok'
    _atomic_write(out_path, state)
    return state


def _self_test() -> int:
    demo = layer1_demo()
    arms = demo['arms']
    assert set(arms) == {'A', 'B', 'C'}, arms
    assert arms['A']['nspi'] > 0, arms['A']
    assert abs(arms['B']['nspi']) < 0.01, arms['B']
    assert arms['C']['nspi'] < 0, arms['C']
    for a in arms.values():
        assert -1.0 <= a['nspi'] <= 1.0
        assert a['n_evals'] == 21
    assert arms['A']['trend'] == 'improving'
    assert arms['B']['trend'] == 'stable'
    assert arms['C']['trend'] == 'degrading'
    # constant arm is exactly 0 regardless of baseline
    assert nspi([0.3] * 10, 1.0) == 0.0
    empty = evaluate_arms({})
    assert empty['arms'] == {}
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    try:
        _atomic_write(tmp, demo)
        loaded = json.loads(tmp.read_text(encoding='utf-8'))
        assert loaded['arms']['A']['nspi'] > 0
    finally:
        tmp.unlink(missing_ok=True)
        tmp.with_suffix(tmp.suffix + '.lock').unlink(missing_ok=True)
    print('[anytime-nspi-evaluator] --self-test PASS A=%.4f B=%.4f C=%.4f' % (
        arms['A']['nspi'], arms['B']['nspi'], arms['C']['nspi']))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description='Anytime NSPI evaluator')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print('[anytime-nspi-evaluator] --self-test FAIL: %s' % exc)
            return 1
    try:
        state = run_live(OUT_PATH)
        print(json.dumps(state))
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
