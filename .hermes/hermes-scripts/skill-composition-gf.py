#!/usr/bin/env python3
"""skill-composition-gf.py — ordinary generating function blow-up of skill DAG walks.

A_d = number of length-d walks. Radius of convergence ~ 1/spectral_radius ~ 1/max_outdeg.
Alarm if walks at depth 6 exceed 1e6 (combinatorial explosion of skill stacks).

Source: Flajolet & Sedgewick, Analytic Combinatorics (transfer / singularity).
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

DEPTH = 6
BLOW = 1e6


def adj_from_lattice(lattice, index):
    adj = defaultdict(list)
    if isinstance(lattice, dict):
        edges = lattice.get('edges') or []
        if isinstance(edges, list):
            for e in edges:
                if isinstance(e, (list, tuple)) and len(e) >= 2:
                    adj[str(e[0])].append(str(e[1]))
                elif isinstance(e, dict):
                    u, v = e.get('src') or e.get('from'), e.get('dst') or e.get('to')
                    if u and v:
                        adj[str(u)].append(str(v))
        concepts = lattice.get('concepts') or []
        if isinstance(concepts, list):
            for c in concepts:
                if isinstance(c, dict):
                    members = [str(x) for x in (c.get('skills') or [])]
                    for i, u in enumerate(members):
                        for v in members[i+1:]:
                            adj[u].append(v)
    # fallback: token-subset edges (A -> B if tokens A subset tokens B, A!=B)
    token_map = {}
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                token_map[s['name']] = {t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)}
    names = list(token_map)
    for a in names:
        ta = token_map[a]
        if not ta:
            continue
        for b in names:
            if a == b:
                continue
            tb = token_map[b]
            if ta < tb:  # proper subset
                adj[a].append(b)
    # unique
    return {k: sorted(set(v)) for k, v in adj.items()}


def walk_counts(adj, depth=DEPTH):
    nodes = set(adj)
    for vs in adj.values():
        nodes.update(vs)
    if not nodes:
        return [0] * (depth + 1), 0
    counts = [0] * (depth + 1)
    counts[0] = len(nodes)
    cur = {n: 1.0 for n in nodes}
    max_out = max((len(adj.get(n, [])) for n in nodes), default=0)
    for d in range(1, depth + 1):
        nxt = defaultdict(float)
        total = 0.0
        for u, c in cur.items():
            for v in adj.get(u, []):
                nxt[v] += c
                total += c
        counts[d] = total
        cur = nxt
        if total > BLOW * 10:
            break
    return counts, max_out


def compute(lattice, index):
    adj = adj_from_lattice(lattice if isinstance(lattice, dict) else {},
                           index if isinstance(index, dict) else {})
    counts, max_out = walk_counts(adj)
    c6 = counts[DEPTH] if len(counts) > DEPTH else 0
    radius = (1.0 / max_out) if max_out else 1.0
    alarm = c6 > BLOW
    return {
        'ts': time.time(),
        'n_nodes': len(set(adj) | {x for vs in adj.values() for x in vs}),
        'max_outdeg': max_out,
        'radius_of_convergence_bound': round(radius, 6),
        'walks_by_depth': [int(c) if c < 1e18 else int(1e18) for c in counts],
        'walks_depth6': int(min(c6, 1e18)),
        'alarm': alarm,
        'reason': 'combinatorial_blowup' if alarm else 'ok',
    }


def run(cache=None):
    cache = cache or _cache_dir()
    result = compute(_load_json(cache / 'concept-lattice.json', {}),
                     _load_json(cache / 'skill-router-index.json', {}))
    try:
        _atomic_write_json(cache / 'skill-composition-gf.json', result)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        chain = {'a': ['b'], 'b': ['c'], 'c': []}
        c, mx = walk_counts(chain, 3)
        assert mx == 1
        assert c[1] == 2 and c[2] == 1 and c[3] == 0
        binom = {'r': ['l', 'x'], 'l': ['ll', 'lr'], 'x': ['xl', 'xr']}
        c2, mx2 = walk_counts(binom, 2)
        assert mx2 == 2
        assert c2[1] >= 6
    except Exception as e:
        failures.append(f'walks: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d)
            assert (d / 'skill-composition-gf.json').exists()
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
