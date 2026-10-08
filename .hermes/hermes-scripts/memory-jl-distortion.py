#!/usr/bin/env python3
"""memory-jl-distortion.py — Johnson–Lindenstrauss hash-embedding check.

Blum Foundations of Data Science / JL lemma: a random linear map
R^d → R^k with k >= C ε^{-2} log n preserves pairwise distances
(1±ε) with high probability.

Here k = HASH_DIM hashed token counts. JL preserves Euclidean distances:
compare L2 of L2-normalised bag-of-words vectors (original) to L2 of the
hashed embeddings (projected). Jaccard is a different metric and is NOT
used as the JL baseline. Alarm if max relative distortion > ε while k
is below the JL floor.

Usage:
  python3 memory-jl-distortion.py --self-test
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
HASH_DIM = 32
EPS = 0.5
JL_C = 8.0


def tokenize(text: str) -> set:
    return set(TOKEN_RE.findall((text or '').lower()))


def hash_embed(toks: set, dim: int = HASH_DIM) -> list:
    vec = [0.0] * dim
    for tok in toks:
        h = 2166136261
        for ch in tok:
            h ^= ord(ch)
            h = (h * 16777619) & 0xFFFFFFFF
        vec[h % dim] += 1.0
    nrm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / nrm for x in vec]


def l2(a: list, b: list) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def bow_embed(toks: set, vocab: list) -> list:
    """L2-normalised bag-of-words in the original token basis (Euclidean)."""
    vec = [0.0] * len(vocab)
    idx = {t: i for i, t in enumerate(vocab)}
    for t in toks:
        i = idx.get(t)
        if i is not None:
            vec[i] += 1.0
    nrm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / nrm for x in vec]


def jl_floor(n: int, eps: float = EPS, c: float = JL_C) -> float:
    return c * math.log(max(n, 2)) / max(eps * eps, 1e-9)


def distortion(texts: list, dim: int = HASH_DIM, eps: float = EPS) -> dict:
    toks = [tokenize(t) for t in (texts or [])]
    n = len(toks)
    if n < 2:
        return {'n': n, 'max_rel_distortion': 0.0, 'k': dim, 'k_jl': 0.0, 'alarm': False, 'reason': 'too_few',
                'metric': 'euclidean_l2'}
    vocab = sorted({t for s in toks for t in s})
    orig = [bow_embed(t, vocab) for t in toks]
    embs = [hash_embed(t, dim) for t in toks]
    max_rel = 0.0
    pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            d0 = l2(orig[i], orig[j])
            d1 = l2(embs[i], embs[j])
            pairs += 1
            if d0 <= 1e-9 and d1 <= 1e-9:
                continue
            denom = max(d0, 1e-6)
            rel = abs(d1 - d0) / denom
            if rel > max_rel:
                max_rel = rel
    k_need = jl_floor(n, eps)
    alarm = bool(max_rel > eps and dim < k_need)
    return {
        'n': n,
        'pairs': pairs,
        'max_rel_distortion': round(max_rel, 6),
        'eps': eps,
        'k': dim,
        'k_jl': round(k_need, 4),
        'alarm': alarm,
        'reason': 'jl_distortion' if alarm else 'ok',
        'metric': 'euclidean_l2',
        'scope': 'jl_preserves_euclidean_not_jaccard',
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
        rec = distortion(list(texts) if texts is not None else load_texts())
        _atomic_write(_cache_dir() / 'memory-jl-distortion.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    docs = [
        'alpha beta gamma delta epsilon',
        'alpha beta gamma delta zeta',
        'quantum banana flux pancake maple',
        'quantum banana flux pancake syrup',
    ]
    rec = distortion(docs, dim=32, eps=0.5)
    assert rec['n'] == 4
    assert rec['max_rel_distortion'] >= 0
    # identical docs → distortion 0
    same = distortion(['hello world foo bar'] * 3, dim=16, eps=0.5)
    assert same['max_rel_distortion'] < 1e-9
    empty = distortion([])
    assert empty['n'] == 0
    print('PASS memory-jl-distortion self-test')
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
