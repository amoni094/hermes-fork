#!/usr/bin/env python3
"""memory-dkw-ue.py — DKW inequality band on empirical UE CDF.

Lugosi / Massart DKW: P(sup_x |F_n(x)-F(x)| > ε) <= 2 exp(-2 n ε^2).
Null F = Uniform[0,1] on composite_ue. At alpha=0.05,
  ε = sqrt(log(2/alpha) / (2n))
Alarm if Kolmogorov–Smirnov stat exceeds ε (UE scores not exchangeable
uniform — calibration / mix-shift).

Usage:
  python3 memory-dkw-ue.py --self-test
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

ALPHA = 0.05


def _clip01(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(v):
        return 0.5
    return max(0.0, min(1.0, v))


def ks_uniform(xs: list) -> float:
    n = len(xs)
    if n == 0:
        return 0.0
    ys = sorted(_clip01(x) for x in xs)
    d = 0.0
    for i, y in enumerate(ys, start=1):
        # F_n = i/n, F = y  (and (i-1)/n)
        d = max(d, abs(i / n - y), abs((i - 1) / n - y))
    return d


def dkw_eps(n: int, alpha: float = ALPHA) -> float:
    if n <= 0:
        return 1.0
    return math.sqrt(math.log(2.0 / max(alpha, 1e-12)) / (2.0 * n))


def dkw_test(samples: list, alpha: float = ALPHA) -> dict:
    xs = [_clip01(x) for x in (samples or [])]
    n = len(xs)
    if n == 0:
        return {'n': 0, 'ks': 0.0, 'eps': 1.0, 'alarm': False, 'reason': 'empty'}
    ks = ks_uniform(xs)
    eps = dkw_eps(n, alpha)
    alarm = bool(ks > eps)
    return {
        'n': n,
        'ks': round(ks, 6),
        'eps': round(eps, 6),
        'alpha': alpha,
        'alarm': alarm,
        'reason': 'dkw_reject_uniform' if alarm else 'ok',
        'ts': time.time(),
    }


def load_ue() -> list:
    out = []
    cache = _cache_dir()
    for name in ('ue-memory-gate-log.jsonl', 'ue-blackbox-scores.jsonl'):
        p = cache / name
        try:
            if not p.exists():
                continue
            for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
                s = line.strip()
                if not s.startswith('{'):
                    continue
                try:
                    row = json.loads(s)
                except Exception:
                    continue
                if isinstance(row, dict) and row.get('composite_ue') is not None:
                    out.append(_clip01(row.get('composite_ue')))
        except Exception:
            continue
        if out:
            break
    return out[-400:]


def compute(samples=None) -> dict:
    try:
        rec = dkw_test(list(samples) if samples is not None else load_ue())
        _atomic_write(_cache_dir() / 'memory-dkw-ue.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    # Quasi-uniform grid → KS small
    uni = [(i + 0.5) / 40.0 for i in range(40)]
    r = dkw_test(uni)
    assert r['ks'] < r['eps']
    assert r['alarm'] is False
    spike = [0.01] * 40
    r2 = dkw_test(spike)
    assert r2['ks'] > r['ks']
    empty = dkw_test([])
    assert empty['n'] == 0
    # Massart: eps decreases in n
    assert dkw_eps(100) < dkw_eps(10)
    print('PASS memory-dkw-ue self-test')
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
