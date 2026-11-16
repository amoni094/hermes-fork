#!/usr/bin/env python3
"""Spectral moment guard: algebraic connectivity (lambda_2) and fragile edges.

Reads cache/skill-graph.json. Computes the Fiedler value of the weighted
Laplacian via shifted power iteration (stdlib only). Ranks edges by the
Fiedler perturbation w*(f_i-f_j)^2, then recomputes lambda_2 after
removing the top candidates. Alarms if lambda_2 < 0.1.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get('HERMES_HOME', '').strip()
    p = Path(env) if env else Path.home() / '.hermes'
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


def _profile_name() -> str:
    profile = os.environ.get('HERMES_PROFILE', '').strip()
    if profile:
        return profile
    raw = os.environ.get('HERMES_HOME', '').strip()
    if raw:
        p = Path(raw)
        if p.parent.name == 'profiles':
            return p.name
    if (_hermes_home() / 'profiles' / 'fork').exists():
        return 'fork'
    return ''


_hermes_base = _hermes_home()
_hermes_profile = _profile_name()
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile else _hermes_base
)
CACHE = _hermes_root / 'cache'
GRAPH_PATH = CACHE / 'skill-graph.json'
OUT_PATH = CACHE / 'spectral-moment-guard.json'

LAMBDA2_ALARM = 0.1
POWER_ITERS = 250
POWER_TOL = 1e-10
FRAGILE_RECOMPUTE = 25
FRAGILE_REPORT = 15


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    with open(lock, 'w', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(str(tmp), str(path))


def _load_graph(graph_path: Path):
    if not graph_path.exists():
        return None, {'status': 'insufficient_data', 'reason': 'skill-graph.json missing'}
    try:
        g = json.loads(graph_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None, {'status': 'insufficient_data', 'reason': 'skill-graph.json unreadable'}
    if not isinstance(g, dict):
        return None, {'status': 'insufficient_data', 'reason': 'skill-graph.json unreadable'}
    return g, None


def _nodes_from_graph(g: dict) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for n in g.get('nodes') or []:
        if isinstance(n, str):
            nid = n
        elif isinstance(n, dict):
            nid = n.get('id') or n.get('name') or n.get('skill')
            nid = str(nid) if nid else ''
        else:
            nid = ''
        if nid and nid not in seen:
            seen.add(nid)
            names.append(nid)
    return names


def _undirected_edges(g: dict, idx: dict[str, int]) -> list[tuple[int, int, float, str, str]]:
    """Unique undirected edges (i<j) with summed weight."""
    acc: dict[tuple[int, int], tuple[float, str, str]] = {}
    for e in g.get('edges') or []:
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
        if src not in idx or dst not in idx or src == dst:
            continue
        i, j = idx[src], idx[dst]
        if i > j:
            i, j = j, i
            src, dst = dst, src
        key = (i, j)
        prev = acc.get(key)
        if prev:
            acc[key] = (prev[0] + w, prev[1], prev[2])
        else:
            acc[key] = (w, src, dst)
    return [(i, j, tw, s, d) for (i, j), (tw, s, d) in acc.items() if tw > 0]


def _adj_from_edges(n: int, edges: list[tuple[int, int, float, str, str]], skip: tuple[int, int] | None = None):
    adj: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    deg = [0.0] * n
    for i, j, w, _s, _d in edges:
        if skip is not None and i == skip[0] and j == skip[1]:
            continue
        adj[i].append((j, w))
        adj[j].append((i, w))
        deg[i] += w
        deg[j] += w
    return adj, deg


def _lap_matvec(adj, deg, x):
    y = [0.0] * len(x)
    for i, nbrs in enumerate(adj):
        s = deg[i] * x[i]
        for j, w in nbrs:
            s -= w * x[j]
        y[i] = s
    return y


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _l2(x):
    return math.sqrt(sum(v * v for v in x))


def algebraic_connectivity(adj, deg, iters: int = POWER_ITERS) -> tuple[float, list[float]]:
    """lambda_2 of Laplacian via (cI-L) power iteration on 1-perp."""
    n = len(deg)
    if n < 2:
        return 0.0, [1.0] * n
    c = max(deg) * 2.0 if deg else 1.0
    if c <= 0:
        c = 1.0
    x = [float(i) - (n - 1) / 2.0 for i in range(n)]
    nrm = _l2(x)
    if nrm <= 0:
        x = [1.0 if i == 0 else -1.0 / (n - 1) for i in range(n)]
        nrm = _l2(x)
    x = [v / nrm for v in x]
    mean = sum(x) / n
    x = [v - mean for v in x]
    nrm = _l2(x) or 1.0
    x = [v / nrm for v in x]
    last = None
    for _ in range(iters):
        lx = _lap_matvec(adj, deg, x)
        y = [c * x[i] - lx[i] for i in range(n)]
        mean = sum(y) / n
        y = [v - mean for v in y]
        nrm = _l2(y)
        if nrm <= 1e-18:
            break
        x = [v / nrm for v in y]
        ray = _dot(x, _lap_matvec(adj, deg, x))
        if last is not None and abs(ray - last) < POWER_TOL:
            return max(0.0, ray), x
        last = ray
    ray = _dot(x, _lap_matvec(adj, deg, x))
    return max(0.0, ray), x


def run(graph_path: Path | None = None) -> dict:
    gp = Path(graph_path) if graph_path is not None else GRAPH_PATH
    g, err = _load_graph(gp)
    if err is not None or g is None:
        payload = err or {'status': 'insufficient_data', 'reason': 'skill-graph.json missing'}
        payload.update({
            'ts': _now(),
            'lambda_2': None,
            'alarm': False,
            'fragile_edges': [],
            'n_nodes': 0,
            'n_edges': 0,
        })
        return payload
    nodes = _nodes_from_graph(g)
    idx = {u: i for i, u in enumerate(nodes)}
    for e in g.get('edges') or []:
        if isinstance(e, dict):
            for k in ('src', 'source', 'from', 'u', 'dst', 'target', 'to', 'v'):
                v = e.get(k)
                if v and str(v) not in idx:
                    idx[str(v)] = len(nodes)
                    nodes.append(str(v))
    n = len(nodes)
    edges = _undirected_edges(g, idx)
    if n < 2 or not edges:
        return {
            'status': 'insufficient_data',
            'reason': 'empty or singleton graph',
            'ts': _now(),
            'lambda_2': 0.0,
            'alarm': True,
            'fragile_edges': [],
            'n_nodes': n,
            'n_edges': len(edges),
        }
    adj, deg = _adj_from_edges(n, edges)
    lam2, fiedler = algebraic_connectivity(adj, deg)
    scored = []
    for i, j, w, s, d in edges:
        drop_proxy = w * (fiedler[i] - fiedler[j]) ** 2
        scored.append((drop_proxy, i, j, w, s, d))
    scored.sort(reverse=True)
    fragile = []
    for drop_proxy, i, j, w, s, d in scored[:FRAGILE_RECOMPUTE]:
        adj2, deg2 = _adj_from_edges(n, edges, skip=(i, j))
        lam2_rm, _ = algebraic_connectivity(adj2, deg2)
        fragile.append({
            'src': s,
            'dst': d,
            'weight': w,
            'fiedler_score': drop_proxy,
            'lambda_2_without': lam2_rm,
            'delta_lambda_2': lam2 - lam2_rm,
        })
    fragile.sort(key=lambda e: -e['delta_lambda_2'])
    fragile = fragile[:FRAGILE_REPORT]
    alarm = lam2 < LAMBDA2_ALARM
    return {
        'status': 'ok',
        'ts': _now(),
        'graph_source': str(gp),
        'n_nodes': n,
        'n_edges': len(edges),
        'lambda_2': lam2,
        'lambda_2_threshold': LAMBDA2_ALARM,
        'alarm': alarm,
        'alarm_reason': 'lambda_2 < 0.1 (poorly connected graph)' if alarm else None,
        'fragile_edges': fragile,
    }


def _self_test() -> int:
    missing = run(graph_path=Path('/nonexistent/skill-graph.json'))
    assert missing['status'] == 'insufficient_data'
    td = Path(tempfile.mkdtemp(prefix=f'smg-{uuid.uuid4().hex[:8]}-'))
    try:
        g = {
            'n_nodes': 6,
            'n_edges': 7,
            'nodes': [{'id': c} for c in 'abcdef'],
            'edges': [
                {'src': 'a', 'dst': 'b', 'weight': 1},
                {'src': 'b', 'dst': 'c', 'weight': 1},
                {'src': 'c', 'dst': 'a', 'weight': 1},
                {'src': 'd', 'dst': 'e', 'weight': 1},
                {'src': 'e', 'dst': 'f', 'weight': 1},
                {'src': 'f', 'dst': 'd', 'weight': 1},
                {'src': 'c', 'dst': 'd', 'weight': 1},
            ],
        }
        p = td / 'skill-graph.json'
        p.write_text(json.dumps(g), encoding='utf-8')
        r = run(graph_path=p)
        assert r['status'] == 'ok', r
        assert r['lambda_2'] > 0.05, r
        assert r['fragile_edges'], r
        top = r['fragile_edges'][0]
        ends = {top['src'], top['dst']}
        assert ends == {'c', 'd'}, top
        g2 = {
            'n_nodes': 4,
            'nodes': [{'id': c} for c in 'abcd'],
            'edges': [
                {'src': 'a', 'dst': 'b', 'weight': 1},
                {'src': 'c', 'dst': 'd', 'weight': 1},
            ],
        }
        p2 = td / 'disc.json'
        p2.write_text(json.dumps(g2), encoding='utf-8')
        d = run(graph_path=p2)
        assert d['lambda_2'] < 0.05, d
        assert d['alarm'] is True
        empty = run(graph_path=td / 'nope.json')
        assert empty['status'] == 'insufficient_data'
        print('[spectral-moment-guard] --self-test PASS lambda_2={:.4f}'.format(r['lambda_2']))
        return 0
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            return _self_test()
        except Exception as exc:
            print(f'[spectral-moment-guard] --self-test FAIL: {exc}')
            return 1
    try:
        r = run()
        _atomic_write(OUT_PATH, r)
        slim = {k: r[k] for k in r if k != 'fragile_edges'}
        slim['n_fragile'] = len(r.get('fragile_edges') or [])
        slim['top_fragile'] = (r.get('fragile_edges') or [None])[0]
        print(json.dumps(slim))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc), 'ts': _now()}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
