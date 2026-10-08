#!/usr/bin/env python3
"""routing-precision-recall.py — P@k / R@k of BM25 self-rank vs beta successes.

Relevant = skills with alpha > beta (empirical success). Alarm if P@5 < 0.2 and n_rel>=5.

Source: Manning, Raghavan, Schütze — Introduction to Information Retrieval (Ch 8).
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

K = 5
P_ALARM = 0.2


def precision_recall(ranked, relevant, k=K):
    rel = set(relevant)
    top = ranked[:k]
    hit = sum(1 for x in top if x in rel)
    p = hit / max(len(top), 1)
    r = hit / max(len(rel), 1)
    return p, r, hit


def compute(index, beta):
    token_map = {}
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                token_map[s['name']] = {t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)}
    names = list(token_map) or (sorted(beta.keys()) if isinstance(beta, dict) else [])
    # self-distinctiveness score
    scores = {}
    n = max(len(names), 1)
    df = Counter()
    for toks in token_map.values():
        for t in toks:
            df[t] += 1
    for nm in names:
        toks = token_map.get(nm, set())
        sc = 0.0
        for t in toks:
            sc += math.log((n - df[t] + 0.5) / (df[t] + 0.5) + 1.0)
        scores[nm] = sc
    ranked = sorted(names, key=lambda x: -scores.get(x, 0.0))
    relevant = []
    if isinstance(beta, dict):
        for nm, e in beta.items():
            if not isinstance(e, dict):
                continue
            try:
                a = float(e.get('alpha', 1.0)); b = float(e.get('beta', 1.0))
            except (TypeError, ValueError):
                continue
            if a > b:
                relevant.append(nm)
    p, r, hit = precision_recall(ranked, relevant, K)
    nrel = len(relevant)
    alarm = (p < P_ALARM) and nrel >= 5
    return {
        'ts': time.time(),
        'n_skills': len(names),
        'n_relevant': nrel,
        'k': K,
        'P_at_k': round(p, 6),
        'R_at_k': round(r, 6),
        'hits': hit,
        'alarm': alarm,
        'reason': 'low_precision' if alarm else 'ok',
        'ranked_top': ranked[:K],
    }


def run(cache=None):
    cache = cache or _cache_dir()
    result = compute(_load_json(cache / 'skill-router-index.json', {}),
                     _load_json(cache / 'skill-beta-state.json', {}))
    try:
        _atomic_write_json(cache / 'routing-precision-recall.json', result)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        p, r, h = precision_recall(['a', 'b', 'c'], ['a', 'b'], k=2)
        assert abs(p - 1.0) < 1e-12 and abs(r - 1.0) < 1e-12
        p2, r2, _ = precision_recall(['x', 'y'], ['a'], k=2)
        assert p2 == 0.0
    except Exception as e:
        failures.append(f'pr: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d)
            assert (d / 'routing-precision-recall.json').exists()
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
