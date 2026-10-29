#!/usr/bin/env python3
"""Locally-fair PageRank on the skill graph (Gleich et al.)."""
from __future__ import annotations

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'fair-pagerank.json'
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
        return None, {'status': 'insufficient_data', 'reason': 'skill-graph.json missing'}
    try:
        g = json.loads(graph_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None, {'status': 'insufficient_data', 'reason': 'skill-graph.json missing'}
    if not isinstance(g, dict) or int(g.get('n_nodes', 0) or 0) == 0:
        return None, {'status': 'insufficient_data', 'reason': 'empty graph'}
    return g, None


def _nodes_from_graph(g: dict) -> list:
    names = []
    for n in g.get('nodes') or []:
        if isinstance(n, str):
            names.append(n)
        elif isinstance(n, dict):
            nid = n.get('id') or n.get('name') or n.get('skill')
            if nid:
                names.append(str(nid))
    return [n for n in names if n]


def adjacency_from_edges(edges) -> dict:
    adj = defaultdict(dict)
    for e in edges or []:
        src = dst = None
        w = 1.0
        if isinstance(e, dict):
            src = e.get('src') or e.get('source') or e.get('from') or e.get('u')
            dst = e.get('dst') or e.get('target') or e.get('to') or e.get('v')
            try:
                w = float(e.get('weight', 1) or 1)
            except (TypeError, ValueError):
                w = 1.0
        elif isinstance(e, (list, tuple)) and len(e) >= 2:
            src, dst = e[0], e[1]
            if len(e) > 2:
                try:
                    w = float(e[2])
                except (TypeError, ValueError):
                    w = 1.0
        if not src or not dst:
            continue
        src, dst = str(src), str(dst)
        adj[src][dst] = adj[src].get(dst, 0.0) + w
        adj[dst][src] = adj[dst].get(src, 0.0) + w
    return adj


def pagerank(nodes, adj, damping=0.85, iters=40):
    n = len(nodes)
    if n == 0:
        return {}
    idx = {u: i for i, u in enumerate(nodes)}
    pr = [1.0 / n] * n
    for _ in range(iters):
        nxt = [(1.0 - damping) / n] * n
        for i, u in enumerate(nodes):
            dests = adj.get(u) or {}
            tw = sum(dests.values()) if dests else 0.0
            if tw <= 0:
                share = damping * pr[i] / n
                for j in range(n):
                    nxt[j] += share
            else:
                for v, w in dests.items():
                    j = idx.get(v)
                    if j is not None:
                        nxt[j] += damping * pr[i] * (w / tw)
        pr = nxt
    return {nodes[i]: pr[i] for i in range(n)}


def fair_adjust(pr, groups):
    if not pr:
        return {}
    by = defaultdict(list)
    for u, p in pr.items():
        by[groups.get(u, 'default')].append((u, p))
    out = dict(pr)
    for g, items in by.items():
        if not items:
            continue
        mean = sum(p for _, p in items) / len(items)
        for u, p in items:
            out[u] = 0.5 * p + 0.5 * mean
    s = sum(out.values()) or 1.0
    return {u: v / s for u, v in out.items()}


def group_of(name):
    return name.split('-')[0] if name else 'default'


def run(graph_path=None):
    gp = Path(graph_path) if graph_path is not None else GRAPH_PATH
    g, err = _load_graph(gp)
    if err is not None:
        err.update({'n_nodes': 0, 'n_edges': 0, 'scores': {}, 'ts': _now()})
        return err
    nodes = _nodes_from_graph(g)
    adj = adjacency_from_edges(g.get('edges') or [])
    for u in list(adj.keys()):
        if u not in nodes:
            nodes.append(u)
    for u in nodes:
        adj.setdefault(u, {})
    if not nodes:
        return {
            'status': 'insufficient_data',
            'reason': 'empty graph',
            'n_nodes': 0,
            'n_edges': 0,
            'scores': {},
            'ts': _now(),
        }
    pr = pagerank(nodes, adj)
    groups = {u: group_of(u) for u in nodes}
    fair = fair_adjust(pr, groups)
    ranked = sorted(fair.items(), key=lambda kv: -kv[1])
    return {
        'status': 'ok',
        'n_nodes': len(nodes),
        'n_edges': len(g.get('edges') or []),
        'graph_source': str(gp),
        'top': ranked[:12],
        'scores': {k: v for k, v in ranked},
        'ts': _now(),
    }


def _self_test() -> int:
    empty = run(graph_path=Path('/nonexistent/skill-graph.json'))
    assert empty['status'] == 'insufficient_data'
    assert empty.get('reason') == 'skill-graph.json missing'
    td = Path(tempfile.mkdtemp(prefix='fpr-%s-' % uuid.uuid4().hex[:8]))
    try:
        tmpg = td / 'skill-graph.json'
        payload = {
            'n_nodes': 3,
            'n_edges': 2,
            'nodes': [{'id': 'a', 'degree': 1}, {'id': 'b', 'degree': 2}, {'id': 'c', 'degree': 1}],
            'edges': [{'src': 'a', 'dst': 'b', 'weight': 1}, {'src': 'b', 'dst': 'c', 'weight': 2}],
        }
        tmpg.write_text(json.dumps(payload), encoding='utf-8')
        r = run(graph_path=tmpg)
        assert r['status'] == 'ok', r
        assert r['n_nodes'] == 3
        assert abs(sum(r['scores'].values()) - 1.0) < 1e-6
        empty_g = td / 'empty.json'
        empty_g.write_text(json.dumps({'n_nodes': 0, 'nodes': [], 'edges': []}), encoding='utf-8')
        e2 = run(graph_path=empty_g)
        assert e2['status'] == 'insufficient_data'
        print('[fair-pagerank-skill-scorer] --self-test PASS n=%s' % r['n_nodes'])
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
            print('[fair-pagerank-skill-scorer] --self-test FAIL: %s' % exc)
            sys.exit(1)
    try:
        r = run()
        if r.get('status') != 'insufficient_data':
            _atomic_write(OUT_PATH, r)
        slim = {k: r[k] for k in r if k != 'scores'}
        print(json.dumps(slim))
    except Exception:
        pass


if __name__ == '__main__':
    main()
