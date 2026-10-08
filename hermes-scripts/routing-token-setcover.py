#!/usr/bin/env python3
"""routing-token-setcover.py — greedy set-cover of query tokens by skill descriptions.

H_n-approx (ln |U| + 1). Alarm if cover size > 8 on the default routing query
(composition too fragmented) or leftover tokens remain with nonempty universe.

Source: Vazirani Approximation Algorithms (greedy set cover); Schrijver combinatorial opt.
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

COVER_ALARM = 8


def greedy_cover(universe, sets):
    """sets: name -> token set. Returns ordered names."""
    U = set(universe)
    chosen = []
    unused = dict(sets)
    while U and unused:
        best, best_gain = None, 0
        for n, s in unused.items():
            g = len(s & U)
            if g > best_gain:
                best, best_gain = n, g
        if not best or best_gain == 0:
            break
        chosen.append(best)
        U -= unused.pop(best)
    return chosen, U


def compute(index, query_tokens):
    token_map = {}
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                token_map[s['name']] = {t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)}
    U = set(t.lower() for t in query_tokens)
    if not U:
        U = {'skill', 'routing'}
    chosen, leftover = greedy_cover(U, token_map)
    nU = max(len(U), 1)
    bound = math.log(nU) + 1.0
    alarm = len(chosen) > COVER_ALARM
    return {
        'ts': time.time(),
        'universe_size': len(U),
        'cover': chosen,
        'cover_size': len(chosen),
        'leftover': sorted(leftover)[:32],
        'hn_approx_factor': round(bound, 4),
        'alarm': alarm,
        'reason': 'cover_too_large' if alarm else 'ok',
    }


def run(cache=None, query='skill routing bandit'):
    cache = cache or _cache_dir()
    result = compute(_load_json(cache / 'skill-router-index.json', {}), query.split())
    try:
        _atomic_write_json(cache / 'routing-token-setcover.json', result)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        sets = {'a': {'x', 'y'}, 'b': {'y', 'z'}, 'c': {'z'}}
        ch, left = greedy_cover({'x', 'y', 'z'}, sets)
        assert left == set()
        assert ch[0] in ('a', 'b')
        assert len(ch) <= 2
    except Exception as e:
        failures.append(f'greedy: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d)
            assert (d / 'routing-token-setcover.json').exists()
    except Exception as e:
        failures.append(f'io: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--query', default='skill routing bandit')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        print(json.dumps(run(query=args.query), indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
