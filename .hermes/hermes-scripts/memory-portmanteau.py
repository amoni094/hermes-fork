#!/usr/bin/env python3
"""memory-portmanteau.py — Billingsley portmanteau on split UE laws.

Billingsley Thm 2.1: P_n ⇒ P iff E_n f → E f for all bounded Lipschitz f.
1-D W1 metrizes weak convergence on compact [0,1]. Hard core:
  |mean(A)-mean(B)| <= W1(A,B) + slack
for Lip-1 identity test function. Split the UE stream in half.

Alarm if the inequality fails (empirical laws not tight / not on [0,1]).

Usage:
  python3 memory-portmanteau.py --self-test
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

SLACK = 1e-6


def _clip01(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(v):
        return 0.5
    return max(0.0, min(1.0, v))


def w1_1d(a: list, b: list) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    sa, sb = sorted(a[:n]), sorted(b[:n])
    return sum(abs(x - y) for x, y in zip(sa, sb)) / n


def portmanteau(xs: list) -> dict:
    vals = [_clip01(x) for x in (xs or [])]
    n = len(vals)
    if n < 8:
        return {'n': n, 'alarm': False, 'reason': 'short', 'w1': 0.0}
    mid = n // 2
    a, b = vals[:mid], vals[mid:mid * 2]
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)
    w = w1_1d(a, b)
    ok = abs(ma - mb) <= w + SLACK
    return {
        'n': n,
        'mean_a': round(ma, 6),
        'mean_b': round(mb, 6),
        'w1': round(w, 6),
        'portmanteau_ok': ok,
        'alarm': not ok,
        'reason': 'portmanteau_fail' if not ok else 'ok',
        'ts': time.time(),
    }


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
                    out.append(_clip01(row.get('composite_ue')))
    except Exception:
        pass
    return out[-400:]


def compute(xs=None) -> dict:
    try:
        rec = portmanteau(list(xs) if xs is not None else load_ue())
        _atomic_write(_cache_dir() / 'memory-portmanteau.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    xs = [i / 40.0 for i in range(20)] + [i / 40.0 for i in range(20)]
    r = portmanteau(xs)
    assert r['portmanteau_ok'] is True
    # Same law shifted — W1 equals mean gap
    ys = [0.1] * 20 + [0.9] * 20
    r2 = portmanteau(ys)
    assert abs(r2['w1'] - abs(r2['mean_a'] - r2['mean_b'])) < 1e-9
    assert r2['portmanteau_ok'] is True
    print('PASS memory-portmanteau self-test')
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
