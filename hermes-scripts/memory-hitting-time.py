#!/usr/bin/env python3
"""memory-hitting-time.py — Brownian hitting time as commit wait.

Morters–Peres: for standard Brownian motion, E_0[τ_a] = ∞ but for BM with
variance σ^2 t the expected hitting time of level a for a random walk
approximation is a^2 / σ^2. For drifted BM, E[τ_a] = a / μ if μ>0.

UE path treated as RW. Barrier = DENY_UE (0.75). Predicted wait (steps)
vs observed steps-to-barrier. Alarm if we commit (cross) in << predicted
time (premature memory write).

Usage:
  python3 memory-hitting-time.py --self-test
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

BARRIER = 0.75
PREMATURE_RATIO = 0.25


def _clip01(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(v):
        return 0.5
    return max(0.0, min(1.0, v))


def hitting_stats(path: list, barrier: float = BARRIER) -> dict:
    xs = [_clip01(x) for x in (path or [])]
    n = len(xs)
    if n < 3:
        return {'n': n, 'pred_steps': 0.0, 'obs_steps': None, 'alarm': False, 'reason': 'short'}
    diffs = [xs[i] - xs[i - 1] for i in range(1, n)]
    mu = sum(diffs) / len(diffs)
    var = sum((d - mu) ** 2 for d in diffs) / len(diffs)
    sigma2 = max(var, 1e-9)
    x0 = xs[0]
    gap = max(barrier - x0, 0.0)
    if mu > 1e-6:
        pred = gap / mu
    else:
        pred = (gap * gap) / sigma2
    obs = None
    for i, x in enumerate(xs):
        if x >= barrier:
            obs = i
            break
    premature = False
    if obs is not None and pred > 4 and obs < PREMATURE_RATIO * pred:
        premature = True
    return {
        'n': n,
        'mu': round(mu, 6),
        'sigma2': round(sigma2, 6),
        'barrier': barrier,
        'pred_steps': round(pred, 4),
        'obs_steps': obs,
        'alarm': premature,
        'reason': 'premature_hit' if premature else 'ok',
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
    return out[-300:]


def compute(path=None) -> dict:
    try:
        rec = hitting_stats(list(path) if path is not None else load_ue())
        _atomic_write(_cache_dir() / 'memory-hitting-time.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    # Slow climb: mu small, hit late
    slow = [0.1 + 0.01 * i for i in range(80)]
    r = hitting_stats(slow, barrier=0.75)
    assert r['pred_steps'] > 1
    # Instant jump
    jump = [0.1, 0.9, 0.9, 0.9]
    r2 = hitting_stats(jump, barrier=0.75)
    assert r2['obs_steps'] == 1
    empty = hitting_stats([0.2, 0.2])
    assert empty['n'] == 2
    print('PASS memory-hitting-time self-test')
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
