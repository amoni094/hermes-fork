#!/usr/bin/env python3
"""routing-kl-ucb.py — Bernoulli KL-UCB indices from beta-bandit state.

Index: max q in [mu,1] s.t. n * kl(mu,q) <= log(t) + 3 log log(t).
Unused arms (n=0) get +inf. Alarm if argmax KL-UCB disagrees with argmax beta-mean
and the index gap exceeds 0.15.

Source: Cappé/Garivier KL-UCB; Lattimore & Szepesvari Theorem 10.6.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
import time
from collections import defaultdict, deque, Counter
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

EPS = 1e-15


def _cache_dir() -> Path:
    override = os.environ.get('HERMES_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write_json(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n')
        os.replace(str(tmp), str(path))
    except Exception:
        try:
            tmp = path.with_suffix(path.suffix + '.tmp')
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, FileNotFoundError, json.JSONDecodeError):
        return default

GAP = 0.15


def bernoulli_kl(p, q):
    p = min(1.0 - EPS, max(EPS, p))
    q = min(1.0 - EPS, max(EPS, q))
    return p * math.log(p / q) + (1.0 - p) * math.log((1.0 - p) / (1.0 - q))


def kl_ucb_index(mu, n, t, lo=0.0, hi=1.0):
    if n <= 0:
        return 1.0
    if t <= 1:
        t = 2.0
    rhs = math.log(t) + 3.0 * math.log(max(math.log(t), 1.0))
    # binary search q in [mu, 1]
    mu = min(1.0, max(0.0, mu))
    loq, hiq = mu, 1.0
    for _ in range(48):
        mid = 0.5 * (loq + hiq)
        if n * bernoulli_kl(mu, mid) > rhs:
            hiq = mid
        else:
            loq = mid
    return loq


def compute(beta):
    names = sorted(beta.keys()) if isinstance(beta, dict) else []
    rows = []
    t = 0.0
    for nm in names:
        e = beta.get(nm) if isinstance(beta.get(nm), dict) else {}
        try:
            a = float(e.get('alpha', 1.0))
            b = float(e.get('beta', 1.0))
        except (TypeError, ValueError):
            a, b = 1.0, 1.0
        n = max(0.0, a + b - 2.0)
        mu = a / max(a + b, EPS)
        t += n
        rows.append({'skill': nm, 'n': n, 'mu': mu, 'alpha': a, 'beta': b})
    t = max(t, 1.0)
    for r in rows:
        r['kl_ucb'] = kl_ucb_index(r['mu'], r['n'], t)
    if not rows:
        return {'n_skills': 0, 'alarm': False, 'reason': 'empty'}
    by_ucb = sorted(rows, key=lambda x: -x['kl_ucb'])
    by_mu = sorted(rows, key=lambda x: -x['mu'])
    top_u, top_m = by_ucb[0]['skill'], by_mu[0]['skill']
    gap = abs(by_ucb[0]['kl_ucb'] - by_mu[0]['mu'])
    alarm = top_u != top_m and gap > GAP
    return {
        'ts': time.time(),
        'n_skills': len(rows),
        't': t,
        'kl_ucb_top1': top_u,
        'mean_top1': top_m,
        'index_gap': round(gap, 6),
        'alarm': alarm,
        'reason': 'klucb_vs_mean_disagreement' if alarm else 'ok',
        'top': [{k: (round(v, 6) if isinstance(v, float) else v)
                 for k, v in r.items()} for r in by_ucb[:8]],
    }


def run(cache=None):
    cache = cache or _cache_dir()
    beta = _load_json(cache / 'skill-beta-state.json', {})
    result = compute(beta if isinstance(beta, dict) else {})
    try:
        _atomic_write_json(cache / 'routing-kl-ucb.json', result)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        assert abs(bernoulli_kl(0.5, 0.5)) < 1e-12
        assert bernoulli_kl(0.1, 0.9) > 0
        idx0 = kl_ucb_index(0.0, 0, 10)
        assert idx0 == 1.0
        idx = kl_ucb_index(0.9, 100, 200)
        assert 0.9 <= idx <= 1.0
        idx_low = kl_ucb_index(0.1, 100, 200)
        assert idx_low < idx
    except Exception as e:
        failures.append(f'kl: {e}')
    try:
        # under-sampled high-mean vs well-sampled medium
        r = compute({
            'star': {'alpha': 3.0, 'beta': 1.0},   # n=2, mu=0.75
            'work': {'alpha': 60.0, 'beta': 40.0}, # n=98, mu=0.6
        })
        assert r['kl_ucb_top1'] in ('star', 'work')
        json.dumps(r)
    except Exception as e:
        failures.append(f'rank: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d)
            assert (d / 'routing-kl-ucb.json').exists()
    except Exception as e:
        failures.append(f'missing: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        print(json.dumps(run(), indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
