#!/usr/bin/env python3
"""routing-skill-percolation.py — giant-component percolation of the Jaccard skill graph.

Scan Jaccard thresholds; record giant fraction and Molloy–Reed kappa=<k^2>/<k>.
Operating edge if J>=0.15 (BM25 token Jaccard; 0.35 fragments the graph).
Alarm FRAGMENTED if giant_frac < 0.5; CLIQUE if giant_frac==1 and mean_deg > 3 log n.
Giant component exists (configuration-model) iff kappa > 2.

Source: van der Hofstad, Random Graphs and Complex Networks (percolation / giant);
Molloy–Reed criterion.
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

# 0.35 is too aggressive for BM25 token Jaccard (mean_deg ~ 0.17, kappa << 2).
# 0.15 sits near the Molloy–Reed crossing for this corpus (see T_star in output).
OPERATING = 0.15
CURVE_THRESHOLDS = (
    0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.22, 0.25, 0.30, 0.35, 0.50, 0.70, 0.90,
)


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


def molloy_reed(adj):
    """Configuration-model giant-component criterion: kappa = <k^2>/<k>.

    A giant component exists (w.h.p. in the configuration model) iff kappa > 2.
    Isolated vertices contribute k=0; if mean_k==0 then kappa=0 (no giant).
    """
    n = len(adj)
    if n == 0:
        return 0.0, 0.0, 0.0
    degs = [len(v) for v in adj.values()]
    mean_k = sum(degs) / n
    mean_k2 = sum(d * d for d in degs) / n
    kappa = (mean_k2 / mean_k) if mean_k > EPS else 0.0
    return mean_k, mean_k2, kappa


def t_star_from_curve(curve):
    """T* := interpolated T where kappa crosses 2 from above as T increases.

    Returns the last downward crossing, else max T with kappa>=2, else None.
    """
    if not curve:
        return None
    crossing = None
    last_above = None
    prev = None
    for pt in curve:
        k = float(pt.get('kappa') or 0.0)
        t = float(pt.get('threshold') or 0.0)
        if k >= 2.0:
            last_above = t
        if prev is not None:
            pk = float(prev['kappa'])
            pt_t = float(prev['threshold'])
            if pk >= 2.0 and k < 2.0:
                dk = pk - k
                frac = ((pk - 2.0) / dk) if dk > EPS else 0.0
                crossing = pt_t + (t - pt_t) * frac
        prev = pt
    if crossing is not None:
        return round(crossing, 6)
    if last_above is not None:
        return last_above
    return None


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
    for t in CURVE_THRESHOLDS:
        adj = graph_at(token_map, t)
        gf, gs = giant_frac(adj)
        mean_k, mean_k2, kappa = molloy_reed(adj)
        curve.append({
            'threshold': t,
            'giant_frac': round(gf, 6),
            'giant_size': gs,
            'mean_deg': round(mean_k, 4),
            'mean_k2': round(mean_k2, 4),
            'kappa': round(kappa, 6),
            'molloy_reed_giant': kappa > 2.0,
        })
    adj = graph_at(token_map, OPERATING)
    gf, gs = giant_frac(adj)
    mean_k, mean_k2, kappa = molloy_reed(adj)
    t_star = t_star_from_curve(curve)
    reason = 'ok'
    alarm = False
    if gf < 0.5:
        reason, alarm = 'FRAGMENTED', True
    elif abs(gf - 1.0) < 1e-12 and mean_k > 3.0 * math.log(max(n, 2)):
        reason, alarm = 'CLIQUE', True
    rationale = (
        'Molloy-Reed: a giant component exists in the configuration model iff '
        'kappa=<k^2>/<k> > 2. BM25 token Jaccard at 0.35 yields mean_deg ~0.17 '
        'so kappa << 2 (correctly FRAGMENTED). Operating threshold 0.15 is chosen '
        'to sit near the kappa=2 crossing for this description-token graph; '
        'T_star is the interpolated threshold where kappa crosses 2.'
    )
    return {
        'ts': time.time(),
        'n_skills': n,
        'operating_threshold': OPERATING,
        'giant_frac': round(gf, 6),
        'giant_size': gs,
        'mean_degree': round(mean_k, 4),
        'mean_k2': round(mean_k2, 4),
        'kappa': round(kappa, 6),
        'molloy_reed_giant': kappa > 2.0,
        'T_star': t_star,
        'molloy_reed_rationale': rationale,
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
        # complete graph K_4: k=3, k^2=9, kappa=9/3=3 > 2
        k4 = {f'n{i}': set(f'n{j}' for j in range(4) if j != i) for i in range(4)}
        _mk, _mk2, kap = molloy_reed(k4)
        assert abs(kap - 3.0) < 1e-9, kap
        assert abs(OPERATING - 0.15) < 1e-12
        # T* interpolation: kappa 3 -> 1 between 0.1 and 0.2
        ts = t_star_from_curve([
            {'threshold': 0.1, 'kappa': 3.0},
            {'threshold': 0.2, 'kappa': 1.0},
        ])
        assert ts is not None
        assert abs(ts - 0.15) < 1e-6, ts
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
