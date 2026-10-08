#!/usr/bin/env python3
"""routing-graph-bandit-update.py — graph-structured bandit credit on the skill lattice.

On skill success, propagate alpha credit to neighbors at hop d<=2:
  neighbor_credit = base_credit * (0.5 ** hop_distance)

Source: Lattimore & Szepesvari, Bandit Algorithms Ch 22 (graph feedback).
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

MAX_HOP = 2
DECAY = 0.5
JACCARD_EDGE = 0.4
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


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    u = len(a | b)
    return (len(a & b) / u) if u else 0.0


def build_graph(lattice: dict, index: dict, extra_edges=None) -> dict:
    """Undirected adjacency: skill -> list of neighbors."""
    adj = defaultdict(set)
    extra_edges = extra_edges or []
    for a, b in extra_edges:
        adj[a].add(b)
        adj[b].add(a)
    # lattice: concepts may list members; connect co-members that look like skills
    concepts = []
    if isinstance(lattice, dict):
        concepts = lattice.get('concepts') or lattice.get('nodes') or []
        edges = lattice.get('edges') or lattice.get('graph') or []
        if isinstance(edges, list):
            for e in edges:
                if isinstance(e, (list, tuple)) and len(e) >= 2:
                    adj[str(e[0])].add(str(e[1]))
                    adj[str(e[1])].add(str(e[0]))
                elif isinstance(e, dict):
                    u, v = e.get('src') or e.get('from'), e.get('dst') or e.get('to')
                    if u and v:
                        adj[str(u)].add(str(v))
                        adj[str(v)].add(str(u))
    if isinstance(concepts, list):
        for c in concepts:
            members = []
            if isinstance(c, dict):
                members = c.get('skills') or c.get('skill_names') or []
            for i, u in enumerate(members):
                for v in members[i + 1:]:
                    adj[str(u)].add(str(v))
                    adj[str(v)].add(str(u))
    # token-overlap edges from skill-router-index
    skills = []
    if isinstance(index, dict):
        skills = index.get('skills') or []
    token_map = {}
    if isinstance(skills, list):
        for s in skills:
            if not isinstance(s, dict):
                continue
            name = s.get('name')
            toks = s.get('tokens') or []
            if name:
                token_map[str(name)] = set(t.lower() for t in toks if isinstance(t, str))
    names = list(token_map)
    for i, a in enumerate(names):
        ta = token_map[a]
        if not ta:
            continue
        for b in names[i + 1:]:
            tb = token_map[b]
            if tb and _jaccard(ta, tb) >= JACCARD_EDGE:
                adj[a].add(b)
                adj[b].add(a)
    return {k: sorted(v) for k, v in adj.items()}


def hop_credits(adj: dict, source: str, base: float = 1.0, max_hop: int = MAX_HOP) -> dict:
    """BFS credits: source gets base; hop d gets base * (0.5 ** d)."""
    credits = {source: base}
    q = deque([(source, 0)])
    seen = {source}
    while q:
        node, dist = q.popleft()
        if dist >= max_hop:
            continue
        for nb in adj.get(node, []):
            if nb in seen:
                continue
            seen.add(nb)
            nd = dist + 1
            credits[nb] = base * (DECAY ** nd)
            q.append((nb, nd))
    return credits


def apply_credits(beta_state: dict, credits: dict) -> dict:
    out = dict(beta_state) if isinstance(beta_state, dict) else {}
    for skill, cred in credits.items():
        entry = dict(out.get(skill) or {'alpha': 1.0, 'beta': 1.0})
        try:
            a = float(entry.get('alpha', 1.0))
        except (TypeError, ValueError):
            a = 1.0
        entry['alpha'] = a + float(cred)
        if 'beta' not in entry:
            entry['beta'] = 1.0
        out[skill] = entry
    return out


def snapshot_beta(cache: Path) -> dict:
    cur = _load_json(cache / 'skill-beta-state.json', {})
    prev_path = cache / 'skill-beta-state.prev.json'
    prev = _load_json(prev_path, {})
    return cur if isinstance(cur, dict) else {}, prev if isinstance(prev, dict) else {}


def successes_from_delta(cur: dict, prev: dict) -> list:
    """Skills whose alpha increased since prev snapshot."""
    hits = []
    for k, entry in cur.items():
        if not isinstance(entry, dict):
            continue
        try:
            a_now = float(entry.get('alpha', 1.0))
        except (TypeError, ValueError):
            continue
        old = prev.get(k) or {}
        try:
            a_old = float(old.get('alpha', 1.0)) if isinstance(old, dict) else 1.0
        except (TypeError, ValueError):
            a_old = 1.0
        delta = a_now - a_old
        if delta > EPS:
            hits.append((k, delta))
    return hits


def run(cache: Path | None = None, skill: str | None = None, credit: float = 1.0,
        extra_edges=None, from_delta: bool = False) -> dict:
    cache = cache or _cache_dir()
    lattice = _load_json(cache / 'concept-lattice.json', {})
    index = _load_json(cache / 'skill-router-index.json', {})
    adj = build_graph(lattice if isinstance(lattice, dict) else {},
                      index if isinstance(index, dict) else {},
                      extra_edges=extra_edges)
    beta_path = cache / 'skill-beta-state.json'
    beta = _load_json(beta_path, {})
    if not isinstance(beta, dict):
        beta = {}
    events = []
    if skill:
        events.append((skill, float(credit)))
    if from_delta:
        cur, prev = snapshot_beta(cache)
        events.extend(successes_from_delta(cur if cur else beta, prev))
    applied = []
    for src, cred in events:
        credits = hop_credits(adj, src, base=float(cred))
        # source already counted in beta if from_delta; only propagate neighbors
        if from_delta:
            credits.pop(src, None)
        beta = apply_credits(beta, credits)
        applied.append({'source': src, 'base': cred, 'credits': credits})
    if applied:
        _atomic_write_json(beta_path, beta)
    try:
        _atomic_write_json(cache / 'skill-beta-state.prev.json',
                           _load_json(beta_path, beta))
    except Exception:
        pass
    result = {
        'ts': time.time(),
        'n_events': len(applied),
        'n_graph_nodes': len(adj),
        'applied': applied,
        'note': 'no-op' if not applied else 'updated',
    }
    try:
        _atomic_write_json(cache / 'routing-graph-bandit.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    # A-B-C chain: A success => B 0.5, C 0.25
    try:
        extra = [('A', 'B'), ('B', 'C')]
        adj = build_graph({}, {}, extra_edges=extra)
        credits = hop_credits(adj, 'A', base=1.0)
        assert abs(credits['A'] - 1.0) < 1e-12
        assert abs(credits['B'] - 0.5) < 1e-12, credits
        assert abs(credits['C'] - 0.25) < 1e-12, credits
        beta = apply_credits({'A': {'alpha': 1.0, 'beta': 1.0},
                              'B': {'alpha': 1.0, 'beta': 1.0},
                              'C': {'alpha': 1.0, 'beta': 1.0}}, credits)
        assert abs(beta['B']['alpha'] - 1.5) < 1e-12
        assert abs(beta['C']['alpha'] - 1.25) < 1e-12
    except Exception as e:
        failures.append(f'hop-credit: {e}')
    # isolated write, no production mutation
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / 'skill-beta-state.json').write_text(json.dumps({
                'A': {'alpha': 1.0, 'beta': 1.0},
                'B': {'alpha': 1.0, 'beta': 1.0},
                'C': {'alpha': 1.0, 'beta': 1.0},
            }))
            r = run(cache=d, skill='A', credit=1.0, extra_edges=[('A', 'B'), ('B', 'C')])
            st = json.loads((d / 'skill-beta-state.json').read_text())
            assert abs(st['B']['alpha'] - 1.5) < 1e-9, st
            assert abs(st['C']['alpha'] - 1.25) < 1e-9, st
            json.dumps(r)
    except Exception as e:
        failures.append(f'atomic: {e}')
    # missing files
    try:
        with tempfile.TemporaryDirectory() as td:
            r = run(cache=Path(td), skill='Z', credit=1.0)
            assert r['n_events'] == 1
    except Exception as e:
        failures.append(f'missing: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--skill', default=None)
    ap.add_argument('--credit', type=float, default=1.0)
    ap.add_argument('--from-beta-delta', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        r = run(skill=args.skill, credit=args.credit, from_delta=args.from_beta_delta or not args.skill)
        print(json.dumps(r, indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
