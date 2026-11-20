#!/usr/bin/env python3
"""Skill graph edge accumulator from co-access calibration data.

Groups calibration-log.jsonl by session_id, builds undirected weighted
edges for co-accessed skills (scope != ue_blackbox). Preserves existing
nodes in skill-graph.json. Stdlib only.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import fcntl
import json
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
CALIB = CACHE / 'calibration-log.jsonl'
GRAPH_PATH = CACHE / 'skill-graph.json'
MATRIX_PATH = CACHE / 'skill-coacccess-matrix.json'


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def load_graph(path: Path) -> dict:
    if not path.exists():
        return {'generated_at': _now(), 'nodes': [], 'edges': [], 'n_nodes': 0, 'n_edges': 0}
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'generated_at': _now(), 'nodes': [], 'edges': [], 'n_nodes': 0, 'n_edges': 0}
    if not isinstance(obj, dict):
        return {'generated_at': _now(), 'nodes': [], 'edges': [], 'n_nodes': 0, 'n_edges': 0}
    nodes = obj.get('nodes') if isinstance(obj.get('nodes'), list) else []
    return {
        'generated_at': obj.get('generated_at') or _now(),
        'nodes': nodes,
        'edges': obj.get('edges') if isinstance(obj.get('edges'), list) else [],
        'n_nodes': int(obj.get('n_nodes') or len(nodes)),
        'n_edges': int(obj.get('n_edges') or 0),
    }


def sessions_from_calib(calib_path: Path) -> dict:
    """session_id -> set(skill names). Skips ue_blackbox and empty scope."""
    by_sess = defaultdict(set)
    if not calib_path.exists():
        return {}
    try:
        with open(str(calib_path), encoding='utf-8', errors='replace') as fh:
            for line in fh:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                sid = rec.get('session_id')
                if not sid:
                    continue
                # calibration-log entries use 'scope' when set, otherwise fall back
                # to 'tool_name' (which is populated on the vast majority of entries).
                scope = rec.get('scope')
                if scope == 'ue_blackbox':
                    continue  # internal scoring row — skip entirely, never use tool_name fallback
                if scope is None or scope == '':
                    scope = rec.get('tool_name')
                if scope is None or scope == '':
                    continue
                scope = str(scope)
                by_sess[str(sid)].add(scope)
    except OSError:
        return {}
    return dict(by_sess)


def build_edges(by_sess: dict) -> tuple:
    """Return (edge_list, matrix, n_sessions). weight = co-sessions / total sessions."""
    n_sess = len(by_sess)
    pair_count = {}
    for skills in by_sess.values():
        ns = sorted(skills)
        for i in range(len(ns)):
            for j in range(i + 1, len(ns)):
                key = (ns[i], ns[j])
                pair_count[key] = pair_count.get(key, 0) + 1
    edges = []
    matrix = {}
    denom = float(n_sess) if n_sess else 1.0
    for (a, b), cnt in sorted(pair_count.items()):
        w = float(cnt) / denom
        edges.append({'source': a, 'target': b, 'weight': w, 'co_sessions': int(cnt)})
        matrix.setdefault(a, {})[b] = w
        matrix.setdefault(b, {})[a] = w
    return edges, matrix, n_sess


def apply_edges(graph: dict, edges: list) -> dict:
    nodes = list(graph.get('nodes') or [])
    ids = set()
    for n in nodes:
        if isinstance(n, dict) and n.get('id'):
            ids.add(str(n['id']))
        elif isinstance(n, str):
            ids.add(n)
    extra = set()
    for e in edges:
        extra.add(e['source'])
        extra.add(e['target'])
    for name in sorted(extra - ids):
        nodes.append({'id': name, 'degree': 0})
        ids.add(name)
    degree = defaultdict(int)
    for e in edges:
        degree[e['source']] += 1
        degree[e['target']] += 1
    new_nodes = []
    for n in nodes:
        if isinstance(n, dict):
            nid = str(n.get('id') or '')
            nn = dict(n)
            nn['degree'] = int(degree.get(nid, 0))
            new_nodes.append(nn)
        else:
            new_nodes.append({'id': str(n), 'degree': int(degree.get(str(n), 0))})
    out = {
        'generated_at': _now(),
        'nodes': new_nodes,
        'edges': edges,
        'n_nodes': len(new_nodes),
        'n_edges': len(edges),
    }
    return out


def run(calib_path: Path, graph_path: Path, matrix_path: Path) -> dict:
    if not calib_path.exists():
        return {'status': 'insufficient_data', 'reason': 'missing_calib', 'n_edges': 0}
    by_sess = sessions_from_calib(calib_path)
    if not by_sess:
        graph = load_graph(graph_path)
        return {
            'status': 'insufficient_data',
            'reason': 'no_skill_sessions',
            'n_edges': int(graph.get('n_edges') or 0),
            'n_nodes': int(graph.get('n_nodes') or len(graph.get('nodes') or [])),
        }
    edges, matrix, n_sess = build_edges(by_sess)
    graph = load_graph(graph_path)
    updated = apply_edges(graph, edges)
    _atomic_write(graph_path, updated)
    _atomic_write(matrix_path, {
        'generated_at': updated['generated_at'],
        'n_sessions': n_sess,
        'matrix': matrix,
    })
    return {
        'status': 'ok',
        'n_sessions': n_sess,
        'n_nodes': updated['n_nodes'],
        'n_edges': updated['n_edges'],
        'written': str(graph_path),
    }


def _self_test() -> int:
    td = Path(tempfile.mkdtemp(prefix='sgeb-'))
    try:
        calib = td / 'calibration-log.jsonl'
        # 5 sessions with known co-access
        sessions = [
            ('s1', ['alpha', 'beta']),
            ('s2', ['alpha', 'beta', 'gamma']),
            ('s3', ['beta', 'gamma']),
            ('s4', ['delta']),
            ('s5', ['alpha', 'ue_blackbox']),  # ue_blackbox ignored; alpha alone -> no new pair
        ]
        lines = []
        for sid, skills in sessions:
            for sk in skills:
                lines.append(json.dumps({
                    'ts': _now(), 'session_id': sid, 'scope': sk, 'predicted_confidence': 0.5,
                }))
        calib.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        graph_path = td / 'skill-graph.json'
        graph_path.write_text(json.dumps({
            'generated_at': 'old',
            'nodes': [{'id': 'alpha', 'degree': 0}, {'id': 'beta', 'degree': 0},
                      {'id': 'gamma', 'degree': 0}, {'id': 'delta', 'degree': 0},
                      {'id': 'keep-me', 'degree': 0}],
            'edges': [],
            'n_nodes': 5,
            'n_edges': 0,
        }), encoding='utf-8')
        matrix_path = td / 'skill-coacccess-matrix.json'
        r = run(calib, graph_path, matrix_path)
        assert r.get('status') == 'ok', r
        g = json.loads(graph_path.read_text(encoding='utf-8'))
        ids = {n['id'] for n in g['nodes']}
        assert 'keep-me' in ids, ids  # preserved
        assert g['n_edges'] >= 2, g
        pairs = {(e['source'], e['target']) for e in g['edges']}
        assert ('alpha', 'beta') in pairs, pairs
        assert ('beta', 'gamma') in pairs, pairs
        # weight alpha-beta: sessions s1,s2 of 5 = 0.4
        w = None
        for e in g['edges']:
            if e['source'] == 'alpha' and e['target'] == 'beta':
                w = e['weight']
        assert w is not None and abs(w - 2.0 / 5.0) < 1e-9, w
        mx = json.loads(matrix_path.read_text(encoding='utf-8'))
        assert 'matrix' in mx
        assert mx['matrix']['alpha']['beta'] == w
        missing = run(td / 'nope.jsonl', graph_path, matrix_path)
        assert missing.get('status') == 'insufficient_data'
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    print('[skill-graph-edge-builder] --self-test PASS')
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--calib', default=str(CALIB))
    ap.add_argument('--graph', default=str(GRAPH_PATH))
    ap.add_argument('--matrix', default=str(MATRIX_PATH))
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[skill-graph-edge-builder] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = run(Path(args.calib), Path(args.graph), Path(args.matrix))
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0)
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
