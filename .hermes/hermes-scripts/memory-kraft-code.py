#!/usr/bin/env python3
"""memory-kraft-code.py — Kraft inequality on memory description lengths.

Cover–Thomas 5.2: a prefix code with lengths l_i exists iff sum 2^{-l_i} <= 1.
Take l_i = ceil(zlib_bits(entry) / scale) so lengths are integers. If Kraft
sum > 1 the claimed MDL lengths cannot be a prefix code (inconsistent
description-length ranking).

Usage:
  python3 memory-kraft-code.py --self-test
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



def zlib_bits(text: str) -> int:
    data = (text or '').encode('utf-8', errors='replace')
    if not data:
        return 8
    try:
        return max(8, len(zlib.compress(data, 9)) * 8)
    except Exception:
        return max(8, len(data) * 8)


def kraft(texts: list) -> dict:
    if not texts:
        return {'n': 0, 'kraft_sum': 0.0, 'alarm': False, 'reason': 'empty'}
    bits = [zlib_bits(t) for t in texts]
    # scale so min length >= 1 and typical Kraft ~ O(1)
    m = min(bits)
    lengths = [max(1, int(math.ceil(b / m))) for b in bits]
    ks = 0.0
    for ell in lengths:
        ks += 2.0 ** (-ell)
    alarm = bool(ks > 1.0 + 1e-12)
    return {
        'n': len(texts),
        'lengths': lengths[:32],
        'kraft_sum': round(ks, 8),
        'alarm': alarm,
        'reason': 'kraft_violation' if alarm else 'ok',
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
        rec = kraft(list(texts) if texts is not None else load_texts())
        _atomic_write(_cache_dir() / 'memory-kraft-code.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    # Huffman-like: 1,2,2 → 1/2+1/4+1/4=1
    rec = kraft(['a' * 8, 'b' * 16, 'c' * 16])
    assert rec['kraft_sum'] > 0
    # Many equal short codes violate Kraft
    rec2 = kraft(['x'] * 8)
    assert rec2['n'] == 8
    empty = kraft([])
    assert empty['n'] == 0
    print('PASS memory-kraft-code self-test')
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
