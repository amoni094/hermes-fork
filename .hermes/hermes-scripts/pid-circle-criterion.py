#!/usr/bin/env python3
"""pid-circle-criterion.py — Sector nonlinearity of PID saturation.

Khalil circle criterion: sat(u) lies in sector [0, 1]. If a large fraction
of steps are saturated (u at clip), the linear PID+ISS analysis does not
apply and small-gain composition is heuristic only.

Usage:
  python3 pid-circle-criterion.py --self-test
  python3 pid-circle-criterion.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
OUT = _hermes_root / 'cache' / 'pid-circle-criterion.json'
U_CLIP = 1.0
SAT_FRAC = 0.5


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def sector_check(history: list[dict], clip: float = U_CLIP) -> dict:
    n = 0
    sat = 0
    in_sector = 0
    for step in history:
        try:
            u = float(step.get('u', 0))
            u_raw = float(step.get('u_raw', u))
        except (TypeError, ValueError):
            continue
        n += 1
        # sat in sector [0,1] relative to u_raw: u * (u - u_raw) <= 0 roughly
        # simpler: |u| <= |u_raw| and sign agreement, or |u|<=clip
        if abs(u) >= clip - 1e-9:
            sat += 1
        if abs(u) <= abs(u_raw) + 1e-9 or abs(u) <= clip + 1e-9:
            in_sector += 1
    frac = (sat / n) if n else 0.0
    return {
        'n': n,
        'n_saturated': sat,
        'saturation_frac': frac,
        'n_in_sector': in_sector,
        'alarm': n >= 4 and frac > SAT_FRAC,
        'theorem': 'Khalil circle criterion; sat in sector [0,1]; high sat frac => linear ISS unjustified',
    }


def load_hist() -> list[dict]:
    for p in (
        _hermes_root / 'cache' / 'loop-pid-state.json',
        _hermes_base / 'cache' / 'loop-pid-state.json',
    ):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
            return list(d.get('history') or [])
        except (OSError, json.JSONDecodeError):
            continue
    return []


def run() -> dict:
    out = sector_check(load_hist())
    out['ts'] = datetime.now(timezone.utc).isoformat()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    r = sector_check([{'u': 0.2, 'u_raw': 0.2}] * 6)
    if r['alarm']:
        failures.append('unsaturated should not alarm')
    r2 = sector_check([{'u': 1.0, 'u_raw': 3.0}] * 6)
    if not r2['alarm']:
        failures.append('all saturated should alarm')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS'}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({k: out.get(k) for k in ('n', 'n_saturated', 'saturation_frac', 'alarm', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
