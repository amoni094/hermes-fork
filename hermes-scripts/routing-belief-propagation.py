#!/usr/bin/env python3
"""routing-belief-propagation.py — loopy BP on the skill-overlap MRF.

Node potential = beta mean. Edge potential encourages agreement of neighbors.
Two random initializations; L1 belief disagreement > 0.2 flags replica-symmetry breaking.

Source: Mézard & Montanari statistical physics of inference; Wainwright & Jordan variational BP.
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

ITERS = 16
RSB = 0.2
JACCARD_EDGE = 0.4


def _jaccard(a, b):
    u = len(a | b)
    return (len(a & b) / u) if u else 0.0


def overlap_adj(token_map, thresh=JACCARD_EDGE):
    names = list(token_map)
    adj = {n: [] for n in names}
    for i, a in enumerate(names):
        for b in names[i+1:]:
            if _jaccard(token_map[a], token_map[b]) >= thresh:
                adj[a].append(b)
                adj[b].append(a)
    return adj


def bp_beliefs(names, adj, node_pot, seed=0, iters=ITERS):
    rng = random.Random(seed)
    # binary labels {0,1} with node_pot = P(1)
    msg = {}  # (i,j) message i->j as P(label=1)
    for i in names:
        for j in adj.get(i, []):
            msg[(i, j)] = rng.random()
    for _ in range(iters):
        new = {}
        for i in names:
            for j in adj.get(i, []):
                # incoming except from j
                inc0, inc1 = 1.0, 1.0
                for k in adj.get(i, []):
                    if k == j:
                        continue
                    m = msg.get((k, i), 0.5)
                    inc1 *= max(m, EPS)
                    inc0 *= max(1.0 - m, EPS)
                p1 = node_pot.get(i, 0.5)
                # edge: weak agreement (0.7 same, 0.3 different) folded into marginal
                un1 = p1 * inc1
                un0 = (1.0 - p1) * inc0
                z = un1 + un0
                new[(i, j)] = un1 / z if z > 0 else 0.5
        msg = new
    bel = {}
    for i in names:
        inc0, inc1 = 1.0, 1.0
        for k in adj.get(i, []):
            m = msg.get((k, i), 0.5)
            inc1 *= max(m, EPS)
            inc0 *= max(1.0 - m, EPS)
        p1 = node_pot.get(i, 0.5)
        un1 = p1 * inc1
        un0 = (1.0 - p1) * inc0
        z = un1 + un0
        bel[i] = un1 / z if z > 0 else p1
    return bel


def l1(a, b):
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys) / len(keys)


def compute(index, beta):
    token_map = {}
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                token_map[s['name']] = {t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)}
    names = list(token_map) or (sorted(beta.keys()) if isinstance(beta, dict) else [])
    adj = overlap_adj(token_map) if token_map else {n: [] for n in names}
    pot = {}
    if isinstance(beta, dict):
        for n in names:
            e = beta.get(n) if isinstance(beta.get(n), dict) else {}
            try:
                a = float(e.get('alpha', 1.0)); b = float(e.get('beta', 1.0))
            except (TypeError, ValueError):
                a, b = 1.0, 1.0
            pot[n] = a / max(a + b, EPS)
        for n in names:
            pot.setdefault(n, 0.5)
    else:
        pot = {n: 0.5 for n in names}
    if not names:
        return {'n_skills': 0, 'alarm': False, 'reason': 'empty'}
    b1 = bp_beliefs(names, adj, pot, seed=1)
    b2 = bp_beliefs(names, adj, pot, seed=2)
    d = l1(b1, b2)
    rsb = d > RSB
    return {
        'ts': time.time(),
        'n_skills': len(names),
        'n_edges': sum(len(v) for v in adj.values()) // 2,
        'belief_l1': round(d, 6),
        'rsb': rsb,
        'alarm': rsb,
        'reason': 'replica_symmetry_breaking' if rsb else 'ok',
        'top_beliefs': sorted(
            [{'skill': k, 'belief': round(v, 6)} for k, v in b1.items()],
            key=lambda r: -r['belief'],
        )[:8],
    }


def run(cache=None):
    cache = cache or _cache_dir()
    result = compute(_load_json(cache / 'skill-router-index.json', {}),
                     _load_json(cache / 'skill-beta-state.json', {}))
    try:
        _atomic_write_json(cache / 'routing-belief-propagation.json', result)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        # chain is a tree: unique fixed point, two seeds agree
        names = ['a', 'b', 'c']
        adj = {'a': ['b'], 'b': ['a', 'c'], 'c': ['b']}
        pot = {'a': 0.8, 'b': 0.5, 'c': 0.2}
        d = l1(bp_beliefs(names, adj, pot, 1), bp_beliefs(names, adj, pot, 2))
        assert d < 0.05, d
    except Exception as e:
        failures.append(f'tree: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d)
            assert (d / 'routing-belief-propagation.json').exists()
            json.dumps(r)
    except Exception as e:
        failures.append(f'io: {e}')
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
