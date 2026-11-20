#!/usr/bin/env python3
"""Build a co-access skill graph from skill dirs, calibration log, and KL history."""
from __future__ import annotations

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import fcntl
import json
import sqlite3
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'skill-graph.json'
SKILLS_DIR = _hermes_root / 'skills'
CALIB_LOG = _hermes_root / 'cache' / 'calibration-log.jsonl'
ACCESS_LOG = _hermes_root / 'cache' / 'skill-access.log'
# Fallback: skill-access-logger may write to base cache if HERMES_PROFILE unset at hook time
ACCESS_LOG_FALLBACK = _hermes_base / 'cache' / 'skill-access.log'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(lock_path, 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def list_skill_dirs(skills_root: Path) -> list:
    names = []
    if not skills_root.exists():
        return names
    try:
        for p in skills_root.iterdir():
            if p.is_dir() and not p.name.startswith('.'):
                names.append(p.name)
    except OSError:
        return names
    return names


def _add_clique(weights: dict, nodes: set) -> None:
    ns = sorted(nodes)
    for i in range(len(ns)):
        for j in range(i + 1, len(ns)):
            key = (ns[i], ns[j])
            weights[key] = weights.get(key, 0) + 1


def access_coaccess(access_path: Path) -> dict:
    """Build co-access weights from skill-access-logger's skill-access.log.

    Each line: {"skill": str, "session": str, "ts": str}
    Skills accessed in the same session (full session ID match) are co-accessed.
    """
    weights = {}
    if not access_path.exists():
        return weights
    by_sess = defaultdict(set)
    try:
        with open(access_path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                skill = rec.get('skill')
                if not isinstance(skill, str):
                    skill = str(skill) if skill else ''
                skill = skill.strip()
                if not skill or skill in ('MISSING', 'ue_blackbox'):
                    continue
                session = rec.get('session') or rec.get('session_id') or ''
                session = str(session).strip()
                if not session:
                    continue
                by_sess[session].add(skill)
    except OSError:
        return weights
    for nodes in by_sess.values():
        _add_clique(weights, nodes)
    return weights


def calib_coaccess(calib_path: Path) -> dict:
    weights = {}
    if not calib_path.exists():
        return weights
    by_sess = defaultdict(set)
    try:
        with open(calib_path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                sid = rec.get('session_id')
                if not sid:
                    continue
                prefix = str(sid)[:8]
                scope = rec.get('scope')
                if scope is None or scope == '' or scope == 'MISSING':
                    continue
                by_sess[prefix].add(str(scope))
    except OSError:
        return weights
    for nodes in by_sess.values():
        _add_clique(weights, nodes)
    return weights


def kl_coaccess(db_path: Path):
    names = set()
    weights = {}
    if not db_path.exists():
        return names, weights
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute('PRAGMA journal_mode=WAL')
        try:
            tabs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'skill_kl_history' not in tabs:
                return names, weights
            rows = conn.execute('SELECT ts, skill_name FROM skill_kl_history').fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return names, weights
    by_min = defaultdict(set)
    for ts, skill in rows:
        if not skill:
            continue
        s = str(skill)
        names.add(s)
        minute = str(ts or '')[:16]
        if minute:
            by_min[minute].add(s)
    for nodes in by_min.values():
        _add_clique(weights, nodes)
    return names, weights


def build(skills_root=None, calib_path=None, db_path=None, out_path=None, access_path=None) -> dict:
    skills_root = Path(skills_root) if skills_root is not None else SKILLS_DIR
    calib_path = Path(calib_path) if calib_path is not None else CALIB_LOG
    db_path = Path(db_path) if db_path is not None else LIFECYCLE_DB
    out_path = Path(out_path) if out_path is not None else OUT_PATH
    access_path = Path(access_path) if access_path is not None else ACCESS_LOG
    # Try fallback path if primary doesn't exist and they differ
    if not access_path.exists() and access_path != ACCESS_LOG_FALLBACK and ACCESS_LOG_FALLBACK.exists():
        access_path = ACCESS_LOG_FALLBACK

    dir_names = list_skill_dirs(skills_root)
    calib_w = calib_coaccess(calib_path)
    access_w = access_coaccess(access_path)
    kl_names, kl_w = kl_coaccess(db_path)

    nodes = set(dir_names) | set(kl_names)
    weights = {}
    for src in (calib_w, access_w, kl_w):
        for k, v in src.items():
            weights[k] = weights.get(k, 0) + v
            nodes.add(k[0])
            nodes.add(k[1])

    degree = {n: 0 for n in nodes}
    edges = []
    for (a, b), w in sorted(weights.items()):
        if a == b:
            continue
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
        edges.append({'src': a, 'dst': b, 'weight': int(w)})

    node_list = [{'id': n, 'degree': int(degree.get(n, 0))} for n in sorted(nodes)]
    result = {
        'generated_at': _now(),
        'nodes': node_list,
        'edges': edges,
        'n_nodes': len(node_list),
        'n_edges': len(edges),
    }
    _atomic_write(out_path, result)
    return result


def _self_test() -> int:
    import shutil
    td = Path(tempfile.mkdtemp(prefix=f'sgb-{uuid.uuid4().hex[:8]}-'))
    try:
        skills = td / 'skills'
        for name in ('alpha', 'beta', 'gamma'):
            (skills / name).mkdir(parents=True)
        db = td / 'lifecycle.db'
        conn = sqlite3.connect(str(db))
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute(
            'CREATE TABLE skill_kl_history ('
            'id INTEGER PRIMARY KEY, ts TEXT, skill_name TEXT, '
            'posterior_prob REAL, prior_prob REAL, kl_contrib REAL, net_score REAL)'
        )
        rows = [
            ('2026-10-28T12:00:01', 'alpha', 0.5, 0.4, 0.1, 0.2),
            ('2026-10-28T12:00:30', 'beta', 0.6, 0.4, 0.2, 0.3),
            ('2026-10-28T12:01:00', 'gamma', 0.3, 0.4, 0.05, 0.1),
        ]
        conn.executemany(
            'INSERT INTO skill_kl_history(ts, skill_name, posterior_prob, prior_prob, kl_contrib, net_score) '
            'VALUES (?,?,?,?,?,?)',
            rows,
        )
        conn.commit()
        conn.close()
        calib = td / 'calib.jsonl'
        calib.write_text('', encoding='utf-8')
        # skill-access.log: delta and epsilon co-accessed in same session
        access = td / 'skill-access.log'
        import json as _json
        access.write_text(
            _json.dumps({'skill': 'delta', 'session': 'sess-abc123', 'ts': '2026-11-16T00:00:00Z'}) + '\n' +
            _json.dumps({'skill': 'epsilon', 'session': 'sess-abc123', 'ts': '2026-11-16T00:00:01Z'}) + '\n' +
            _json.dumps({'skill': 'MISSING', 'session': 'sess-bad999', 'ts': '2026-11-16T00:00:02Z'}) + '\n',
            encoding='utf-8',
        )
        out = td / 'skill-graph.json'
        r = build(skills_root=skills, calib_path=calib, db_path=db, out_path=out, access_path=access)
        assert r['n_edges'] >= 1, f'expected >=1 edge from kl+access, got: {r}'
        assert r['n_nodes'] >= 2, r
        g = json.loads(out.read_text(encoding='utf-8'))
        assert g['n_edges'] >= 1
        assert g['n_nodes'] >= 2
        ids = {n['id'] for n in g['nodes']}
        assert 'alpha' in ids and 'beta' in ids, f'kl nodes missing: {ids}'
        assert 'delta' in ids and 'epsilon' in ids, f'access nodes missing: {ids}'
        assert 'MISSING' not in ids, f'MISSING leaked into nodes: {ids}'
        # verify delta-epsilon co-access edge exists
        edge_pairs = {(e['src'], e['dst']) for e in g['edges']}
        assert ('delta', 'epsilon') in edge_pairs or ('epsilon', 'delta') in edge_pairs, \
            f'delta-epsilon edge missing: {edge_pairs}'
        print('[skill-graph-builder] --self-test PASS n_nodes={} n_edges={}'.format(g['n_nodes'], g['n_edges']))
        return 0
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[skill-graph-builder] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        r = build()
        print(json.dumps({'n_nodes': r['n_nodes'], 'n_edges': r['n_edges'], 'generated_at': r['generated_at']}))
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}))


if __name__ == '__main__':
    main()
