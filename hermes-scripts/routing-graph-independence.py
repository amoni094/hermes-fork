#!/usr/bin/env python3
"""routing-graph-independence.py — independence number of the skill-overlap graph.

Graph-feedback regret scales with alpha(G) (independence number), not n.
Greedy alpha-hat via min-degree peeling; alarm if alpha_hat > sqrt(n) (weak structure).

Source: Lattimore-Szepesvari Ch 22; Mannor & Shamir graph bandits.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

JACCARD_EDGE = 0.35


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


def _jaccard(a: set, b: set) -> float:
    u = len(a | b)
    return (len(a & b) / u) if u else 0.0


def overlap_graph(index: dict, thresh: float = JACCARD_EDGE) -> dict:
    skills = index.get('skills') if isinstance(index, dict) else []
    toks = {}
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                toks[s['name']] = {t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)}
    names = list(toks)
    adj = {n: set() for n in names}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if _jaccard(toks[a], toks[b]) >= thresh:
                adj[a].add(b)
                adj[b].add(a)
    return adj


def greedy_independence(adj: dict) -> list:
    """Min-degree greedy independent set (Caro-Wei style)."""
    remaining = {k: set(v) for k, v in adj.items()}
    indep = []
    while remaining:
        node = min(remaining, key=lambda k: (len(remaining[k]), k))
        indep.append(node)
        nbrs = list(remaining[node])
        remaining.pop(node, None)
        for nb in nbrs:
            remaining.pop(nb, None)
            if nb in remaining:
                pass
        for k in list(remaining):
            remaining[k].discard(node)
            for nb in nbrs:
                remaining[k].discard(nb)
    return indep


def graph_feedback_bound(t: int, alpha_hat: int) -> float:
    """O(sqrt(alpha T log n)) proxy with n replaced by max(alpha,2)."""
    a = max(alpha_hat, 1)
    return math.sqrt(a * max(t, 1) * math.log(max(a, 2)))


def compute(index: dict, t: int = 100) -> dict:
    adj = overlap_graph(index)
    n = len(adj)
    n_edges = sum(len(v) for v in adj.values()) // 2
    indep = greedy_independence(adj)
    alpha_hat = len(indep)
    weak = alpha_hat > math.sqrt(max(n, 1))
    return {
        'ts': time.time(),
        'n_nodes': n,
        'n_edges': n_edges,
        'alpha_hat': alpha_hat,
        'sqrt_n': round(math.sqrt(max(n, 1)), 4),
        'graph_feedback_regret_proxy': round(graph_feedback_bound(t, alpha_hat), 4),
        'independent_vs_n': round(alpha_hat / max(n, 1), 4),
        'alarm': weak,
        'reason': 'alpha_hat > sqrt(n) (weak graph structure)' if weak else 'ok',
        'sample_independent_set': indep[:12],
    }


def run(cache: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    index = _load_json(cache / 'skill-router-index.json', {})
    result = compute(index if isinstance(index, dict) else {})
    try:
        _atomic_write_json(cache / 'routing-graph-independence.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    try:
        # complete graph on 3: alpha=1
        idx = {'skills': [
            {'name': 'a', 'tokens': ['x', 'y']},
            {'name': 'b', 'tokens': ['x', 'y']},
            {'name': 'c', 'tokens': ['x', 'y']},
        ]}
        r = compute(idx)
        assert r['alpha_hat'] == 1, r
        assert r['n_edges'] == 3
    except Exception as e:
        failures.append(f'clique: {e}')
    try:
        idx = {'skills': [
            {'name': 'a', 'tokens': ['onlya']},
            {'name': 'b', 'tokens': ['onlyb']},
            {'name': 'c', 'tokens': ['onlyc']},
        ]}
        r = compute(idx)
        assert r['alpha_hat'] == 3, r
        assert r['alarm'] is True
    except Exception as e:
        failures.append(f'empty-graph: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            r = run(cache=Path(td))
            json.dumps(r)
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
