#!/usr/bin/env python3
"""pid-passivity-index.py — Khalil/Sontag passivity of the PID loop.

A system is passive if V(k+1)-V(k) <= e_k * u_k (supply rate s=e u).
Discrete check on loop-pid history. If a majority of steps violate the
dissipation inequality, the linear PID model is not a passive operator
and ISS small-gain composition is not justified.

Usage:
  python3 pid-passivity-index.py --self-test
  python3 pid-passivity-index.py
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
OUT = _hermes_root / 'cache' / 'pid-passivity-index.json'


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def passivity(history: list[dict]) -> dict:
    viol = 0
    n = 0
    supplies = []
    for i in range(len(history) - 1):
        a, b = history[i], history[i + 1]
        try:
            e = float(a.get('e', 0))
            u = float(a.get('u', 0))
            e1 = float(b.get('e', 0))
        except (TypeError, ValueError):
            continue
        v = e * e
        v1 = e1 * e1
        s = e * u
        n += 1
        supplies.append(s)
        if (v1 - v) > s + 1e-9:
            viol += 1
    ratio = (viol / n) if n else 0.0
    return {
        'n': n,
        'n_violations': viol,
        'violation_ratio': ratio,
        'mean_supply': (sum(supplies) / len(supplies)) if supplies else None,
        'alarm': n >= 3 and ratio > 0.5,
        'theorem': 'Khalil passivity / Sontag supply rate s=e u; ISS composition requires passivity',
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
    out = passivity(load_hist())
    out['ts'] = datetime.now(timezone.utc).isoformat()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    # decreasing error with positive supply: passive
    h = [{'e': 1.0, 'u': 1.0}, {'e': 0.5, 'u': 0.5}, {'e': 0.2, 'u': 0.2}]
    r = passivity(h)
    if r['alarm']:
        failures.append(f'passive series alarmed {r}')
    # error grows despite control
    h2 = [{'e': 0.1, 'u': 0.0}, {'e': 0.8, 'u': 0.0}, {'e': 1.5, 'u': 0.0}, {'e': 2.0, 'u': 0.0}]
    r2 = passivity(h2)
    if not r2['alarm']:
        failures.append(f'growing error should violate {r2}')
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
    print(json.dumps({k: out.get(k) for k in ('n', 'n_violations', 'violation_ratio', 'alarm', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
