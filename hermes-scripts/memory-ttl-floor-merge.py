#!/usr/bin/env python3
"""memory-ttl-floor-merge.py — merge spectral-gap and Cheeger TTL floors.

Hairer/Durrett mixing time vs Levin–Peres Cheeger:
  t_mix >= 1/(2 Phi) - 1
  t_mix <= log(1/(eps pi_min)) / gamma

Legal TTL is at least the max of the two lower bounds. Consumes
memory-mixing-ttl.json and memory-conductance-ttl.json.

Alarm if policy ephemeral (1d) is shorter than the merged floor.

Usage:
  python3 memory-ttl-floor-merge.py --self-test
  python3 memory-ttl-floor-merge.py
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

EPHEMERAL_SECONDS = 86400


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


def _load(name: str) -> dict:
    try:
        p = _cache_dir() / name
        if p.exists():
            obj = json.loads(p.read_text(encoding='utf-8'))
            if isinstance(obj, dict):
                return obj
    except Exception:
        pass
    return {}


def merge_floors(mix: dict, cond: dict, ephemeral_s: int = EPHEMERAL_SECONDS) -> dict:
    mix_days = float(mix.get('tau_mix_days') or 0.0)
    mix_s = max(0.0, mix_days * 86400.0)
    cond_s = float(cond.get('ttl_floor_seconds') or 0.0)
    floor_s = max(mix_s, cond_s, 0.0)
    alarm = bool(ephemeral_s < floor_s and floor_s > 0)
    return {
        'ttl_floor_seconds': int(math.ceil(floor_s)),
        'from_mixing_seconds': int(round(mix_s)),
        'from_conductance_seconds': int(round(cond_s)),
        'ephemeral_seconds': int(ephemeral_s),
        'alarm': alarm,
        'reason': 'ephemeral_below_floor' if alarm else 'ok',
        'ts': time.time(),
    }


def compute() -> dict:
    try:
        rec = merge_floors(_load('memory-mixing-ttl.json'), _load('memory-conductance-ttl.json'))
        _atomic_write(_cache_dir() / 'memory-ttl-floor.json', rec)
        return rec
    except Exception as exc:
        return {'ttl_floor_seconds': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    rec = merge_floors({'tau_mix_days': 2.0}, {'ttl_floor_seconds': 1000}, ephemeral_s=86400)
    assert rec['ttl_floor_seconds'] == 2 * 86400
    assert rec['alarm'] is True
    rec2 = merge_floors({'tau_mix_days': 0.1}, {'ttl_floor_seconds': 100}, ephemeral_s=86400)
    assert rec2['alarm'] is False
    rec3 = merge_floors({}, {}, ephemeral_s=86400)
    assert rec3['ttl_floor_seconds'] == 0
    assert rec3['alarm'] is False
    print('PASS memory-ttl-floor-merge self-test')
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
