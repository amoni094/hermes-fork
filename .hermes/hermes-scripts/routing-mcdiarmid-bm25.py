#!/usr/bin/env python3
"""routing-mcdiarmid-bm25.py — McDiarmid bounded-differences radius on BM25 top-gap.

Changing one skill's tokens moves any score by at most c_i. Radius
eps = sqrt((sum c_i^2 / 2) log(2/delta)). Alarm if top1-top2 gap < radius (unstable rank).

Source: McDiarmid bounded differences; Lugosi concentration; Vershynin HDP.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import random
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

DELTA = 0.05


def bm25_scores(token_map):
    n = max(len(token_map), 1)
    df = Counter()
    for toks in token_map.values():
        for t in toks:
            df[t] += 1
    scores = {}
    for name, toks in token_map.items():
        sc = 0.0
        tf = Counter(toks)
        for t, f in tf.items():
            idf = math.log((n - df[t] + 0.5) / (df[t] + 0.5) + 1.0)
            sc += idf * f
        scores[name] = sc
    return scores


def mcdiarmid_radius(n, c=1.0, delta=DELTA):
    # P(|f-Ef|>=eps) <= 2 exp(-2 eps^2 / sum c_i^2); invert
    # eps = sqrt( (sum c^2 / 2) * log(2/delta) )
    n = max(int(n), 1)
    ssc = n * (c * c)
    return math.sqrt((ssc / 2.0) * math.log(2.0 / max(delta, EPS)))


def compute(index):
    token_map = {}
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                token_map[s['name']] = [t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)]
    n = len(token_map)
    if n < 2:
        return {'n_skills': n, 'alarm': False, 'reason': 'too_few'}
    scores = bm25_scores({k: set(v) for k, v in token_map.items()})
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    gap = ranked[0][1] - ranked[1][1]
    # per-doc change bound: IDF of a unique token <= log(n+1)
    c = math.log(n + 1.0)
    rad = mcdiarmid_radius(n, c=c)
    alarm = gap < rad
    return {
        'ts': time.time(),
        'n_skills': n,
        'top1': ranked[0][0],
        'top2': ranked[1][0],
        'gap': round(gap, 6),
        'c_bound': round(c, 6),
        'mcdiarmid_radius': round(rad, 6),
        'delta': DELTA,
        'alarm': alarm,
        'reason': 'unstable_ranking' if alarm else 'ok',
    }


def run(cache=None):
    cache = cache or _cache_dir()
    result = compute(_load_json(cache / 'skill-router-index.json', {}))
    try:
        _atomic_write_json(cache / 'routing-mcdiarmid-bm25.json', result)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        r1 = mcdiarmid_radius(10, c=1.0)
        r2 = mcdiarmid_radius(100, c=1.0)
        assert r2 > r1
        assert r1 > 0
    except Exception as e:
        failures.append(f'rad: {e}')
    try:
        idx = {'skills': [
            {'name': 'a', 'tokens': ['same', 'same']},
            {'name': 'b', 'tokens': ['same', 'same']},
        ]}
        r = compute(idx)
        assert r['alarm'] is True  # gap 0 < radius
    except Exception as e:
        failures.append(f'tie: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d)
            assert (d / 'routing-mcdiarmid-bm25.json').exists()
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
