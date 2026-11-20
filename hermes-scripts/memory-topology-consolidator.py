#!/usr/bin/env python3
"""Consolidate co-accessed Graphiti entities (Jaccard + shared-neighbor). Report-only by default."""
from __future__ import annotations
import argparse, json, os, sqlite3, sys, tempfile, uuid
from collections import defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
GRAPHITI_DB = _hermes_root / 'graphiti' / 'graphiti.db'

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))

def _lifecycle_db() -> Path:
    return _hermes_root / 'memory-facts' / 'lifecycle.db'

def _temp_out(prefix: str) -> Path:
    return Path(tempfile.gettempdir()) / (f'{prefix}-{uuid.uuid4().hex}.json')

OUT_PATH = CACHE / 'memory-topology-consolidator.json'


def jaccard(a, b):
    sa, sb = set(a or []), set(b or [])
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def _load_nodes(db_path=None):
    db = Path(db_path) if db_path else GRAPHITI_DB
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'nodes' not in tables:
                return []
            cols = {r[1] for r in conn.execute('PRAGMA table_info(nodes)')}
            name_col = 'name' if 'name' in cols else ('id' if 'id' in cols else None)
            type_col = 'entity_type' if 'entity_type' in cols else ('type' if 'type' in cols else None)
            if not name_col:
                return []
            sel = name_col + ((', ' + type_col) if type_col else '')
            rows = conn.execute(f'SELECT {sel} FROM nodes LIMIT 400').fetchall()
            out = []
            for row in rows:
                name = row[0]
                et = row[1] if type_col else 'Entity'
                out.append({'name': name, 'entity_type': et, 'neighbors': []})
            return out
        finally:
            conn.close()
    except Exception:
        return []


def propose(nodes, require_coaccess=True):
    n = len(nodes)
    if n == 0:
        return {'status': 'insufficient_data', 'n_nodes': 0, 'n_pairs': 0, 'proposals': [], 'ts': _now()}
    proposals = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = nodes[i], nodes[j]
            if (a.get('entity_type') or 'Entity') != (b.get('entity_type') or 'Entity'):
                continue
            na, nb = set(a.get('neighbors') or []), set(b.get('neighbors') or [])
            shared = na & nb
            jac = jaccard(na, nb)
            if require_coaccess and not shared and jac <= 0:
                continue
            if jac < 0.3 and len(shared) < 2:
                continue
            proposals.append({
                'a': a.get('name'),
                'b': b.get('name'),
                'jaccard': round(jac, 4),
                'shared_neighbors': len(shared),
                'entity_type': a.get('entity_type') or 'Entity',
            })
    return {
        'status': 'ok',
        'n_nodes': n,
        'n_pairs': len(proposals),
        'proposals': proposals[:50],
        'dry_run': True,
        'ts': _now(),
    }


def _self_test() -> int:
    assert jaccard([], []) == 0.0
    nodes = [
        {'name': 'Alpha', 'entity_type': 'Person', 'neighbors': ['x', 'y', 'z']},
        {'name': 'A.', 'entity_type': 'Person', 'neighbors': ['x', 'y']},
        {'name': 'Tool', 'entity_type': 'Thing', 'neighbors': ['q']},
    ]
    r = propose(nodes)
    assert r['n_pairs'] >= 1
    empty = propose([])
    assert empty['status'] == 'insufficient_data'
    tmp = _temp_out('mtc')
    _atomic_write(tmp, r)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    print('[memory-topology-consolidator] --self-test PASS pairs={}'.format(r['n_pairs']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[memory-topology-consolidator] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        nodes = _load_nodes()
        r = propose(nodes)
        r['apply'] = bool(args.apply)
        r['dry_run'] = not args.apply
        if r.get('status') != 'insufficient_data':
            _atomic_write(OUT_PATH, r)
        print(json.dumps({'n_nodes': r.get('n_nodes'), 'n_pairs': r.get('n_pairs'), 'status': r.get('status')}))
    except Exception:
        pass


if __name__ == '__main__':
    main()
