#!/usr/bin/env python3
"""memory-malliavin-ibp.py — Gaussian integration-by-parts sensitivity.

Hairer / Nualart Malliavin: for F = f(X), X~N(0,1),
  E[X f(X)] = E[f'(X)].
Finite-difference f' on standardized UE scores. Gate sensitivity =
E[f'] vs empirical covariance. Alarm if |E[X f(X)] - E[f']| > slack
(score-to-decision map not Sobolev — UE gate is non-Lipschitz / brittle).

Usage:
  python3 memory-malliavin-ibp.py --self-test
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

SLACK = 0.25
H = 1e-3


def _f(x: float) -> float:
    # logistic commit gate around 0 (standardized UE)
    return 1.0 / (1.0 + math.exp(-x))


def _fp_fd(x: float, h: float = H) -> float:
    return (_f(x + h) - _f(x - h)) / (2.0 * h)


def ibp_check(raw: list) -> dict:
    xs = []
    for v in (raw or []):
        try:
            xs.append(float(v))
        except (TypeError, ValueError):
            continue
    n = len(xs)
    if n < 4:
        return {'n': n, 'alarm': False, 'reason': 'short', 'residual': 0.0}
    mu = sum(xs) / n
    var = sum((x - mu) ** 2 for x in xs) / n
    sd = math.sqrt(max(var, 1e-12))
    z = [(x - mu) / sd for x in xs]
    left = sum(zi * _f(zi) for zi in z) / n
    right = sum(_fp_fd(zi) for zi in z) / n
    resid = abs(left - right)
    return {
        'n': n,
        'left_EXf': round(left, 6),
        'right_Efprime': round(right, 6),
        'residual': round(resid, 6),
        'alarm': bool(resid > SLACK),
        'reason': 'ibp_fail' if resid > SLACK else 'ok',
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
                    out.append(float(row['composite_ue']))
    except Exception:
        pass
    return out[-400:]


def compute(xs=None) -> dict:
    try:
        rec = ibp_check(list(xs) if xs is not None else load_ue())
        _atomic_write(_cache_dir() / 'memory-malliavin-ibp.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    # Box-Muller lite: inverse-erf via 12-uniform CLT
    import random
    rng = random.Random(0)
    gauss = [sum(rng.random() for _ in range(12)) - 6.0 for _ in range(400)]
    r = ibp_check(gauss)
    assert r['residual'] < SLACK
    assert r['alarm'] is False
    empty = ibp_check([0.1, 0.2])
    assert empty['n'] == 2
    print('PASS memory-malliavin-ibp self-test')
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
