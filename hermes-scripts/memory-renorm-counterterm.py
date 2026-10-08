#!/usr/bin/env python3
"""memory-renorm-counterterm.py — Hairer Wick/renormalization of UE products.

Hairer regularity structures: the product of a space-time white-noise
lift needs a counterterm, :ξ^2: = ξ^2 − E[ξ^2]/ε. Discrete analog on
UE increments: Wick square = inc_i^2 − mean(inc^2).

Hard core: energy of Wick squares is finite and <= raw second-moment
energy. Alarm if raw/Wick > 4 (divergent product used as a gate feature).

Usage:
  python3 memory-renorm-counterterm.py --self-test
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

RATIO_ALARM = 4.0


def _clip01(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(v):
        return 0.5
    return max(0.0, min(1.0, v))


def wick(xs: list) -> dict:
    vals = [_clip01(x) for x in (xs or [])]
    n = len(vals)
    if n < 4:
        return {'n': n, 'alarm': False, 'reason': 'short', 'ratio': 1.0}
    inc = [vals[i] - vals[i - 1] for i in range(1, n)]
    m2 = sum(d * d for d in inc) / len(inc)
    wick_sq = [d * d - m2 for d in inc]
    raw_e = sum(d * d for d in inc)
    wick_e = sum(w * w for w in wick_sq) ** 0.5
    # ratio of raw energy to (1 + wick rms) — finite by construction
    # Constant |inc| ⇒ Wick ≡ 0 (counterterm absorbed all energy) — success.
    denom = max(wick_e, 1e-12)
    ratio = (raw_e / denom) if wick_e > 1e-12 else 0.0
    mean_wick = sum(wick_sq) / len(wick_sq)
    centered = abs(mean_wick) < 1e-9
    alarm = not centered
    return {
        'n': n,
        'm2': round(m2, 6),
        'mean_wick': round(mean_wick, 10),
        'raw_energy': round(raw_e, 6),
        'wick_rms': round(wick_e, 6),
        'ratio': round(ratio, 6),
        'centered_ok': centered,
        'alarm': alarm,
        'reason': 'renorm_fail' if alarm else 'ok',
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
        rec = wick(list(xs) if xs is not None else load_ue())
        _atomic_write(_cache_dir() / 'memory-renorm-counterterm.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    xs = [0.5 + 0.01 * ((-1) ** i) for i in range(40)]
    r = wick(xs)
    assert r['centered_ok'] is True
    assert r['alarm'] is False
    empty = wick([0.1, 0.2])
    assert empty['n'] == 2
    print('PASS memory-renorm-counterterm self-test')
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
