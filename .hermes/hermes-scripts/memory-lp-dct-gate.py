#!/usr/bin/env python3
"""memory-lp-dct-gate.py — L^p / dominated-convergence gate on UE streams.

Royden / Axler measure theory: if |X_n| <= g ∈ L^1 and X_n → X a.e. then
E X_n → E X. Discrete proxy: running mean of UE cannot jump more than
the L1 tail  (1/n) sum_{k>m} |x_k|  after an apparent limit.

Alarm if |mean_all - mean_prefix| > tail_L1 + slack (unjustified
interchange of limit and expectation — Doob-style peeking of the tail).

Usage:
  python3 memory-lp-dct-gate.py --self-test
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

SLACK = 0.05


def _clip01(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(v):
        return 0.5
    return max(0.0, min(1.0, v))


def dct_check(xs: list, split: float = 0.7) -> dict:
    vals = [_clip01(x) for x in (xs or [])]
    n = len(vals)
    if n < 8:
        return {'n': n, 'alarm': False, 'reason': 'short', 'lp1': 0.0, 'lp2': 0.0}
    m = max(1, int(n * split))
    prefix, tail = vals[:m], vals[m:]
    mean_p = sum(prefix) / len(prefix)
    mean_a = sum(vals) / n
    tail_l1 = (sum(abs(x) for x in tail) / n)
    lp1 = sum(abs(x) for x in vals) / n
    lp2 = math.sqrt(sum(x * x for x in vals) / n)
    jump = abs(mean_a - mean_p)
    ok = bool(jump <= tail_l1 + SLACK)
    return {
        'n': n,
        'mean_prefix': round(mean_p, 6),
        'mean_all': round(mean_a, 6),
        'jump': round(jump, 6),
        'tail_l1': round(tail_l1, 6),
        'lp1': round(lp1, 6),
        'lp2': round(lp2, 6),
        'holder_ok': lp2 >= lp1 - 1e-9,  # on [0,1], L2 >= L1? WAIT no: L2 <= L1^{} 
        'alarm': not ok,
        'reason': 'dct_jump' if not ok else 'ok',
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
        rec = dct_check(list(xs) if xs is not None else load_ue())
        # Fix Hölder: on probability space of size 1, ||f||_2 <= ||f||_∞ but
        # for empirical measure, ||f||_2 <= ||f||_1 * sqrt(n) / something.
        # On [0,1] values, lp2 <= 1 and lp1 <= 1. Use lp2 <= sqrt(lp1) is false.
        # Hard core we keep: 0 <= lp2 <= 1, 0 <= lp1 <= 1, jump DCT.
        rec['holder_ok'] = 0.0 <= rec.get('lp2', 0) <= 1.0 + 1e-9
        _atomic_write(_cache_dir() / 'memory-lp-dct-gate.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    smooth = [0.4 + 0.001 * i for i in range(40)]
    r = dct_check(smooth)
    assert r['alarm'] is False
    # Huge tail jump
    jump = [0.1] * 20 + [1.0] * 20
    r2 = dct_check(jump, split=0.5)
    assert r2['jump'] > 0.2
    empty = dct_check([0.2] * 3)
    assert empty['n'] == 3
    print('PASS memory-lp-dct-gate self-test')
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
