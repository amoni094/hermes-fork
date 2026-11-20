#!/usr/bin/env python3
"""Strategic opinion manipulation in multiplex networks.

Hard core: final_score = sum_i(w_i * report_i) where w_i is centrality-tilted
by manipulability index M_i = sqrt(influence_i), and sum(w_i)=1; distortion
bounded by covariance(M_i, private_opinion_i).
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

import argparse
import fcntl
import json
import math
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'
OUT_NAME = 'consensus-weights.json'


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            tmp.replace(path)
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _clip01(val) -> float | None:
    try:
        s = float(val)
    except (TypeError, ValueError):
        return None
    if s != s or s in (float('inf'), float('-inf')):
        return None
    s = max(s, 0.0)
    s = min(s, 1.0)
    return s


def manipulability_index(influence) -> float | None:
    """M_i = sqrt(influence_i). influence is clipped to [0, 1]."""
    inf = _clip01(influence)
    if inf is None:
        return None
    return math.sqrt(inf)


def normalize_weights(M) -> list:
    vals = []
    for m in M:
        try:
            v = float(m)
        except (TypeError, ValueError):
            return []
        if v != v or v < 0.0:
            v = 0.0
        vals.append(v)
    s = sum(vals)
    if s <= 0.0:
        n = len(vals)
        if n == 0:
            return []
        return [1.0 / n] * n
    w = [v / s for v in vals]
    # re-normalize residual so sum(w)=1 exactly
    residual = 1.0 - sum(w)
    w[-1] = w[-1] + residual
    return w


def merge_reports(weights, reports) -> float | None:
    if not weights or not reports or len(weights) != len(reports):
        return None
    acc = 0.0
    for w, r in zip(weights, reports):
        try:
            acc += float(w) * float(r)
        except (TypeError, ValueError):
            return None
    return acc


def covariance(xs, ys) -> float:
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    xa = [float(xs[i]) for i in range(n)]
    ya = [float(ys[i]) for i in range(n)]
    mx = sum(xa) / n
    my = sum(ya) / n
    return sum((xa[i] - mx) * (ya[i] - my) for i in range(n)) / n


def layer1_demo() -> dict:
    # Exact layer1 scenario: M listed as success rates [0.9, 0.7, 0.8]
    success = [0.9, 0.7, 0.8]
    variance = [0.05, 0.15, 0.08]
    M = list(success)
    w = normalize_weights(M)
    reports = [0.6, 0.4, 0.55]
    final = merge_reports(w, reports)
    noisy_plus = [r + 0.05 for r in reports]
    noisy_minus = [r - 0.05 for r in reports]
    d1 = abs(merge_reports(w, noisy_plus) - final)
    d2 = abs(merge_reports(w, noisy_minus) - final)
    distortion_change = max(d1, d2)
    dist_bound = abs(covariance(M, reports))
    return {
        'M': M,
        'weights': w,
        'reports': reports,
        'variance': variance,
        'final': final,
        'distortion_change': distortion_change,
        'distortion_bound': dist_bound,
        'success_rate': success,
    }


def read_arm_metrics(db_path: Path) -> list:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    try:
        try:
            rows = conn.execute(
                'SELECT arm_id, AVG(mean_score) AS mean_score, '
                'AVG(spi_score) AS spi_score, COUNT(*) AS n '
                'FROM anytime_eval_runs GROUP BY arm_id'
            ).fetchall()
        except sqlite3.Error:
            return []
    finally:
        conn.close()
    out = []
    for arm_id, mean_score, spi_score, n in rows:
        sr = _clip01(mean_score)
        if sr is None or not arm_id:
            continue
        out.append({
            'arm_id': str(arm_id),
            'success_rate': sr,
            'spi_score': spi_score,
            'n': int(n or 0),
        })
    return out


def compute_weights(arms: list) -> dict:
    if not arms:
        return {
            'status': 'insufficient_data',
            'weights': {},
            'n_arms': 0,
            'ts': _now(),
        }
    ids = [a['arm_id'] for a in arms]
    success = [float(a['success_rate']) for a in arms]
    M = [manipulability_index(s) for s in success]
    if any(m is None for m in M):
        return {
            'status': 'insufficient_data',
            'reason': 'bad_success_rate',
            'weights': {},
            'n_arms': 0,
            'ts': _now(),
        }
    w = normalize_weights(M)
    reports = success  # private opinion proxy
    dist_bound = abs(covariance(M, reports))
    weights = {i: wi for i, wi in zip(ids, w)}
    final = merge_reports(w, reports)
    return {
        'status': 'ok',
        'weights': weights,
        'M': {i: m for i, m in zip(ids, M)},
        'n_arms': len(ids),
        'final_score': final,
        'distortion_bound': dist_bound,
        'ts': _now(),
    }


def payload_for_file(result: dict) -> dict:
    """Flat {arm_id: weight, ...} plus metadata."""
    out = {}
    for k, v in (result.get('weights') or {}).items():
        out[k] = v
    out['ts'] = result.get('ts') or _now()
    out['distortion_bound'] = result.get('distortion_bound', 0.0)
    out['status'] = result.get('status')
    out['n_arms'] = result.get('n_arms', 0)
    if result.get('final_score') is not None:
        out['final_score'] = result['final_score']
    return out


def run(db_path: Path | None = None, out_path: Path | None = None) -> dict:
    db = Path(db_path) if db_path is not None else LIFECYCLE_DB
    dest = Path(out_path) if out_path is not None else (CACHE / OUT_NAME)
    arms = read_arm_metrics(db)
    result = compute_weights(arms)
    if result.get('status') != 'ok':
        return result
    _atomic_write_json(dest, payload_for_file(result))
    result['out_path'] = str(dest)
    return result


def _self_test() -> int:
    assert normalize_weights([]) == []
    assert merge_reports([], []) is None
    assert manipulability_index('x') is None
    assert manipulability_index(-3) == 0.0
    assert abs(manipulability_index(0.9) - math.sqrt(0.9)) < 1e-12
    demo = layer1_demo()
    w = demo['weights']
    assert abs(sum(w) - 1.0) < 1e-12
    # listed rounded weights ~ [0.38, 0.30, 0.32]
    assert abs(w[0] - 0.38) < 0.02
    assert abs(w[1] - 0.30) < 0.02
    assert abs(w[2] - 0.32) < 0.02
    final = demo['final']
    assert final is not None
    assert abs(final - 0.532) <= 0.01, f'final={final}'
    assert demo['distortion_change'] < 0.1, demo['distortion_change']
    empty = compute_weights([])
    assert empty['status'] == 'insufficient_data'
    td = Path(tempfile.mkdtemp(prefix=f'cmw-{uuid.uuid4().hex[:8]}-'))
    try:
        missing = run(db_path=td / 'no.db', out_path=td / OUT_NAME)
        assert missing['status'] == 'insufficient_data'
        assert not (td / OUT_NAME).exists()
        # synthetic arms through production M=sqrt path
        synth = [
            {'arm_id': 'A', 'success_rate': 0.9},
            {'arm_id': 'B', 'success_rate': 0.7},
            {'arm_id': 'C', 'success_rate': 0.8},
        ]
        got = compute_weights(synth)
        assert got['status'] == 'ok'
        assert abs(sum(got['weights'].values()) - 1.0) < 1e-12
        tmp = td / ('{}-{}.json'.format(OUT_NAME.replace('.json', ''), uuid.uuid4().hex[:8]))
        _atomic_write_json(tmp, payload_for_file(got))
        loaded = json.loads(tmp.read_text(encoding='utf-8'))
        assert 'A' in loaded and 'distortion_bound' in loaded
    finally:
        for p in sorted(td.rglob('*'), reverse=True):
            try:
                p.unlink() if p.is_file() else p.rmdir()
            except OSError:
                pass
        try:
            td.rmdir()
        except OSError:
            pass
    print('[compute-manipulability-weights] --self-test PASS final={:.4f} dist={:.4f}'.format(
        final, demo['distortion_change']))
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description='Manipulability-tilted consensus weights')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[compute-manipulability-weights] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = run()
        print(json.dumps({k: result[k] for k in result if k != 'M'}, default=str))
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc), 'ts': _now()}))
        sys.exit(1)


if __name__ == '__main__':
    main()
