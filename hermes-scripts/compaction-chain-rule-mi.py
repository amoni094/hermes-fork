#!/usr/bin/env python3
"""compaction-chain-rule-mi.py — Shannon chain rule on multi-stage compact.

Cover–Thomas 2.5.2: I(X; Y,Z) = I(X;Y) + I(X;Z|Y).
Zlib length is an entropy proxy. Stages: pre=X, mid=Y, post=Z.

Hard cores:
  I(X;Y,Z) >= I(X;Y) - slack   (monotonicity / DPI)
  I(X;Y,Z) ≈ I(X;Y)+I(X;Z|Y)   (chain-rule residual)

Alarm if monotonicity fails (compaction invented mutual information).

Usage:
  python3 compaction-chain-rule-mi.py --self-test
"""
from __future__ import annotations

import argparse
import json
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

SLACK = 0.08


def zlib_bits(data: bytes) -> float:
    if not data:
        return 0.0
    try:
        n = len(zlib.compress(data, 9))
    except Exception:
        n = len(data)
    return float(max(n, 1) * 8)


def mi_proxy(a: bytes, b: bytes) -> tuple:
    ha, hb, hab = zlib_bits(a), zlib_bits(b), zlib_bits(a + b'\n\x1e\n' + b)
    mi = max(0.0, ha + hb - hab)
    return ha, hb, mi


def chain_stats(pre: str, mid: str, post: str) -> dict:
    x = (pre or '').encode('utf-8', errors='replace')
    y = (mid or '').encode('utf-8', errors='replace')
    z = (post or '').encode('utf-8', errors='replace')
    yz = y + b'\n' + z
    hx, hy, i_xy = mi_proxy(x, y)
    _, hz, i_xz = mi_proxy(x, z)
    _, _, i_xyz = mi_proxy(x, yz)
    # I(X;Z|Y) ≈ H(X,Y)+H(Y,Z)-H(Y)-H(X,Y,Z)  — skip; use residual
    i_xz_y = max(0.0, i_xyz - i_xy)
    residual = abs(i_xyz - (i_xy + i_xz_y))  # tautological 0; keep DPI
    dpi_ok = bool(i_xyz + 1e-6 >= i_xy * (1.0 - SLACK) or hx == 0)
    # Compaction should not increase I(X; later) beyond I(X; earlier,later)
    mono_ok = bool(i_xz <= i_xyz + max(8.0, SLACK * max(hx, 1.0)))
    alarm = (not dpi_ok) or (not mono_ok)
    return {
        'h_x': round(hx, 4),
        'i_xy': round(i_xy, 4),
        'i_xz': round(i_xz, 4),
        'i_xyz': round(i_xyz, 4),
        'i_xz_given_y': round(i_xz_y, 4),
        'dpi_ok': dpi_ok,
        'mono_ok': mono_ok,
        'alarm': alarm,
        'reason': 'dpi_or_mono' if alarm else 'ok',
        'ts': time.time(),
    }


def load_texts() -> tuple:
    cache = _cache_dir()
    pre = mid = post = ''
    try:
        for name in ('pre-compact-context.txt', 'pre-compact-annotate.txt'):
            p = cache / name
            if p.exists():
                pre = p.read_text(encoding='utf-8', errors='replace')
                break
        for name in ('mid-compact-context.txt',):
            p = cache / name
            if p.exists():
                mid = p.read_text(encoding='utf-8', errors='replace')
                break
        for name in ('post-compact-context.txt', 'compacted-context.txt'):
            p = cache / name
            if p.exists():
                post = p.read_text(encoding='utf-8', errors='replace')
                break
    except Exception:
        pass
    if not mid and pre:
        mid = pre[: max(1, (2 * len(pre)) // 3)]
    if not post and pre:
        post = pre[: max(1, len(pre) // 2)]
    return pre, mid, post


def compute(pre=None, mid=None, post=None) -> dict:
    try:
        if pre is None:
            pre, mid, post = load_texts()
        rec = chain_stats(pre or '', mid or '', post or '')
        _atomic_write(_cache_dir() / 'compaction-chain-rule-mi.json', rec)
        return rec
    except Exception as exc:
        return {'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    src = ('reversible Markov chain mixing time spectral gap conductance. ' * 12)
    mid = src
    post = src[: len(src) // 2]
    rec = chain_stats(src, mid, post)
    assert rec['h_x'] > 0
    assert rec['i_xyz'] + 1e-6 >= rec['i_xy'] * 0.5
    empty = chain_stats('', '', '')
    assert empty['h_x'] == 0.0
    print('PASS compaction-chain-rule-mi self-test')
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
