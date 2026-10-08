#!/usr/bin/env python3
"""routing-linucb.py — LinUCB ridge contextual bandit over hashed skill features.

d=16 hashed bag-of-token features. Sherman-Morrison rank-1 updates.
UCB = theta·x + alpha * sqrt(x^T A^{-1} x). Alarm if UCB-top1 != beta-mean-top1 with gap>0.2.

Source: Li et al. LinUCB; Lattimore & Szepesvari Ch 19 (linear bandits).
"""
from __future__ import annotations
import argparse
import json
import math
import os
import random
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

D = 16
ALPHA = 0.5
RIDGE = 1.0
GAP = 0.2


def hash_feat(tokens, dim=D):
    x = [0.0] * dim
    for t in tokens:
        h = abs(hash('linucb:' + t))
        x[h % dim] += 1.0 if ((h // dim) % 2 == 0) else -1.0
    nrm = math.sqrt(sum(v*v for v in x)) or 1.0
    return [v / nrm for v in x]


def mat_eye(d, ridge=RIDGE):
    return [[ridge if i == j else 0.0 for j in range(d)] for i in range(d)]


def mat_vec(A, x):
    return [sum(A[i][j] * x[j] for j in range(len(x))) for i in range(len(A))]


def vec_dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def sherman_morrison(Ainv, x):
    # A <- A + x x^T; Ainv <- Ainv - Ainv x x^T Ainv / (1 + x^T Ainv x)
    Ax = mat_vec(Ainv, x)
    den = 1.0 + vec_dot(x, Ax)
    if abs(den) < EPS:
        return Ainv
    d = len(x)
    out = [row[:] for row in Ainv]
    for i in range(d):
        for j in range(d):
            out[i][j] -= Ax[i] * Ax[j] / den
    return out


def solve_theta(Ainv, b):
    return mat_vec(Ainv, b)


def ucb(theta, Ainv, x, alpha=ALPHA):
    Ax = mat_vec(Ainv, x)
    bonus = math.sqrt(max(0.0, vec_dot(x, Ax)))
    return vec_dot(theta, x) + alpha * bonus


def compute(index, beta, state):
    token_map = {}
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                token_map[s['name']] = [t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)]
    names = list(token_map) or (sorted(beta.keys()) if isinstance(beta, dict) else [])
    d = D
    Ainv = state.get('Ainv') if isinstance(state, dict) else None
    b = state.get('b') if isinstance(state, dict) else None
    if not isinstance(Ainv, list) or len(Ainv) != d:
        Ainv = mat_eye(d)
    if not isinstance(b, list) or len(b) != d:
        b = [0.0] * d
    theta = solve_theta(Ainv, b)
    scores = []
    for nm in names:
        x = hash_feat(token_map.get(nm, [nm]))
        scores.append((nm, ucb(theta, Ainv, x), x))
    scores.sort(key=lambda t: -t[1])
    top = scores[0][0] if scores else None
    mean_top = None
    best_mu = -1
    if isinstance(beta, dict):
        for nm, e in beta.items():
            if not isinstance(e, dict):
                continue
            try:
                a = float(e.get('alpha', 1.0)); bb = float(e.get('beta', 1.0))
            except (TypeError, ValueError):
                continue
            mu = a / max(a + bb, EPS)
            if mu > best_mu:
                best_mu, mean_top = mu, nm
    gap = (scores[0][1] - scores[1][1]) if len(scores) > 1 else 0.0
    alarm = bool(top and mean_top and top != mean_top and gap > GAP)
    return {
        'ts': time.time(),
        'n_skills': len(names),
        'd': d,
        'linucb_top1': top,
        'mean_top1': mean_top,
        'ucb_gap': round(gap, 6),
        'alarm': alarm,
        'reason': 'linucb_vs_mean' if alarm else 'ok',
        'Ainv': Ainv,
        'b': b,
        'theta': [round(v, 6) for v in theta],
    }, scores


def run(cache=None, skill=None, reward=0.0):
    cache = cache or _cache_dir()
    index = _load_json(cache / 'skill-router-index.json', {})
    beta = _load_json(cache / 'skill-beta-state.json', {})
    state = _load_json(cache / 'routing-linucb-state.json', {})
    result, scores = compute(index, beta, state if isinstance(state, dict) else {})
    Ainv, b = result['Ainv'], result['b']
    if skill:
        x = None
        for nm, _, xx in scores:
            if nm == skill:
                x = xx
                break
        if x is None:
            x = hash_feat([skill])
        Ainv = sherman_morrison(Ainv, x)
        r = 0.0 if reward < 0 else (1.0 if reward > 1 else float(reward))
        b = [b[i] + r * x[i] for i in range(D)]
        result['Ainv'] = Ainv
        result['b'] = b
        result['updated'] = skill
    slim = {k: v for k, v in result.items() if k not in ('Ainv', 'b')}
    try:
        _atomic_write_json(cache / 'routing-linucb-state.json', result)
        _atomic_write_json(cache / 'routing-linucb.json', slim)
    except Exception:
        pass
    return slim


def self_test():
    failures = []
    try:
        A = mat_eye(4)
        x = [1.0, 0, 0, 0]
        A2 = sherman_morrison(A, x)
        # (I+xx^T)^{-1} e1 should be smaller in first coord than 1
        assert A2[0][0] < 1.0
        th = solve_theta(A2, [1, 0, 0, 0])
        u1 = ucb(th, A2, x)
        u2 = ucb(th, A2, [0, 1, 0, 0])
        json.dumps({'u1': u1, 'u2': u2})
    except Exception as e:
        failures.append(f'sm: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / 'skill-beta-state.json').write_text(json.dumps({
                'a': {'alpha': 5, 'beta': 1}, 'b': {'alpha': 1, 'beta': 5}
            }))
            r = run(cache=d, skill='a', reward=1.0)
            assert (d / 'routing-linucb.json').exists()
            json.dumps(r)
    except Exception as e:
        failures.append(f'io: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--skill', default=None)
    ap.add_argument('--reward', type=float, default=0.0)
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        print(json.dumps(run(skill=args.skill, reward=args.reward), indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
