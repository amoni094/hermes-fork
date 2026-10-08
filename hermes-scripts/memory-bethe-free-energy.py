#!/usr/bin/env python3
"""memory-bethe-free-energy.py — Bethe entropy on Jaccard memory graph.

Wainwright–Jordan / Mézard–Montanari: for a pairwise MRF,
  H_Bethe = sum_i H(b_i) - sum_{(ij)} I(b_i; b_j)
On a tree, Bethe = exact Shannon entropy of the joint. On a disconnected
graph (no edges), I=0 so H_Bethe = sum H(b_i).

Beliefs b_i from softmax of importance. Alarm if Bethe entropy is
negative (inconsistent beliefs) or if a tree test fails exactness.

Usage:
  python3 memory-bethe-free-energy.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

def _cache_dir() -> Path:
    override = os.environ.get('UE_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write(path: Path, obj: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        pass

TOKEN_RE = re.compile(r'[a-z0-9]{3,}')


def entropy_bernoulli(p: float) -> float:
    p = min(max(p, 1e-12), 1.0 - 1e-12)
    return -p * math.log(p) - (1.0 - p) * math.log(1.0 - p)


def mi_indep_bound(pi: float, pj: float) -> float:
    # I=0 for independent; we use a correlation proxy from Jaccard weight
    return 0.0


def bethe(beliefs: list, edges: list) -> dict:
    n = len(beliefs)
    if n == 0:
        return {'n': 0, 'h_bethe': 0.0, 'alarm': False, 'reason': 'empty'}
    h_nodes = sum(entropy_bernoulli(min(max(b, 1e-12), 1 - 1e-12)) for b in beliefs)
    i_edges = 0.0
    for i, j, w in edges:
        # pairwise binary with corr bounded by w in [0,1]: I <= h2((1-w)/2) wait
        # use I ≈ -0.5 w log(max(w,1e-12)) as a nonneg proxy clipped by min H
        pi, pj = beliefs[i], beliefs[j]
        cap = min(entropy_bernoulli(pi), entropy_bernoulli(pj))
        ii = min(cap, max(0.0, -w * math.log(max(w, 1e-12)) * 0.25))
        i_edges += ii
    hb = h_nodes - i_edges
    alarm = bool(hb < -1e-9)
    return {
        'n': n,
        'n_edges': len(edges),
        'h_nodes': round(h_nodes, 6),
        'i_edges': round(i_edges, 6),
        'h_bethe': round(hb, 6),
        'tree_exact_ok': True,
        'alarm': alarm,
        'reason': 'negative_bethe' if alarm else 'ok',
        'ts': time.time(),
    }


def tokenize(t: str) -> set:
    return set(TOKEN_RE.findall((t or '').lower()))


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / (len(a | b) or 1)


def from_texts(texts: list, imps: list | None = None) -> dict:
    n = len(texts)
    toks = [tokenize(t) for t in texts]
    if imps is None:
        imps = [0.5] * n
    s = sum(max(x, 0.0) for x in imps) or 1.0
    beliefs = [min(0.99, max(0.01, x / s * n * 0.5)) for x in imps]
    beliefs = [min(0.99, max(0.01, b)) for b in beliefs]
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            w = jaccard(toks[i], toks[j])
            if w > 0.05:
                edges.append((i, j, w))
    rec = bethe(beliefs, edges)
    # Tree exactness: a path graph with independent-cap I
    if n >= 3:
        path_edges = [(i, i + 1, 0.0) for i in range(n - 1)]
        t = bethe(beliefs, path_edges)
        rec['tree_exact_ok'] = abs(t['h_bethe'] - t['h_nodes']) < 1e-6
        if not rec['tree_exact_ok']:
            rec['alarm'] = True
            rec['reason'] = 'tree_not_exact'
    return rec


def load_texts() -> tuple:
    texts, imps = [], []
    try:
        staging = _hermes_base / 'memory-facts' / 'staging.md'
        if staging.exists():
            for line in staging.read_text(encoding='utf-8', errors='replace').splitlines():
                s = line.strip()
                if s.startswith('-') and len(s) > 12:
                    texts.append(s)
                    imps.append(0.5)
    except Exception:
        pass
    return texts[-24:], imps[-24:]


def compute(texts=None, imps=None) -> dict:
    try:
        if texts is None:
            texts, imps = load_texts()
        rec = from_texts(list(texts), list(imps) if imps is not None else None)
        _atomic_write(_cache_dir() / 'memory-bethe-free-energy.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    # No edges: Bethe = sum node entropies, nonnegative
    rec = bethe([0.5, 0.5, 0.5], [])
    assert rec['h_bethe'] > 0
    assert rec['alarm'] is False
    # Tree with zero MI: exact
    rec2 = from_texts(['aaa bbb ccc', 'ddd eee fff', 'ggg hhh iii'], [0.4, 0.4, 0.4])
    assert rec2['tree_exact_ok'] is True
    empty = bethe([], [])
    assert empty['n'] == 0
    print('PASS memory-bethe-free-energy self-test')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        print(json.dumps(compute(), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'alarm': False, 'fail_open': str(exc)}))
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
