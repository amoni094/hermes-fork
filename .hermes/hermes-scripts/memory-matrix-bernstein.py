#!/usr/bin/env python3
"""memory-matrix-bernstein.py — matrix Bernstein on hash Gram.

Vershynin HDP / Tropp: for centered self-adjoint X_i, ||X_i||<=R,
  P(||sum X_i|| >= t) <= 2d exp(-t^2/2 / (σ^2 + Rt/3)).

Gram G = A^T A of hash embeddings vs (n/d) I. Deviation vs Bernstein
tail. Alarm if operator-norm proxy (Frobenius of G - n/d I) exceeds
the bound at t = 3σ.

Usage:
  python3 memory-matrix-bernstein.py --self-test
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
DIM = 16


def tokenize(t: str) -> set:
    return set(TOKEN_RE.findall((t or '').lower()))


def embed(toks: set, dim: int = DIM) -> list:
    v = [0.0] * dim
    for tok in toks:
        h = 2166136261
        for ch in tok:
            h ^= ord(ch)
            h = (h * 16777619) & 0xFFFFFFFF
        v[h % dim] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def frobenius(mat: list) -> float:
    return math.sqrt(sum(x * x for row in mat for x in row))


def bernstein(texts: list, dim: int = DIM) -> dict:
    toks = [tokenize(t) for t in (texts or [])]
    n = len(toks)
    if n < 2:
        return {'n': n, 'alarm': False, 'reason': 'short', 'dev': 0.0}
    rows = [embed(t, dim) for t in toks]
    # G = A^T A  (dim x dim)
    g = [[0.0] * dim for _ in range(dim)]
    for v in rows:
        for i in range(dim):
            for j in range(dim):
                g[i][j] += v[i] * v[j]
    ident = n / dim
    centered = [[g[i][j] - (ident if i == j else 0.0) for j in range(dim)] for i in range(dim)]
    dev = frobenius(centered)
    # crude σ^2 ~ n, R ~ 1
    sigma2 = float(n)
    rbound = 1.0
    t = 3.0 * math.sqrt(max(sigma2, 1e-9))
    thresh = math.sqrt(2.0 * (sigma2 + rbound * t / 3.0) * math.log(2 * dim + 1))
    alarm = bool(dev > max(thresh, t))
    return {
        'n': n,
        'dim': dim,
        'dev_frob': round(dev, 6),
        't': round(t, 6),
        'thresh': round(thresh, 6),
        'alarm': alarm,
        'reason': 'gram_concentration' if alarm else 'ok',
        'ts': time.time(),
    }


def load_texts() -> list:
    texts = []
    try:
        staging = _hermes_base / 'memory-facts' / 'staging.md'
        if staging.exists():
            for line in staging.read_text(encoding='utf-8', errors='replace').splitlines():
                s = line.strip()
                if s.startswith('-') and len(s) > 12:
                    texts.append(s)
    except Exception:
        pass
    return texts[-40:]


def compute(texts=None) -> dict:
    try:
        rec = bernstein(list(texts) if texts is not None else load_texts())
        _atomic_write(_cache_dir() / 'memory-matrix-bernstein.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    docs = ['alpha beta gamma'] * 5 + ['quantum flux pancake'] * 5
    rec = bernstein(docs)
    assert rec['n'] == 10
    assert rec['dev_frob'] >= 0
    empty = bernstein(['only one'])
    assert empty['n'] == 1
    print('PASS memory-matrix-bernstein self-test')
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
