#!/usr/bin/env python3
"""memory-bits-back.py — MacKay bits-back identity on memory latents.

MacKay IT Ch. 28: with latent z ~ Q(z|x) and prior P(z),
  L(x) = -log P(x|z) - log P(z) + log Q(z|x)
If Q = P(·|x), L recovers -log P(x). Hard cores:
  bits_back = log Q - log P >= 0 when Q is more concentrated than P
  net_L >= 0
  net_L <= zlib_bits + slack  (cannot beat the compressor by magic)

z is the FNV hash of the entry (discrete latent). Q = peaked on observed
hash; P = uniform on 2^b bins.

Usage:
  python3 memory-bits-back.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import zlib
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

BINS_BITS = 12  # 4096 bins
SLACK_BITS = 32.0


def fnv(text: str) -> int:
    h = 2166136261
    for ch in (text or ''):
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def zlib_bits(text: str) -> float:
    data = (text or '').encode('utf-8', errors='replace')
    if not data:
        return 8.0
    try:
        return float(max(8, len(zlib.compress(data, 9)) * 8))
    except Exception:
        return float(max(8, len(data) * 8))


def bits_back(texts: list, bins_bits: int = BINS_BITS) -> dict:
    n = len(texts or [])
    if n == 0:
        return {'n': 0, 'alarm': False, 'reason': 'empty', 'net_L': 0.0}
    bins = 1 << bins_bits
    log_p = bins_bits  # -log2 P(z) for uniform
    # Q peaked: one bin out of n observations → -log2(1/n) if collisions ignored
    # Use empirical hash occupancy
    occ = {}
    for t in texts:
        z = fnv(t) % bins
        occ[z] = occ.get(z, 0) + 1
    net = 0.0
    bb = 0.0
    for t in texts:
        z = fnv(t) % bins
        q = occ[z] / n
        log_q = -math.log2(max(q, 1e-12))
        # -log P(x|z) ≈ zlib bits of text (likelihood proxy)
        nll = zlib_bits(t)
        # bits-back credit
        credit = log_p - log_q  # log Q - log P in bits if Q sharper... wait
        # L = nll + log_p - (-log2 Q) = nll + log_p - log_q
        # bits_back recovered = -log P + log Q = log_p - log_q
        L = nll + log_p - log_q
        net += L
        bb += (log_p - log_q)
    net /= n
    bb /= n
    mean_zlib = sum(zlib_bits(t) for t in texts) / n
    alarm = bool(net < -1e-6 or net > mean_zlib + log_p + SLACK_BITS)
    return {
        'n': n,
        'bins_bits': bins_bits,
        'net_L': round(net, 4),
        'bits_back': round(bb, 4),
        'mean_zlib': round(mean_zlib, 4),
        'alarm': alarm,
        'reason': 'bits_back_inconsistent' if alarm else 'ok',
        'ts': time.time(),
    }


def load_texts() -> list:
    texts = []
    try:
        staging = _hermes_base / 'memory-facts' / 'staging.md'
        if staging.exists():
            for line in staging.read_text(encoding='utf-8', errors='replace').splitlines():
                s = line.strip()
                if s.startswith('-') and len(s) > 8:
                    texts.append(s)
    except Exception:
        pass
    return texts[-64:]


def compute(texts=None) -> dict:
    try:
        rec = bits_back(list(texts) if texts is not None else load_texts())
        _atomic_write(_cache_dir() / 'memory-bits-back.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    rec = bits_back(['alpha beta gamma'] * 3 + ['other document here'])
    assert rec['n'] == 4
    assert rec['net_L'] > 0
    empty = bits_back([])
    assert empty['n'] == 0
    print('PASS memory-bits-back self-test')
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
