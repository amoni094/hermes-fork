#!/usr/bin/env python3
"""routing-boolean-influence.py — O'Donnell influence of description tokens on top-1.

Inf_i(f) ~ fraction of queries (here: each skill's own tokens as query) whose
BM25 top-1 flips when token i is deleted from every description.
Alarm if max influence > 0.5 (router hinges on one coordinate).

Source: O'Donnell, Analysis of Boolean Functions (influence / pivotality).
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
import time
from collections import defaultdict, deque, Counter
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

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

THRESH = 0.5


def bm25_top1(query, token_map):
    q = set(query)
    best, best_s = None, -1.0
    n = max(len(token_map), 1)
    df = Counter()
    for toks in token_map.values():
        for t in toks:
            df[t] += 1
    for name, toks in token_map.items():
        sc = 0.0
        tf = Counter(toks)
        for t in q:
            if t not in toks:
                continue
            idf = math.log((n - df[t] + 0.5) / (df[t] + 0.5) + 1.0)
            sc += idf * tf[t]
        if sc > best_s:
            best, best_s = name, sc
    return best


def influences(token_map):
    names = list(token_map)
    universe = set()
    for toks in token_map.values():
        universe |= set(toks)
    # cap tokens to keep runtime bounded
    toks_list = sorted(universe, key=lambda t: -sum(1 for s in token_map.values() if t in s))[:64]
    queries = [list(token_map[n]) for n in names]
    base = [bm25_top1(q, token_map) for q in queries]
    inf = {}
    for tok in toks_list:
        flipped = 0
        reduced = {n: (toks - {tok}) for n, toks in token_map.items()}
        for q, b in zip(queries, base):
            q2 = [t for t in q if t != tok]
            if bm25_top1(q2, reduced) != b:
                flipped += 1
        inf[tok] = flipped / max(len(queries), 1)
    return inf


def compute(index):
    token_map = {}
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                token_map[s['name']] = {t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)}
    if len(token_map) < 2:
        return {'n_skills': len(token_map), 'max_influence': 0.0, 'alarm': False, 'reason': 'too_few'}
    inf = influences(token_map)
    if not inf:
        return {'n_skills': len(token_map), 'max_influence': 0.0, 'alarm': False, 'reason': 'empty_tokens'}
    tok, mx = max(inf.items(), key=lambda kv: kv[1])
    return {
        'ts': time.time(),
        'n_skills': len(token_map),
        'n_tokens_scored': len(inf),
        'max_influence_token': tok,
        'max_influence': round(mx, 6),
        'alarm': mx > THRESH,
        'alarm_threshold': THRESH,
        'reason': 'pivot_token' if mx > THRESH else 'ok',
        'top_influences': sorted(
            [{'token': k, 'influence': round(v, 6)} for k, v in inf.items()],
            key=lambda r: -r['influence'],
        )[:12],
    }


def run(cache=None):
    cache = cache or _cache_dir()
    result = compute(_load_json(cache / 'skill-router-index.json', {}))
    try:
        _atomic_write_json(cache / 'routing-boolean-influence.json', result)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        tmap = {
            'unique': {'zzzunique', 'shared'},
            'other': {'shared', 'aaa'},
            'third': {'shared', 'bbb'},
        }
        inf = influences(tmap)
        assert inf.get('zzzunique', 0) >= inf.get('shared', 0) - 1e-12
    except Exception as e:
        failures.append(f'pivot: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / 'skill-router-index.json').write_text(json.dumps({
                'skills': [
                    {'name': 'a', 'tokens': ['alpha', 'shared']},
                    {'name': 'b', 'tokens': ['beta', 'shared']},
                ]
            }))
            r = run(cache=d)
            assert (d / 'routing-boolean-influence.json').exists()
            json.dumps(r)
    except Exception as e:
        failures.append(f'io: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        print(json.dumps(run(), indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
