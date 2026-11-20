#!/usr/bin/env python3
"""Locally Fair PageRank (LFPR) on the skill graph.

Standard PageRank (damping=0.85) then one-step local fairness:
  score' = score * (1 + eps * (mean_neighbor_score - score) / sigma)
Alarms if the top-5 scores hold more than 80% of total mass.
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
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path


def _hermes_home() -> Path:
    env = os.environ.get('HERMES_HOME', '').strip()
    p = Path(env) if env else Path.home() / '.hermes'
    if p.name != '.hermes' and p.parent.name == 'profiles':
        return p.parent.parent
    return p


def _profile_name() -> str:
    profile = os.environ.get('HERMES_PROFILE', 'fork').strip()
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
OUT_PATH = CACHE / 'skill-lfpr-scores.json'

DAMPING = 0.85
PR_ITERS = 50
EPS = 0.5
TOP5_MASS_ALARM = 0.80


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


def adjacency_from_edges(edges) -> dict:
    adj: dict[str, dict[str, float]] = defaultdict(dict)
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
        if src == dst:
            continue
        adj[src][dst] = adj[src].get(dst, 0.0) + w
        adj[dst][src] = adj[dst].get(src, 0.0) + w
    return adj


def pagerank(nodes, adj, damping=DAMPING, iters=PR_ITERS):
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


def lfpr_refine(pr: dict, adj: dict, eps: float = EPS) -> dict:
    if not pr:
        return {}
    vals = list(pr.values())
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    sigma = math.sqrt(var)
    if sigma < 1e-15:
        return dict(pr)
    out = {}
    for u, score in pr.items():
        nbrs = adj.get(u) or {}
        if nbrs:
            tw = sum(nbrs.values()) or 1.0
            mean_nbr = sum(pr.get(v, score) * w for v, w in nbrs.items()) / tw
        else:
            mean_nbr = score
        mult = 1.0 + eps * (mean_nbr - score) / sigma
        mult = max(mult, 0.05)
        mult = min(mult, 4.0)
        out[u] = score * mult
    s = sum(out.values()) or 1.0
    return {u: v / s for u, v in out.items()}


def run(graph_path: Path | None = None, eps: float = EPS) -> dict:
    gp = Path(graph_path) if graph_path is not None else GRAPH_PATH
    g, err = _load_graph(gp)
    if err is not None or g is None:
        payload = err or {'status': 'insufficient_data', 'reason': 'skill-graph.json missing'}
        payload.update({'ts': _now(), 'n_nodes': 0, 'n_edges': 0, 'scores': [], 'alarm': False})
        return payload
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
            'ts': _now(),
            'n_nodes': 0,
            'n_edges': 0,
            'scores': [],
            'alarm': False,
        }
    pr = pagerank(nodes, adj)
    fair = lfpr_refine(pr, adj, eps=eps)
    ranked = sorted(
        ({'skill': k, 'score': v} for k, v in fair.items()),
        key=lambda d: -d['score'],
    )
    total = sum(d['score'] for d in ranked) or 1.0
    top5 = ranked[:5]
    top5_mass = sum(d['score'] for d in top5) / total
    alarm = top5_mass > TOP5_MASS_ALARM
    return {
        'status': 'ok',
        'ts': _now(),
        'graph_source': str(gp),
        'n_nodes': len(nodes),
        'n_edges': len(g.get('edges') or []),
        'damping': DAMPING,
        'epsilon': eps,
        'top5_mass': top5_mass,
        'top5_mass_threshold': TOP5_MASS_ALARM,
        'alarm': alarm,
        'alarm_reason': 'top-5 dominate >80% of total score mass' if alarm else None,
        'scores': ranked,
    }


def _self_test() -> int:
    missing = run(graph_path=Path('/nonexistent/skill-graph.json'))
    assert missing['status'] == 'insufficient_data'
    td = Path(tempfile.mkdtemp(prefix=f'lfpr-{uuid.uuid4().hex[:8]}-'))
    try:
        g = {
            'n_nodes': 4,
            'n_edges': 3,
            'nodes': [{'id': c} for c in 'abcd'],
            'edges': [
                {'src': 'a', 'dst': 'b', 'weight': 1},
                {'src': 'b', 'dst': 'c', 'weight': 1},
                {'src': 'c', 'dst': 'd', 'weight': 1},
            ],
        }
        p = td / 'skill-graph.json'
        p.write_text(json.dumps(g), encoding='utf-8')
        r = run(graph_path=p)
        assert r['status'] == 'ok', r
        scores = {d['skill']: d['score'] for d in r['scores']}
        assert abs(sum(scores.values()) - 1.0) < 1e-6, scores
        assert set(scores) == set('abcd')
        star = {
            'n_nodes': 5,
            'nodes': [{'id': str(i)} for i in range(5)],
            'edges': [{'src': '0', 'dst': str(i), 'weight': 1} for i in range(1, 5)],
        }
        p2 = td / 'star.json'
        p2.write_text(json.dumps(star), encoding='utf-8')
        s = run(graph_path=p2)
        assert s['status'] == 'ok'
        assert abs(sum(d['score'] for d in s['scores']) - 1.0) < 1e-6
        print('[skill-lfpr] --self-test PASS n={} top5_mass={:.3f}'.format(r['n_nodes'], r['top5_mass']))
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
            print(f'[skill-lfpr] --self-test FAIL: {exc}')
            return 1
    try:
        r = run()
        _atomic_write(OUT_PATH, r)
        slim = {k: r[k] for k in r if k != 'scores'}
        slim['top'] = (r.get('scores') or [])[:8]
        print(json.dumps(slim))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc), 'ts': _now()}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
