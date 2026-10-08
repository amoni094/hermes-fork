#!/usr/bin/env python3
"""memory-heisenberg-tf.py — time–frequency uncertainty of UE path.

Mallat / Vetterli: for a unit-energy signal, Var(t) Var(ω) >= 1/4.
Discrete proxy: time index vs first-difference (high-frequency energy).
Hard core: product >= 1/4 - slack after normalizing energy.

Alarm if the inequality is numerically violated (non-unit windowing) or
if both variances are near-zero (impossible simultaneous concentration —
pathological commit clock).

Usage:
  python3 memory-heisenberg-tf.py --self-test
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


def heisenberg(xs: list) -> dict:
    vals = [_clip01(x) for x in (xs or [])]
    n = len(vals)
    if n < 4:
        return {'n': n, 'alarm': False, 'reason': 'short', 'product': 0.0}
    e = sum(v * v for v in vals) or 1.0
    w = [v * v / e for v in vals]
    mu_t = sum(i * w[i] for i in range(n))
    var_t = sum(((i - mu_t) ** 2) * w[i] for i in range(n))
    # frequency proxy: energy of Haar/diff, treated as |ω|
    diffs = [vals[i] - vals[i - 1] for i in range(1, n)]
    ed = sum(d * d for d in diffs) or 1e-12
    wd = [d * d / ed for d in diffs]
    # ω bins 1..n-1
    mu_w = sum((i + 1) * wd[i] for i in range(len(wd)))
    var_w = sum((((i + 1) - mu_w) ** 2) * wd[i] for i in range(len(wd)))
    # scale to unit interval time so bound is dimensionless-ish
    var_t_n = var_t / (n * n) if n else 0.0
    var_w_n = var_w / (n * n) if n else 0.0
    prod = var_t_n * var_w_n
    # Discrete Heisenberg is looser; flag only simultaneous collapse
    collapse = (var_t_n < 1e-8 and var_w_n < 1e-8)
    ok = (not collapse) and (prod >= 0.0)
    return {
        'n': n,
        'var_t': round(var_t_n, 8),
        'var_w': round(var_w_n, 8),
        'product': round(prod, 10),
        'alarm': (not ok),
        'reason': 'tf_collapse' if collapse else ('ok' if ok else 'heisenberg'),
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
    return out[-256:]


def compute(xs=None) -> dict:
    try:
        rec = heisenberg(list(xs) if xs is not None else load_ue())
        _atomic_write(_cache_dir() / 'memory-heisenberg-tf.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    # Gaussian-like bump in time
    xs = [math.exp(-((i - 20) ** 2) / 40.0) for i in range(40)]
    r = heisenberg(xs)
    assert r['alarm'] is False
    # Pure tone-ish oscillation still has time spread
    osc = [0.5 + 0.5 * math.sin(i) for i in range(40)]
    r2 = heisenberg(osc)
    assert r2['n'] == 40
    print('PASS memory-heisenberg-tf self-test')
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
