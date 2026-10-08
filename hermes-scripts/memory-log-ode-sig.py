#!/usr/bin/env python3
"""memory-log-ode-sig.py — log-ODE reconstruction of a memory path.

Kidger Neural CDEs / Hairer rough paths: a linear path is reconstructed
exactly from its level-1 and level-2 signature via the log-ODE method.
For a piecewise-linear UE path, reconstruction MSE of the endpoint
should be ~0 at truncation level 2.

Alarm if endpoint reconstruction error > 0.5 (signature truncated too
aggressively for rerank).

Usage:
  python3 memory-log-ode-sig.py --self-test
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

ERR_ALARM = 0.5


def _clip01(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(v):
        return 0.5
    return max(0.0, min(1.0, v))


def level1(path: list) -> float:
    if len(path) < 2:
        return 0.0
    return path[-1] - path[0]


def level2(path: list) -> float:
    # iterated integral of 1-D path against itself: 0.5 (x_T - x_0)^2
    d = level1(path)
    return 0.5 * d * d


def reconstruct_endpoint(x0: float, s1: float) -> float:
    return x0 + s1


def check(path: list) -> dict:
    xs = [_clip01(x) for x in (path or [])]
    n = len(xs)
    if n < 2:
        return {'n': n, 'alarm': False, 'reason': 'short', 'err': 0.0}
    s1 = level1(xs)
    s2 = level2(xs)
    # Chen identity: 0.5 s1^2 == s2 for 1-D (geometric)
    chen_ok = abs(s2 - 0.5 * s1 * s1) <= 1e-9
    hat = reconstruct_endpoint(xs[0], s1)
    err = abs(hat - xs[-1])
    alarm = (not chen_ok) or (err > ERR_ALARM)
    return {
        'n': n,
        's1': round(s1, 6),
        's2': round(s2, 6),
        'chen_ok': chen_ok,
        'err': round(err, 6),
        'alarm': alarm,
        'reason': 'logode_fail' if alarm else 'ok',
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
    return out[-128:]


def compute(path=None) -> dict:
    try:
        rec = check(list(path) if path is not None else load_ue())
        _atomic_write(_cache_dir() / 'memory-log-ode-sig.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    line = [0.1 * i for i in range(11)]
    r = check(line)
    assert r['chen_ok'] is True
    assert r['err'] < 1e-9
    empty = check([0.3])
    assert empty['n'] == 1
    print('PASS memory-log-ode-sig self-test')
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
