#!/usr/bin/env python3
"""routing-exp4-contextual.py — EXP4 contextual experts over skills.

Each skill is an expert whose advice vector is a softmax of BM25/token overlap
with the query context. Mix: p = (1-gamma) sum_i q_i advice_i + gamma/n.
Update expert weights by importance-weighted reward.

Source: Auer et al. EXP4; Lattimore & Szepesvari Ch 18 (contextual/adversarial).
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

GAMMA = 0.1


def softmax(xs, t=1.0):
    if not xs:
        return []
    m = max(xs)
    ex = [math.exp((x - m) / max(t, EPS)) for x in xs]
    s = sum(ex) or 1.0
    return [e / s for e in ex]


def mixed_p(q, advice, gamma=GAMMA):
    """advice: n x n rows=experts, cols=arms. q: expert mix."""
    n = len(q)
    if n == 0:
        return []
    p = [0.0] * n
    for i in range(n):
        for j in range(n):
            p[j] += q[i] * advice[i][j]
    return [(1.0 - gamma) * pj + gamma / n for pj in p]


def exp4_update(weights, advice, played, reward, gamma=GAMMA):
    n = len(weights)
    s = sum(max(EPS, w) for w in weights) or float(n)
    q = [max(EPS, w) / s for w in weights]
    p = mixed_p(q, advice, gamma)
    pi = max(p[played], EPS)
    rhat = [0.0] * n
    rhat[played] = float(reward) / pi
    xhat = [0.0] * n
    for i in range(n):
        xhat[i] = sum(advice[i][j] * rhat[j] for j in range(n))
    out = []
    for i in range(n):
        out.append(max(EPS, weights[i] * math.exp(gamma * xhat[i] / n)))
    mx = max(out)
    if mx > 1e12:
        out = [w / mx for w in out]
    return out


def advice_from_context(names, token_map, query_tokens):
    n = len(names)
    qset = set(t.lower() for t in query_tokens)
    scores = []
    for nm in names:
        toks = token_map.get(nm, set())
        scores.append(float(len(toks & qset)))
    rows = []
    for i in range(n):
        # expert i boosts its own score then softmax
        row_s = list(scores)
        row_s[i] += 1.0
        rows.append(softmax(row_s))
    return rows


def run(cache=None, query='', skill=None, reward=0.0):
    cache = cache or _cache_dir()
    index = _load_json(cache / 'skill-router-index.json', {})
    beta = _load_json(cache / 'skill-beta-state.json', {})
    names = []
    token_map = {}
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                names.append(s['name'])
                token_map[s['name']] = {t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)}
    if not names and isinstance(beta, dict):
        names = sorted(beta.keys())
    if not names:
        names = ['dummy']
    state = _load_json(cache / 'routing-exp4-state.json', {})
    wmap = (state.get('weights') if isinstance(state, dict) else None) or {}
    weights = [float(wmap.get(nm, 1.0)) for nm in names]
    qtoks = [t for t in (query or 'skill routing').split() if t]
    advice = advice_from_context(names, token_map, qtoks)
    if skill and skill in names:
        weights = exp4_update(weights, advice, names.index(skill), reward)
    s = sum(max(EPS, w) for w in weights) or float(len(names))
    qmix = [max(EPS, w) / s for w in weights]
    p = mixed_p(qmix, advice)
    top = names[max(range(len(p)), key=lambda i: p[i])] if p else None
    out = {
        'ts': time.time(),
        'n': len(names),
        'gamma': GAMMA,
        'query_tokens': qtoks[:16],
        'top1': top,
        'p_top': round(max(p) if p else 0.0, 6),
        'weights': {names[i]: weights[i] for i in range(len(names))},
        'p': {names[i]: p[i] for i in range(len(names))},
        'alarm': False,
    }
    try:
        _atomic_write_json(cache / 'routing-exp4-state.json', out)
    except Exception:
        pass
    return out


def self_test():
    failures = []
    try:
        n = 3
        advice = [[1,0,0],[0,1,0],[0,0,1]]
        w = [1.0, 1.0, 1.0]
        w2 = exp4_update(w, advice, 0, 1.0)
        assert w2[0] > w2[1] and w2[0] > w2[2]
        s = sum(w2)
        q = [x/s for x in w2]
        p = mixed_p(q, advice)
        assert abs(sum(p) - 1.0) < 1e-9
        assert all(x >= GAMMA / n - 1e-12 for x in p)
    except Exception as e:
        failures.append(f'update: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / 'skill-beta-state.json').write_text(json.dumps({
                'a': {'alpha': 2, 'beta': 1}, 'b': {'alpha': 1, 'beta': 2}
            }))
            r = run(cache=d, query='bandit', skill='a', reward=1.0)
            assert (d / 'routing-exp4-state.json').exists()
            json.dumps(r)
    except Exception as e:
        failures.append(f'io: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--query', default='skill routing')
    ap.add_argument('--skill', default=None)
    ap.add_argument('--reward', type=float, default=0.0)
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        r = run(query=args.query, skill=args.skill, reward=args.reward)
        print(json.dumps({k: v for k, v in r.items() if k != 'weights'}, indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
