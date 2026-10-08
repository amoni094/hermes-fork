#!/usr/bin/env python3
"""memory-haar-mra.py — Haar multi-resolution energy of UE / access path.

Mallat / Vetterli: Haar DWT is an orthogonal MRA. Parseval:
  ||x||^2 = ||a_J||^2 + sum_j ||d_j||^2

High-frequency energy fraction > 0.7 means memory scores are churning
faster than the coarse trend (unstable commit signal).

Usage:
  python3 memory-haar-mra.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
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

HF_ALARM = 0.7


def haar_levels(x: list) -> dict:
    n = len(x)
    if n < 2:
        return {'energy': 0.0, 'approx_energy': 0.0, 'detail_energy': 0.0, 'hf_frac': 0.0, 'levels': 0}
    # pad to power of two
    p = 1
    while p < n:
        p *= 2
    xs = list(x) + [x[-1]] * (p - n)
    details = []
    cur = xs
    while len(cur) >= 2:
        s, d = [], []
        for i in range(0, len(cur), 2):
            a, b = cur[i], cur[i + 1]
            s.append((a + b) / math.sqrt(2.0))
            d.append((a - b) / math.sqrt(2.0))
        details.append(d)
        cur = s
    e_x = sum(v * v for v in xs)
    e_a = sum(v * v for v in cur)
    e_d = sum(sum(v * v for v in lvl) for lvl in details)
    hf = (sum(v * v for v in details[0]) / e_x) if e_x > 0 and details else 0.0
    return {
        'energy': e_x,
        'approx_energy': e_a,
        'detail_energy': e_d,
        'parseval_ok': abs(e_x - (e_a + e_d)) <= 1e-6 * max(e_x, 1.0),
        'hf_frac': hf,
        'levels': len(details),
    }


def analyse(path: list) -> dict:
    xs = []
    for v in (path or []):
        try:
            xs.append(float(v))
        except (TypeError, ValueError):
            continue
    h = haar_levels(xs)
    alarm = bool(h.get('hf_frac', 0.0) > HF_ALARM)
    rec = {
        'n': len(xs),
        'hf_frac': round(float(h.get('hf_frac') or 0.0), 6),
        'parseval_ok': bool(h.get('parseval_ok', True)),
        'levels': int(h.get('levels') or 0),
        'alarm': alarm or (not h.get('parseval_ok', True) and len(xs) >= 2),
        'reason': 'hf_churn' if alarm else ('parseval' if not h.get('parseval_ok', True) else 'ok'),
        'ts': time.time(),
    }
    return rec


def load_ue() -> list:
    out = []
    try:
        p = _cache_dir() / 'ue-memory-gate-log.jsonl'
        if p.exists():
            for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
                s = line.strip()
                if not s.startswith('{'):
                    continue
                try:
                    row = json.loads(s)
                except Exception:
                    continue
                if isinstance(row, dict) and row.get('composite_ue') is not None:
                    out.append(float(row['composite_ue']))
    except Exception:
        pass
    return out[-256:]


def compute(path=None) -> dict:
    try:
        rec = analyse(list(path) if path is not None else load_ue())
        _atomic_write(_cache_dir() / 'memory-haar-mra.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    # Constant: all energy in approximation
    c = haar_levels([1.0] * 16)
    assert c['parseval_ok']
    assert c['hf_frac'] < 1e-9
    # Nyquist alternating
    alt = haar_levels([1.0, -1.0] * 8)
    assert alt['parseval_ok']
    assert alt['hf_frac'] > 0.9
    rec = analyse([1.0, -1.0] * 8)
    assert rec['alarm'] is True
    rec2 = analyse([0.4] * 16)
    assert rec2['alarm'] is False
    print('PASS memory-haar-mra self-test')
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
