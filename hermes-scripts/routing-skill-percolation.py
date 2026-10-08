#!/usr/bin/env python3
"""routing-skill-percolation.py — giant-component percolation of the Jaccard skill graph.

Scan Jaccard thresholds; record giant fraction. Operating edge if J>=0.35.
Alarm FRAGMENTED if giant_frac < 0.5; CLIQUE if giant_frac==1 and mean_deg > 3 log n.

Source: van der Hofstad, Random Graphs and Complex Networks (percolation / giant).
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

OPERATING = 0.35


def _jaccard(a, b):
    u = len(a | b)
    return (len(a & b) / u) if u else 0.0


def giant_frac(adj):
    names = list(adj)
    if not names:
        return 0.0, 0
    seen = set()
    best = 0
    for s in names:
        if s in seen:
            continue
        q = deque([s])
        seen.add(s)
        sz = 0
        while q:
            u = q.popleft()
            sz += 1
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        best = max(best, sz)
    return best / len(names), best


def graph_at(token_map, thresh):
    names = list(token_map)
    adj = {n: set() for n in names}
    for i, a in enumerate(names):
        for b in names[i+1:]:
            if _jaccard(token_map[a], token_map[b]) >= thresh:
                adj[a].add(b)
                adj[b].add(a)
    return adj


def compute(index):
    token_map = {}
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                token_map[s['name']] = {t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)}
    n = len(token_map)
    if n == 0:
        return {'n_skills': 0, 'alarm': False, 'reason': 'empty'}
    curve = []
    for t in (0.1, 0.2, 0.35, 0.5, 0.7, 0.9):
        adj = graph_at(token_map, t)
        gf, gs = giant_frac(adj)
        md = (sum(len(v) for v in adj.values()) / n) if n else 0.0
        curve.append({'threshold': t, 'giant_frac': round(gf, 6), 'giant_size': gs, 'mean_deg': round(md, 4)})
    adj = graph_at(token_map, OPERATING)
    gf, gs = giant_frac(adj)
    md = (sum(len(v) for v in adj.values()) / n) if n else 0.0
    reason = 'ok'
    alarm = False
    if gf < 0.5:
        reason, alarm = 'FRAGMENTED', True
    elif abs(gf - 1.0) < 1e-12 and md > 3.0 * math.log(max(n, 2)):
        reason, alarm = 'CLIQUE', True
    return {
        'ts': time.time(),
        'n_skills': n,
        'operating_threshold': OPERATING,
        'giant_frac': round(gf, 6),
        'giant_size': gs,
        'mean_degree': round(md, 4),
        'alarm': alarm,
        'reason': reason,
        'curve': curve,
    }


def run(cache=None):
    cache = cache or _cache_dir()
    result = compute(_load_json(cache / 'skill-router-index.json', {}))
    try:
        _atomic_write_json(cache / 'routing-skill-percolation.json', result)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        # two disjoint cliques
        tmap = {
            'a1': {'x', 'y'}, 'a2': {'x', 'y', 'z'},
            'b1': {'p', 'q'}, 'b2': {'p', 'q', 'r'},
        }
        adj = graph_at(tmap, 0.3)
        gf, gs = giant_frac(adj)
        assert gf <= 0.5 + 1e-9, (gf, gs)
        # complete overlap
        tmap2 = {f's{i}': {'shared', 'tok'} for i in range(6)}
        gf2, _ = giant_frac(graph_at(tmap2, 0.5))
        assert abs(gf2 - 1.0) < 1e-12
    except Exception as e:
        failures.append(f'giant: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d)
            assert (d / 'routing-skill-percolation.json').exists()
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
