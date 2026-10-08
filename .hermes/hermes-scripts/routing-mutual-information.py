#!/usr/bin/env python3
"""routing-mutual-information.py — I(S; Q) informativeness of the skill codebook.

I(S;Q) = H(S) - H(S|Q). If I/H(S) < 0.05 the descriptions carry almost no query
information and BM25 routing is near-chance.

Source: Cover-Thomas; Manning IR (mutual information feature selection).
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

RATIO_ALARM = 0.05
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


def entropy(ps) -> float:
    h = 0.0
    for p in ps:
        if p > EPS:
            h -= p * math.log2(p)
    return h


def softmax(scores):
    if not scores:
        return []
    m = max(scores)
    ex = [math.exp(s - m) for s in scores]
    z = sum(ex) or 1.0
    return [e / z for e in ex]


def compute(index: dict, beta: dict) -> dict:
    skills = index.get('skills') if isinstance(index, dict) else []
    docs = []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                toks = [t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)]
                docs.append((s['name'], toks))
    n = len(docs)
    if n == 0:
        return {'n_skills': 0, 'I_S_Q': 0.0, 'H_S': 0.0, 'H_S_Q': 0.0, 'alarm': True, 'reason': 'empty'}
    # H(S) from beta occupancy else uniform
    weights = []
    for name, _ in docs:
        entry = beta.get(name) if isinstance(beta, dict) else None
        if isinstance(entry, dict):
            try:
                a = float(entry.get('alpha', 1.0))
                b = float(entry.get('beta', 1.0))
                weights.append(max(a + b - 2.0, 0.0) + 1.0)
            except (TypeError, ValueError):
                weights.append(1.0)
        else:
            weights.append(1.0)
    z = sum(weights) or float(n)
    p_s = [w / z for w in weights]
    h_s = entropy(p_s)
    df = Counter()
    for _, toks in docs:
        df.update(set(toks))
    cond = []
    for _, qtoks in docs:
        qset = set(qtoks)
        scores = []
        for _, dtoks in docs:
            tf = Counter(dtoks)
            sc = 0.0
            for t in qset:
                idf = math.log((n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5) + 1.0)
                sc += idf * tf.get(t, 0)
            scores.append(sc)
        cond.append(entropy(softmax(scores)))
    h_s_q = sum(cond) / max(len(cond), 1)
    mi = max(0.0, h_s - h_s_q)
    ratio = mi / h_s if h_s > EPS else 0.0
    alarm = ratio < RATIO_ALARM
    return {
        'ts': time.time(),
        'n_skills': n,
        'H_S': round(h_s, 6),
        'H_S_Q': round(h_s_q, 6),
        'I_S_Q': round(mi, 6),
        'I_over_H': round(ratio, 6),
        'alarm': alarm,
        'reason': 'I(S;Q)/H(S) < 0.05 (near-chance routing)' if alarm else 'ok',
    }


def run(cache: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    index = _load_json(cache / 'skill-router-index.json', {})
    beta = _load_json(cache / 'skill-beta-state.json', {})
    result = compute(index if isinstance(index, dict) else {},
                     beta if isinstance(beta, dict) else {})
    try:
        _atomic_write_json(cache / 'routing-mutual-information.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    try:
        # identical tokens => I ~ 0
        idx = {'skills': [
            {'name': 'a', 'tokens': ['same', 'tok']},
            {'name': 'b', 'tokens': ['same', 'tok']},
        ]}
        r = compute(idx, {})
        assert r['I_S_Q'] < 0.05, r
        assert r['alarm'] is True
    except Exception as e:
        failures.append(f'identical: {e}')
    try:
        idx = {'skills': [
            {'name': 'a', 'tokens': ['alpha', 'unique', 'bandit']},
            {'name': 'b', 'tokens': ['topology', 'homology', 'hatcher']},
        ]}
        r = compute(idx, {})
        assert r['I_S_Q'] > 0.2, r
        assert r['alarm'] is False
        json.dumps(r)
    except Exception as e:
        failures.append(f'distinct: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            r = run(cache=Path(td))
            assert r['n_skills'] == 0
    except Exception as e:
        failures.append(f'missing: {e}')
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
