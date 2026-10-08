#!/usr/bin/env python3
"""memory-ontology-topology.py — Ghrist applied topology over the skill ontology.

BFS components / diameter, DFS directed cycles, Bron-Kerbosch maximal cliques.
Compares to prior snapshot; informational alarms on isolation, new cycles,
diameter spikes. Stdlib only.

Usage:
  python3 memory-ontology-topology.py
  python3 memory-ontology-topology.py --self-test
"""
from __future__ import annotations

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import random
import sys
from collections import deque
from datetime import datetime, timezone
from itertools import combinations

DIAMETER_CAP = 50
CLIQUE_CAP = 30


def _cache_dir() -> Path:
    override = os.environ.get('HERMES_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        try:
            tmp = path.with_suffix('.tmp')
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _load_json(path: Path, default):
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return default
    except Exception:
        return default


def _intent_node(intent) -> str:
    if intent is None:
        return ''
    if isinstance(intent, (list, tuple)):
        parts = [str(x).strip() for x in intent if str(x).strip()]
        return '+'.join(parts)
    return str(intent).strip()


def _as_list(obj) -> list:
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ('concepts', 'candidates', 'triples', 'edges', 'items', 'nodes'):
            v = obj.get(k)
            if isinstance(v, list):
                return v
        return []
    return []


def parse_lattice_concepts(lattice) -> list[dict]:
    concepts = []
    for c in _as_list(lattice if not isinstance(lattice, dict) else lattice.get('concepts', lattice)):
        if not isinstance(c, dict):
            continue
        intent = c.get('intent')
        node = _intent_node(intent)
        if not node:
            continue
        members = c.get('members', c.get('extent', []))
        if not isinstance(members, list):
            members = []
        concepts.append({'intent': node, 'members': [str(m) for m in members]})
    return concepts


def parse_taxonomy_edges(tax) -> list[tuple[str, str]]:
    edges = []
    items = _as_list(tax)
    if isinstance(tax, dict) and not items:
        items = _as_list(tax.get('candidates') or tax.get('edges') or tax.get('isa') or [])
    for item in items:
        if not isinstance(item, dict):
            continue
        sub = (item.get('sub') or item.get('child') or item.get('subject')
               or item.get('from') or item.get('src') or item.get('hyponym'))
        sup = (item.get('super') or item.get('parent') or item.get('object')
               or item.get('to') or item.get('dst') or item.get('hypernym'))
        if sub is None or sup is None:
            continue
        s, t = str(sub).strip(), str(sup).strip()
        if s and t and s != t:
            edges.append((s, t))
    return edges


def parse_relation_edges(rel) -> list[tuple[str, str]]:
    edges = []
    items = _as_list(rel if not isinstance(rel, dict) else rel.get('triples', rel))
    for item in items:
        if not isinstance(item, dict):
            continue
        s = str(item.get('subject') or '').strip()
        t = str(item.get('object') or '').strip()
        if s and t and s != t:
            edges.append((s, t))
    return edges


def parse_relation_nodes(rel) -> list[str]:
    nodes = []
    items = _as_list(rel if not isinstance(rel, dict) else rel.get('triples', rel))
    for item in items:
        if not isinstance(item, dict):
            continue
        for k in ('subject', 'object'):
            v = str(item.get(k) or '').strip()
            if v:
                nodes.append(v)
    return nodes


def build_graph(lattice, taxonomy, relations) -> tuple[set[str], list[tuple[str, str]]]:
    """Nodes + directed edges from lattice / taxonomy / triples / co-membership."""
    nodes: set[str] = set()
    directed: list[tuple[str, str]] = []
    concepts = parse_lattice_concepts(lattice)
    for c in concepts:
        if c['intent']:
            nodes.add(c['intent'])
    for s, t in parse_taxonomy_edges(taxonomy):
        nodes.add(s)
        nodes.add(t)
        directed.append((s, t))
    for n in parse_relation_nodes(relations):
        nodes.add(n)
    for s, t in parse_relation_edges(relations):
        nodes.add(s)
        nodes.add(t)
        directed.append((s, t))
    # co-membership: undirected conceptually, emit both directions so DFS can
    # see them as directed; BFS treats edges undirected anyway.
    member_sets = [(c['intent'], set(c['members'])) for c in concepts if c['intent']]
    for (a, ma), (b, mb) in combinations(member_sets, 2):
        if a == b:
            continue
        if ma and mb and (ma & mb):
            directed.append((a, b))
            directed.append((b, a))
    return nodes, directed


def _undirected_adj(nodes: set[str], directed: list[tuple[str, str]]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for s, t in directed:
        if s not in adj:
            adj[s] = set()
        if t not in adj:
            adj[t] = set()
        if s != t:
            adj[s].add(t)
            adj[t].add(s)
    return adj


def _directed_adj(nodes: set[str], directed: list[tuple[str, str]]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for s, t in directed:
        if s not in adj:
            adj[s] = set()
        if t not in adj:
            adj[t] = set()
        if s != t:
            adj[s].add(t)
    return adj


def num_components(nodes: set[str], uadj: dict[str, set[str]]) -> int:
    if not nodes:
        return 0
    seen: set[str] = set()
    count = 0
    for s in nodes:
        if s in seen:
            continue
        count += 1
        q: deque[str] = deque([s])
        seen.add(s)
        while q:
            u = q.popleft()
            for v in uadj.get(u, ()):
                if v not in seen:
                    seen.add(v)
                    q.append(v)
    return count


def _bfs_ecc(src: str, uadj: dict[str, set[str]]) -> int:
    dist = {src: 0}
    q: deque[str] = deque([src])
    far = 0
    while q:
        u = q.popleft()
        for v in uadj.get(u, ()):
            if v not in dist:
                dist[v] = dist[u] + 1
                far = max(far, dist[v])
                q.append(v)
    return far


def graph_diameter(nodes: set[str], uadj: dict[str, set[str]], cap: int = DIAMETER_CAP) -> int | None:
    if not nodes:
        return None
    if len(nodes) == 1:
        return 0
    sources: list[str]
    nodelist = list(nodes)
    if len(nodelist) > cap:
        sources = random.sample(nodelist, cap)
    else:
        sources = nodelist
    return max(_bfs_ecc(s, uadj) for s in sources)


def cycle_detected(dadj: dict[str, set[str]]) -> bool:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in dadj}

    def dfs(u: str) -> bool:
        color[u] = GRAY
        for v in dadj.get(u, ()):
            cv = color.get(v, WHITE)
            if cv == GRAY:
                return True
            if cv == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    for n in list(dadj):
        if color.get(n, WHITE) == WHITE:
            if dfs(n):
                return True
    return False


def bron_kerbosch_count(nodes: set[str], uadj: dict[str, set[str]], cap: int = CLIQUE_CAP) -> int | None:
    if len(nodes) > cap:
        return None
    if not nodes:
        return 0
    cliques = 0

    def bk(r: set[str], p: set[str], x: set[str]) -> None:
        nonlocal cliques
        if not p and not x:
            if r:
                cliques += 1
            return
        pivot = next(iter(p | x))
        for v in list(p - uadj.get(pivot, set())):
            nbrs = uadj.get(v, set())
            bk(r | {v}, p & nbrs, x & nbrs)
            p.remove(v)
            x.add(v)

    bk(set(), set(nodes), set())
    return cliques


def avg_degree(nodes: set[str], uadj: dict[str, set[str]]) -> float:
    n = len(nodes)
    if n == 0:
        return 0.0
    deg_sum = sum(len(uadj.get(u, ())) for u in nodes)
    return deg_sum / float(n)


def n_undirected_edges(uadj: dict[str, set[str]]) -> int:
    return sum(len(nbrs) for nbrs in uadj.values()) // 2


def analyze_graph(nodes: set[str], directed: list[tuple[str, str]]) -> dict:
    nodes = set(nodes)
    for s, t in directed:
        nodes.add(s)
        nodes.add(t)
    uadj = _undirected_adj(nodes, directed)
    dadj = _directed_adj(nodes, directed)
    n_nodes = len(nodes)
    n_edges = n_undirected_edges(uadj)
    return {
        'n_nodes': n_nodes,
        'n_edges': n_edges,
        'num_components': num_components(nodes, uadj),
        'diameter': graph_diameter(nodes, uadj),
        'avg_degree': avg_degree(nodes, uadj),
        'cycle_detected': cycle_detected(dadj),
        'n_cliques': bron_kerbosch_count(nodes, uadj),
    }


def compare_prior(metrics: dict, prior: dict) -> list[str]:
    alarms: list[str] = []
    if not isinstance(prior, dict) or not prior:
        return alarms
    try:
        prev_c = prior.get('num_components')
        now_c = metrics.get('num_components')
        if prev_c is not None and now_c is not None and int(now_c) > int(prev_c):
            alarms.append('num_components_increased')
    except (TypeError, ValueError):
        pass
    try:
        prev_cyc = bool(prior.get('cycle_detected'))
        now_cyc = bool(metrics.get('cycle_detected'))
        if now_cyc and not prev_cyc:
            alarms.append('cycle_introduced')
    except Exception:
        pass
    try:
        prev_d = prior.get('diameter')
        now_d = metrics.get('diameter')
        if prev_d is not None and now_d is not None:
            pd, nd = float(prev_d), float(now_d)
            if pd > 0 and nd > pd * 1.5:
                alarms.append('diameter_spike')
    except (TypeError, ValueError):
        pass
    return alarms


def run(cache: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    try:
        lattice = _load_json(cache / 'concept-lattice.json', {})
        taxonomy = _load_json(cache / 'taxonomy-candidates.json', {})
        relations = _load_json(cache / 'relation-triples.json', {})
        prior = _load_json(cache / 'ontology-topology-state.json', {})
        nodes, directed = build_graph(lattice, taxonomy, relations)
        metrics = analyze_graph(nodes, directed)
        alarms = compare_prior(metrics, prior if isinstance(prior, dict) else {})
        payload = {
            'ts': _now_iso(),
            'n_nodes': metrics['n_nodes'],
            'n_edges': metrics['n_edges'],
            'num_components': metrics['num_components'],
            'diameter': metrics['diameter'],
            'avg_degree': metrics['avg_degree'],
            'cycle_detected': metrics['cycle_detected'],
            'n_cliques': metrics['n_cliques'],
            'alarms': alarms,
        }
        _atomic_write_json(cache / 'ontology-topology.json', payload)
        state = {
            'ts': payload['ts'],
            'n_nodes': payload['n_nodes'],
            'n_edges': payload['n_edges'],
            'num_components': payload['num_components'],
            'diameter': payload['diameter'],
            'avg_degree': payload['avg_degree'],
            'cycle_detected': payload['cycle_detected'],
            'n_cliques': payload['n_cliques'],
        }
        _atomic_write_json(cache / 'ontology-topology-state.json', state)
        if alarms:
            _atomic_write_json(cache / 'wave22ol-topology-alarm.json', {
                'ts': payload['ts'],
                'kind': 'topology',
                'alarms': alarms,
            })
        return payload
    except Exception:
        payload = {
            'ts': _now_iso(),
            'n_nodes': 0,
            'n_edges': 0,
            'num_components': 0,
            'diameter': None,
            'avg_degree': 0.0,
            'cycle_detected': False,
            'n_cliques': 0,
            'alarms': [],
        }
        try:
            _atomic_write_json(cache / 'ontology-topology.json', payload)
        except Exception:
            pass
        return payload


def self_test() -> int:
    # Component 1: A-B cycle plus C attached; component 2: isolated D.
    # C is listed so the 4-node mock has exactly 2 undirected components.
    nodes = {'A', 'B', 'C', 'D'}
    directed = [('A', 'B'), ('B', 'A'), ('A', 'C')]
    m = analyze_graph(nodes, directed)
    ok = (
        m['num_components'] == 2
        and m['cycle_detected'] is True
        and m['diameter'] in (0, 1, 2)
    )
    empty = analyze_graph(set(), [])
    if empty['num_components'] != 0:
        ok = False
    single = analyze_graph({'X'}, [])
    if not (single['num_components'] == 1 and single['diameter'] == 0 and single['cycle_detected'] is False):
        ok = False
    if ok:
        print('PASS')
        return 0
    print('FAIL metrics=%s' % m)
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Ontology topology health (Ghrist)')
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    try:
        payload = run()
        print(json.dumps({
            'n_nodes': payload.get('n_nodes'),
            'num_components': payload.get('num_components'),
            'cycle_detected': payload.get('cycle_detected'),
            'alarms': payload.get('alarms'),
        }))
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
