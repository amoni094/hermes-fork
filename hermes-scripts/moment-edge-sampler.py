#!/usr/bin/env python3
"""Moment-guided edge sampling + spectral-moment mutation guard.

Loads the skill graph as a success-weighted adjacency matrix, computes the
first three spectral moments of the random-walk transition matrix P, samples
structurally fragile edges, proposes a single low-performing-edge demotion,
and rejects the change if any moment shifts by more than 10%.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

import argparse
import fcntl
import json
import math
import random
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'moment-edge-sample.json'
MOMENTS_PATH = CACHE / 'skill-graph-moments.json'
MUTATION_LOG = CACHE / 'skill-graph-moment-mutations.jsonl'
GRAPH_PATH = CACHE / 'skill-graph.json'

MOMENT_REL_MAX = 0.10
DEMOTE_FACTOR = 0.5
SAMPLE_K = 12
MUTATION_LOG_KEEP = 100
DROP_ABS = 1e-9
DROP_FACTOR = 0.05


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    with open(lock, 'w', encoding='utf-8') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
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
        w = 1.0
        if isinstance(e, dict):
            src = e.get('src') or e.get('source') or e.get('u') or e.get('from')
            dst = e.get('dst') or e.get('target') or e.get('v') or e.get('to')
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
        if src and dst:
            src, dst = str(src), str(dst)
            edges.append((src, dst, max(0.0, w)))
            if src not in nodes:
                nodes.append(src)
            if dst not in nodes:
                nodes.append(dst)
    # unique node order
    seen = set()
    uniq = []
    for n in nodes:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq, edges


def _undirected_adj(edges):
    adj = defaultdict(lambda: defaultdict(float))
    for u, v, w in edges:
        if u == v:
            adj[u][v] += w
            continue
        adj[u][v] += w
        adj[v][u] += w
    return adj


def _degrees(adj):
    return {u: float(sum(nbrs.values())) for u, nbrs in adj.items()}


def degrees(nodes, edges):
    """Unweighted endpoint counts (compat)."""
    d = {n: 0 for n in nodes}
    for item in edges:
        if len(item) >= 2:
            u, v = item[0], item[1]
            d[u] = d.get(u, 0) + 1
            d[v] = d.get(v, 0) + 1
    return d


def _transition(adj, nodes):
    """Row-stochastic random-walk P as dict-of-dicts. Dangling -> self-loop."""
    P = {}
    for u in nodes:
        nbrs = adj.get(u) or {}
        tot = float(sum(nbrs.values()))
        row = {}
        if tot <= 0.0:
            row[u] = 1.0
        else:
            for v, w in nbrs.items():
                if w > 0.0:
                    row[v] = row.get(v, 0.0) + (w / tot)
        P[u] = row
    return P


def _active_nodes(adj, nodes):
    """Nodes with positive weighted degree (isolates swamp tr(P^k) via self-loops)."""
    out = []
    for u in nodes:
        tot = float(sum((adj.get(u) or {}).values()))
        if tot > 0.0:
            out.append(u)
    return out


def moments_of(adj, nodes):
    """Spectral moments of P on the active (positive-degree) support."""
    use = _active_nodes(adj, nodes) or list(nodes)
    P = _transition(adj, use)
    return spectral_moments(P, use), use, P


def spectral_moments(P, nodes):
    """First three spectral moments m_k = tr(P^k) / n of the walk matrix."""
    n = len(nodes)
    if n == 0:
        return [0.0, 0.0, 0.0]
    inv_n = 1.0 / n
    m1 = 0.0
    for u in nodes:
        m1 += float((P.get(u) or {}).get(u, 0.0))
    m1 *= inv_n
    m2 = 0.0
    for u in nodes:
        row_u = P.get(u) or {}
        for v, p_uv in row_u.items():
            p_vu = float((P.get(v) or {}).get(u, 0.0))
            m2 += p_uv * p_vu
    m2 *= inv_n
    m3 = 0.0
    for u in nodes:
        row_u = P.get(u) or {}
        for v, p_uv in row_u.items():
            row_v = P.get(v) or {}
            for w, p_vw in row_v.items():
                p_wu = float((P.get(w) or {}).get(u, 0.0))
                m3 += p_uv * p_vw * p_wu
    m3 *= inv_n
    return [m1, m2, m3]


def _moment_l2(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _rel_deltas(before, after):
    out = []
    for b, a in zip(before, after):
        den = max(abs(b), 1e-12)
        out.append(abs(a - b) / den)
    return out


def sample_edges(nodes, edges, k=SAMPLE_K, rng=None):
    """Compat sampler: inverse degree-product, unique undirected edges."""
    rng = rng or random.Random(0)
    pairs = []
    for item in edges:
        if len(item) >= 2:
            pairs.append((item[0], item[1]))
    if not pairs:
        return [], degrees(nodes, pairs)
    deg = degrees(nodes, pairs)
    weights = []
    for u, v in pairs:
        w = 1.0 / max(1, deg.get(u, 1) * deg.get(v, 1))
        weights.append(w)
    s = sum(weights) or 1.0
    probs = [w / s for w in weights]
    order = list(range(len(pairs)))
    order.sort(key=lambda i: rng.random() / max(1e-12, probs[i]))
    picked = []
    seen = set()
    for i in order:
        e = pairs[i]
        key = tuple(sorted(e))
        if key in seen:
            continue
        seen.add(key)
        picked.append({
            'u': e[0],
            'v': e[1],
            'w': 1.0 / max(1, deg.get(e[0], 1) * deg.get(e[1], 1)),
        })
        if len(picked) >= k:
            break
    return picked, deg


def _edge_m2_contrib(P, u, v):
    p_uv = float((P.get(u) or {}).get(v, 0.0))
    p_vu = float((P.get(v) or {}).get(u, 0.0))
    return p_uv * p_vu


def sample_moment_edges(nodes, edges, adj, P, k=SAMPLE_K, rng=None):
    """Sample edges by spectral-moment leverage (m2 closed-walk mass)."""
    rng = rng or random.Random(0)
    deg_w = _degrees(adj)
    uniq = []
    seen = set()
    for u, v, w in edges:
        if u == v:
            continue
        key = tuple(sorted((u, v)))
        if key in seen:
            continue
        seen.add(key)
        uniq.append((u, v, w))
    if not uniq:
        return []
    scores = []
    for u, v, w in uniq:
        m2c = _edge_m2_contrib(P, u, v)
        inv_deg = 1.0 / max(1e-9, deg_w.get(u, 1.0) * deg_w.get(v, 1.0))
        scores.append(m2c + 0.1 * inv_deg)
    total = sum(scores) or 1.0
    order = list(range(len(uniq)))
    order.sort(key=lambda i: rng.random() / max(1e-12, scores[i] / total))
    picked = []
    for i in order:
        u, v, w = uniq[i]
        picked.append({
            'u': u,
            'v': v,
            'weight': w,
            'm2_contrib': _edge_m2_contrib(P, u, v),
            'sample_score': scores[i],
        })
        if len(picked) >= k:
            break
    return picked


def apply_demotion(adj, u, v, factor=DEMOTE_FACTOR):
    """Rank-2 update: scale undirected edge (u,v) by factor.

    Aggressive demotion (factor <= DROP_FACTOR or near-zero weight) drops the
    edge so the walk operator actually changes; pure rescaling on a path is
    moment-invariant after row-normalisation.
    """
    cur = float((adj.get(u) or {}).get(v, 0.0))
    new = cur * float(factor)
    drop = (new <= DROP_ABS) or (factor <= DROP_FACTOR)
    if drop:
        if u in adj:
            adj[u].pop(v, None)
        if u != v and v in adj:
            adj[v].pop(u, None)
        return -cur
    if u == v:
        adj[u][v] = new
        return new - cur
    adj[u][v] = new
    adj[v][u] = new
    return new - cur


def _clone_adj(adj):
    out = defaultdict(lambda: defaultdict(float))
    for u, nbrs in adj.items():
        for v, w in nbrs.items():
            out[u][v] = w
    return out


def _top_k(nodes, adj, k=5):
    deg = _degrees(adj)
    ranked = sorted(nodes, key=lambda n: (-deg.get(n, 0.0), n))
    return ranked[:k]


def _recall_at_k(before, after):
    if not before:
        return 0.0
    return len(set(before) & set(after)) / float(len(before))


def _pearson(xs, ys):
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx < 1e-15 or dy < 1e-15:
        return None
    r = num / (dx * dy)
    if r > 1.0 or abs(r - 1.0) < 1e-12:
        r = 1.0
    elif r < -1.0 or abs(r + 1.0) < 1e-12:
        r = -1.0
    return r


def _read_mutation_history(path: Path):
    rows = []
    if not path.exists():
        return rows
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return rows
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            rows.append(rec)
    return rows[-MUTATION_LOG_KEEP:]


def _append_mutation(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    with open(lock, 'w', encoding='utf-8') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec) + '\n')
        # trim if the log grew too far past the keep window
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except OSError:
            return
        if len(lines) > MUTATION_LOG_KEEP * 2:
            keep = lines[-MUTATION_LOG_KEEP:]
            tmp = path.with_name(path.name + '.tmp')
            tmp.write_text('\n'.join(keep) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))


def propose_and_guard(nodes, adj, sampled, factor=DEMOTE_FACTOR):
    """Propose demoting the weakest sampled edge; reject if moments shift >10%."""
    before, active_before, _P = moments_of(adj, nodes)
    top_before = _top_k(nodes, adj, 5)
    if not sampled:
        return {
            'proposed': None,
            'accepted': False,
            'reason': 'no_sampled_edges',
            'moments_before': before,
            'moments_after': before,
            'rel_deltas': [0.0, 0.0, 0.0],
            'l2_distance': 0.0,
            'recall_at_5': 1.0,
            'top5_before': top_before,
            'top5_after': top_before,
        }
    # demote the lowest-weight sampled edge (low empirical association)
    cand = min(sampled, key=lambda e: (float(e.get('weight', 1.0)), e.get('u', ''), e.get('v', '')))
    u, v = cand['u'], cand['v']
    adj2 = _clone_adj(adj)
    delta_w = apply_demotion(adj2, u, v, factor=factor)
    after, active_after, _P2 = moments_of(adj2, nodes)
    rel = _rel_deltas(before, after)
    l2 = _moment_l2(before, after)
    top_after = _top_k(nodes, adj2, 5)
    recall = _recall_at_k(top_before, top_after)
    reject = any(r > MOMENT_REL_MAX for r in rel)
    dropped = float((adj2.get(u) or {}).get(v, 0.0)) <= 0.0
    return {
        'proposed': {
            'u': u,
            'v': v,
            'old_weight': float((adj.get(u) or {}).get(v, 0.0)),
            'new_weight': float((adj2.get(u) or {}).get(v, 0.0)),
            'delta_weight': delta_w,
            'factor': factor,
            'dropped': dropped,
            'method': 'rank2_row_update',
        },
        'accepted': (not reject),
        'reason': 'moment_shift' if reject else 'ok',
        'moments_before': before,
        'moments_after': after,
        'n_active_before': len(active_before),
        'n_active_after': len(active_after),
        'rel_deltas': rel,
        'l2_distance': l2,
        'recall_at_5': recall,
        'top5_before': top_before,
        'top5_after': top_after,
        'threshold': MOMENT_REL_MAX,
    }


def run(graph_path=None, mutation_log=None, write_log=False):
    gp = Path(graph_path) if graph_path is not None else GRAPH_PATH
    g = _load_graph(gp)
    if g is None:
        return {'status': 'insufficient_data'}
    nodes, edges = _parse_graph(g)
    if not nodes:
        return {'status': 'insufficient_data'}
    adj = _undirected_adj(edges)
    for n in nodes:
        adj.setdefault(n, defaultdict(float))
    moments, active, P = moments_of(adj, nodes)
    sampled = sample_moment_edges(nodes, edges, adj, P, k=SAMPLE_K)
    # compat unweighted sample for moment-edge-sample.json consumers
    compat_edges = [(u, v) for u, v, _w in edges]
    compat_sampled, deg = sample_edges(nodes, compat_edges)
    guard = propose_and_guard(nodes, adj, sampled)
    avg_d = (sum(deg.values()) / len(deg)) if deg else 0.0
    m2_deg = (sum(v * v for v in deg.values()) / len(deg)) if deg else 0.0
    history = _read_mutation_history(
        Path(mutation_log) if mutation_log is not None else MUTATION_LOG
    )
    hist_l2 = []
    hist_rec = []
    for rec in history:
        try:
            hist_l2.append(float(rec['l2_distance']))
            hist_rec.append(float(rec['recall_at_5']))
        except (KeyError, TypeError, ValueError):
            continue
    if write_log:
        _append_mutation(
            Path(mutation_log) if mutation_log is not None else MUTATION_LOG,
            {
                'ts': _now(),
                'accepted': guard['accepted'],
                'reason': guard['reason'],
                'l2_distance': guard['l2_distance'],
                'recall_at_5': guard['recall_at_5'],
                'rel_deltas': guard['rel_deltas'],
                'moments_before': guard['moments_before'],
                'moments_after': guard['moments_after'],
                'proposed': guard.get('proposed'),
            },
        )
        hist_l2.append(float(guard['l2_distance']))
        hist_rec.append(float(guard['recall_at_5']))
    pearson = _pearson(hist_l2, hist_rec)
    n_hist = min(len(hist_l2), len(hist_rec))
    return {
        'status': 'ok',
        'ts': _now(),
        'sampled_edges': sampled,
        'compat_sampled_edges': compat_sampled,
        'graph_stats': {
            'n_nodes': len(nodes),
            'n_edges': len(edges),
            'n_active': len(active),
            'avg_degree': avg_d,
            'second_moment': m2_deg,
            'spectral_moments': moments,
        },
        'moments': moments,
        'guard': guard,
        'mutation_history_n': n_hist,
        'pearson_l2_vs_recall5': pearson,
        'kill_test_note': (
            'reject prototype if after 50 real mutations Pearson |r| of '
            'moment L2 vs recall@5 is < 0.3'
        ),
    }


def _self_test() -> int:
    empty = run(graph_path=Path('/nonexistent/skill-graph.json'))
    assert empty.get('status') == 'insufficient_data'
    td = Path(tempfile.mkdtemp(prefix=f'mes-{uuid.uuid4().hex[:8]}-'))
    try:
        tmpg = td / 'skill-graph.json'
        payload = {
            'n_nodes': 3,
            'n_edges': 2,
            'nodes': [{'id': 'a', 'degree': 1}, {'id': 'b', 'degree': 2}, {'id': 'c', 'degree': 1}],
            'edges': [
                {'source': 'a', 'target': 'b', 'weight': 1.0},
                {'source': 'b', 'target': 'c', 'weight': 1.0},
            ],
        }
        tmpg.write_text(json.dumps(payload), encoding='utf-8')
        logp = td / 'mutations.jsonl'
        r = run(graph_path=tmpg, mutation_log=logp, write_log=True)
        assert r.get('status') == 'ok', r
        assert r['graph_stats']['n_nodes'] >= 3
        assert r['graph_stats']['n_edges'] >= 2
        assert r['sampled_edges']
        assert len(r['moments']) == 3
        assert all(isinstance(x, float) for x in r['moments'])
        g = r['guard']
        assert 'accepted' in g and 'rel_deltas' in g
        assert len(g['rel_deltas']) == 3
        assert 0.0 <= g['recall_at_5'] <= 1.0
        assert logp.exists()
        # force a large demotion on a hub-and-spoke vs path to exercise reject path
        star = {
            'n_nodes': 4,
            'n_edges': 3,
            'nodes': [{'id': 'h'}, {'id': 'x'}, {'id': 'y'}, {'id': 'z'}],
            'edges': [
                {'src': 'h', 'dst': 'x', 'weight': 10.0},
                {'src': 'h', 'dst': 'y', 'weight': 0.1},
                {'src': 'h', 'dst': 'z', 'weight': 0.1},
            ],
        }
        tmp2 = td / 'star.json'
        tmp2.write_text(json.dumps(star), encoding='utf-8')
        r2 = run(graph_path=tmp2, mutation_log=td / 'm2.jsonl', write_log=False)
        assert r2['status'] == 'ok'
        nodes, edges = _parse_graph(star)
        adj = _undirected_adj(edges)
        for n in nodes:
            adj.setdefault(n, defaultdict(float))
        sampled = [{'u': 'h', 'v': 'x', 'weight': 10.0}]
        forced = propose_and_guard(nodes, adj, sampled, factor=0.01)
        assert forced['proposed']['u'] == 'h'
        assert all(d >= 0.0 for d in forced['rel_deltas'])
        assert forced['l2_distance'] > 0.0
        assert forced['moments_before'] != forced['moments_after']
        # triangle: 0.5 rescale (not drop) still moves m3
        tri_nodes = ['a', 'b', 'c']
        tri_adj = _undirected_adj([
            ('a', 'b', 1.0), ('b', 'c', 1.0), ('c', 'a', 1.0),
        ])
        tri = propose_and_guard(tri_nodes, tri_adj, [{'u': 'a', 'v': 'b', 'weight': 1.0}], factor=0.5)
        assert tri['l2_distance'] > 0.0
        # empty graph
        empty_g = td / 'empty.json'
        empty_g.write_text(json.dumps({'n_nodes': 0, 'nodes': [], 'edges': []}), encoding='utf-8')
        e2 = run(graph_path=empty_g)
        assert e2['status'] == 'insufficient_data'
        # malformed json
        bad = td / 'bad.json'
        bad.write_text('{not json', encoding='utf-8')
        e3 = run(graph_path=bad)
        assert e3['status'] == 'insufficient_data'
        # pearson bounds
        assert _pearson([1, 2, 3], [1, 2, 3]) == 1.0
        assert _pearson([], []) is None
        print('[moment-edge-sampler] --self-test PASS n={} e={} m={} accepted={}'.format(
            r['graph_stats']['n_nodes'],
            r['graph_stats']['n_edges'],
            r['moments'],
            g['accepted'],
        ))
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
            print(f'[moment-edge-sampler] --self-test FAIL: {type(exc).__name__}: {exc}')
            sys.exit(1)
    r = run(write_log=True)
    if r.get('status') == 'insufficient_data':
        print(json.dumps(r))
        return
    sample_out = {
        'status': r['status'],
        'ts': r['ts'],
        'sampled_edges': r['sampled_edges'],
        'graph_stats': r['graph_stats'],
        'n_sampled': len(r['sampled_edges']),
    }
    moments_out = {
        'status': r['status'],
        'ts': r['ts'],
        'moments': r['moments'],
        'guard': r['guard'],
        'graph_stats': r['graph_stats'],
        'mutation_history_n': r['mutation_history_n'],
        'pearson_l2_vs_recall5': r['pearson_l2_vs_recall5'],
        'kill_test_note': r['kill_test_note'],
    }
    _atomic_write(OUT_PATH, sample_out)
    _atomic_write(MOMENTS_PATH, moments_out)
    slim = {
        'status': r['status'],
        'n_nodes': r['graph_stats']['n_nodes'],
        'n_edges': r['graph_stats']['n_edges'],
        'moments': r['moments'],
        'accepted': r['guard']['accepted'],
        'reason': r['guard']['reason'],
        'l2_distance': r['guard']['l2_distance'],
        'recall_at_5': r['guard']['recall_at_5'],
        'pearson_l2_vs_recall5': r['pearson_l2_vs_recall5'],
        'n_sampled': len(r['sampled_edges']),
    }
    print(json.dumps(slim))


if __name__ == '__main__':
    main()
