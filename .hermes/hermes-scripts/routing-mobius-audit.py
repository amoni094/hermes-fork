#!/usr/bin/env python3
"""routing-mobius-audit.py — poset Mobius inversion for BM25 inclusion-exclusion.

Skill A <= B iff tokens(A) subset tokens(B).
corrected(A) = sum_{A<=B} mu(A,B) * BM25(Q,B)
Flag top-5 rank inversions vs raw BM25.

Source: Stanley, Enumerative Combinatorics (Mobius inversion on posets).
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

K1 = 1.2
B = 0.75
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


def build_poset(token_map: dict) -> dict:
    """leq[a] = list of b such that a <= b (tokens a subset tokens b)."""
    names = list(token_map)
    leq = {a: [] for a in names}
    for a in names:
        ta = token_map[a]
        for b in names:
            tb = token_map[b]
            if ta.issubset(tb):
                leq[a].append(b)
    return leq


def mobius_function(leq: dict) -> dict:
    """mu[(x,y)] via recursive inversion: mu(x,x)=1; mu(x,y)= -sum_{x<=z<y} mu(x,z)."""
    names = list(leq)
    # interval: z in [x,y] if x<=z and z<=y
    # Precompute <= as sets
    leq_set = {a: set(bs) for a, bs in leq.items()}
    mu = {}
    for x in names:
        mu[(x, x)] = 1
        def _interval_size(y, _x=x):
            # |{z : x <= z <= y}|
            n = 0
            for z in leq_set[_x]:
                if y in leq_set.get(z, ()):
                    n += 1
            return n
        above = sorted(leq_set[x], key=_interval_size)
        for y in above:
            if y == x:
                continue
            s = 0
            for z in leq_set[x]:
                if z == y:
                    continue
                if y in leq_set.get(z, ()):
                    s += mu.get((x, z), 0)
            mu[(x, y)] = -s
    return mu


def bm25_scores(query_tokens: list, token_map: dict) -> dict:
    names = list(token_map)
    n = max(len(names), 1)
    df = Counter()
    lens = []
    tfs = {}
    for name in names:
        toks = list(token_map[name])
        tfs[name] = Counter(token_map[name])  # set originally; treat presence tf=1
        # restore multiplicity-less tf
        df.update(set(token_map[name]))
        lens.append(max(len(token_map[name]), 1))
    avgdl = sum(lens) / max(len(lens), 1)
    qset = [t.lower() for t in query_tokens]
    scores = {}
    for name in names:
        tfmap = Counter(token_map[name])
        dl = max(len(token_map[name]), 1)
        sc = 0.0
        for t in qset:
            f = tfmap.get(t, 0)
            if f <= 0:
                continue
            idf = math.log((n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5) + 1.0)
            den = f + K1 * (1.0 - B + B * dl / avgdl)
            sc += idf * (f * (K1 + 1.0) / max(den, EPS))
        scores[name] = sc
    return scores


def corrected_scores(raw: dict, leq: dict, mu: dict) -> dict:
    out = {}
    for a in leq:
        s = 0.0
        for b in leq[a]:
            s += mu.get((a, b), 0) * raw.get(b, 0.0)
        out[a] = s
    return out


def rank(scores: dict) -> list:
    return [k for k, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]


def inversions(raw_top: list, corr_top: list) -> list:
    flags = []
    n = min(5, len(raw_top), len(corr_top))
    raw5, corr5 = raw_top[:5], corr_top[:5]
    for i, name in enumerate(corr5):
        if name not in raw5:
            flags.append({'skill': name, 'corrected_rank': i + 1, 'raw_rank': None, 'kind': 'entered_top5'})
        else:
            ri = raw5.index(name)
            if ri != i:
                flags.append({'skill': name, 'corrected_rank': i + 1, 'raw_rank': ri + 1, 'kind': 'rank_swap'})
    return flags


def compute(token_map: dict, query_tokens: list) -> dict:
    leq = build_poset(token_map)
    mu = mobius_function(leq)
    raw = bm25_scores(query_tokens, token_map)
    corr = corrected_scores(raw, leq, mu)
    rt, ct = rank(raw), rank(corr)
    inv = inversions(rt, ct)
    n_rel = sum(1 for a in leq if len(leq[a]) > 1)
    return {
        'n_skills': len(token_map),
        'n_comparable_pairs': n_rel,
        'query_tokens': query_tokens[:32],
        'raw_top5': [{'skill': s, 'score': round(raw[s], 6)} for s in rt[:5]],
        'corrected_top5': [{'skill': s, 'score': round(corr[s], 6)} for s in ct[:5]],
        'inversions': inv,
        'alarm': len(inv) > 0,
    }


def token_map_from_index(index: dict) -> dict:
    out = {}
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        for s in skills:
            if not isinstance(s, dict) or not s.get('name'):
                continue
            toks = {t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)}
            out[s['name']] = toks
    return out


def run(cache: Path | None = None, query: str = '') -> dict:
    cache = cache or _cache_dir()
    index = _load_json(cache / 'skill-router-index.json', {})
    tmap = token_map_from_index(index if isinstance(index, dict) else {})
    qtoks = [t.lower() for t in (query.split() if query else ['skill', 'routing'])]
    if not tmap:
        result = {'n_skills': 0, 'inversions': [], 'alarm': False, 'note': 'empty_index'}
    else:
        result = compute(tmap, qtoks)
    result['ts'] = time.time()
    try:
        _atomic_write_json(cache / 'routing-mobius-audit.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    try:
        # chain A ⊂ B ⊂ C
        tmap = {
            'A': {'x'},
            'B': {'x', 'y'},
            'C': {'x', 'y', 'z'},
            'D': {'q'},
        }
        leq = build_poset(tmap)
        assert set(leq['A']) >= {'A', 'B', 'C'}
        mu = mobius_function(leq)
        assert mu[('A', 'A')] == 1
        # chain of length 3: mu(A,C) = 0 (standard total order: mu(i,i+2)=0)
        assert mu[('A', 'B')] == -1
        assert mu[('A', 'C')] == 0, mu
        assert ('A', 'D') not in mu or mu[('A', 'D')] == 0
    except Exception as e:
        failures.append(f'mobius-chain: {e}')
    try:
        tmap = {
            'narrow': {'bandit', 'exp3'},
            'wide': {'bandit', 'exp3', 'routing', 'skill'},
            'other': {'topology', 'homology'},
        }
        r = compute(tmap, ['bandit', 'exp3'])
        assert r['n_skills'] == 3
        json.dumps(r)
        # rank lists exist
        assert len(r['raw_top5']) >= 1
    except Exception as e:
        failures.append(f'scores: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d, query='skill routing')
            assert (d / 'routing-mobius-audit.json').exists()
    except Exception as e:
        failures.append(f'missing: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--query', default='skill routing')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        r = run(query=args.query)
        print(json.dumps(r, indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
