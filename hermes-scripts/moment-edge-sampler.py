#!/usr/bin/env python3
"""Moment-guided edge sampling on the skill dependency graph."""
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
import tempfile
import uuid
from datetime import datetime, timezone

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'moment-edge-sample.json'
GRAPH_PATH = CACHE / 'skill-graph.json'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))


def _load_graph(graph_path: Path):
    if not graph_path.exists():
        return None
    try:
        g = json.loads(graph_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(g, dict) or int(g.get('n_nodes', 0) or 0) == 0:
        return None
    return g


def _parse_graph(g: dict):
    nodes = []
    for n in g.get('nodes') or []:
        if isinstance(n, str):
            nodes.append(n)
        elif isinstance(n, dict):
            nid = n.get('id') or n.get('name') or n.get('skill')
            if nid:
                nodes.append(str(nid))
    edges = []
    for e in g.get('edges') or []:
        src = dst = None
        if isinstance(e, dict):
            src = e.get('src') or e.get('source') or e.get('u') or e.get('from')
            dst = e.get('dst') or e.get('target') or e.get('v') or e.get('to')
        elif isinstance(e, (list, tuple)) and len(e) >= 2:
            src, dst = e[0], e[1]
        if src and dst:
            edges.append((str(src), str(dst)))
            if str(src) not in nodes:
                nodes.append(str(src))
            if str(dst) not in nodes:
                nodes.append(str(dst))
    return nodes, edges


def degrees(nodes, edges):
    d = {n: 0 for n in nodes}
    for u, v in edges:
        d[u] = d.get(u, 0) + 1
        d[v] = d.get(v, 0) + 1
    return d


def sample_edges(nodes, edges, k=12, rng=None):
    rng = rng or random.Random(0)
    if not edges:
        return [], degrees(nodes, edges)
    deg = degrees(nodes, edges)
    weights = []
    for u, v in edges:
        w = 1.0 / max(1, deg.get(u, 1) * deg.get(v, 1))
        weights.append(w)
    s = sum(weights) or 1.0
    probs = [w / s for w in weights]
    order = list(range(len(edges)))
    order.sort(key=lambda i: rng.random() / max(1e-12, probs[i]))
    picked = []
    seen = set()
    for i in order:
        e = edges[i]
        key = tuple(sorted(e))
        if key in seen:
            continue
        seen.add(key)
        picked.append({'u': e[0], 'v': e[1], 'w': 1.0 / max(1, deg.get(e[0], 1) * deg.get(e[1], 1))})
        if len(picked) >= k:
            break
    return picked, deg


def run(graph_path=None):
    gp = Path(graph_path) if graph_path is not None else GRAPH_PATH
    g = _load_graph(gp)
    if g is None:
        return {'status': 'insufficient_data'}
    nodes, edges = _parse_graph(g)
    if not nodes:
        return {'status': 'insufficient_data'}
    sampled, deg = sample_edges(nodes, edges)
    avg_d = (sum(deg.values()) / len(deg)) if deg else 0.0
    m2 = (sum(v * v for v in deg.values()) / len(deg)) if deg else 0.0
    return {
        'status': 'ok',
        'ts': _now(),
        'sampled_edges': sampled,
        'nodes': nodes,
        'edges': [{'u': u, 'v': v} for u, v in edges],
        'graph_stats': {
            'n_nodes': len(nodes),
            'n_edges': len(edges),
            'avg_degree': avg_d,
            'second_moment': m2,
        },
    }


def _self_test() -> int:
    empty = run(graph_path=Path('/nonexistent/skill-graph.json'))
    assert empty.get('status') == 'insufficient_data'
    td = Path(tempfile.mkdtemp(prefix='mes-%s-' % uuid.uuid4().hex[:8]))
    try:
        tmpg = td / 'skill-graph.json'
        payload = {
            'n_nodes': 3,
            'n_edges': 2,
            'nodes': [{'id': 'a', 'degree': 1}, {'id': 'b', 'degree': 2}, {'id': 'c', 'degree': 1}],
            'edges': [{'src': 'a', 'dst': 'b', 'weight': 1}, {'src': 'b', 'dst': 'c', 'weight': 1}],
        }
        tmpg.write_text(json.dumps(payload), encoding='utf-8')
        r = run(graph_path=tmpg)
        assert r.get('status') == 'ok', r
        assert r['graph_stats']['n_nodes'] >= 3
        assert r['graph_stats']['n_edges'] >= 2
        assert r['sampled_edges']
        print('[moment-edge-sampler] --self-test PASS n=%s e=%s' % (
            r['graph_stats']['n_nodes'], r['graph_stats']['n_edges']))
        return 0
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print('[moment-edge-sampler] --self-test FAIL: %s' % exc)
            sys.exit(1)
    r = run()
    if r.get('status') == 'insufficient_data':
        print(json.dumps(r))
        return
    slim = {'graph_stats': r['graph_stats'], 'sampled_edges': r['sampled_edges'], 'ts': r['ts']}
    _atomic_write(OUT_PATH, r)
    print(json.dumps({'graph_stats': r['graph_stats'], 'n_sampled': len(r['sampled_edges'])}))


if __name__ == '__main__':
    main()
