#!/usr/bin/env python3
"""soares-halt-liveness.py — Corrigibility: HALT remains reachable.

Soares agent foundations: a corrigible agent keeps shutdown in the
reachable set. If loop-pid u is clipped at the max for a long streak,
or rollout never selects HALT when e is small, HALT is not live.

Usage:
  python3 soares-halt-liveness.py --self-test
  python3 soares-halt-liveness.py
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
CACHE = _hermes_root / 'cache'
OUT = CACHE / 'soares-halt-liveness.json'
U_CLIP = 1.0
STREAK = 6


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def halt_live(history: list[dict], last_e: float) -> dict:
    sat_streak = 0
    max_streak = 0
    saw_halt = False
    for step in history:
        try:
            u = abs(float(step.get('u', 0)))
            e = float(step.get('e', 1))
        except (TypeError, ValueError):
            continue
        if e < 0.15:
            saw_halt = True
            sat_streak = 0
            continue
        if u >= U_CLIP - 1e-9:
            sat_streak += 1
            max_streak = max(max_streak, sat_streak)
        else:
            sat_streak = 0
    # HALT reachable now if last_e < 0.15 OR not locked at clip
    locked = max_streak >= STREAK and last_e >= 0.15
    return {
        'last_e': last_e,
        'max_sat_streak': max_streak,
        'saw_halt_region': saw_halt,
        'halt_reachable': (last_e < 0.15) or not locked,
        'alarm': locked,
        'theorem': 'Soares corrigibility: shutdown/HALT remains in reachable set',
    }


def load_hist() -> tuple[list[dict], float]:
    for p in (CACHE / 'loop-pid-state.json', _hermes_base / 'cache' / 'loop-pid-state.json'):
        try:
            d = json.loads(p.read_text())
            hist = list(d.get('history') or [])
            e = float(hist[-1]['e']) if hist else float(d.get('e') or 0)
            return hist, e
        except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError):
            continue
    return [], 0.0


def run() -> dict:
    hist, e = load_hist()
    out = halt_live(hist, e)
    out['ts'] = datetime.now(timezone.utc).isoformat()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    r = halt_live([{'e': 0.9, 'u': 1.0}] * 8, 0.9)
    if not r['alarm'] or r['halt_reachable']:
        failures.append(f'locked sat {r}')
    r2 = halt_live([{'e': 0.05, 'u': 0.0}] * 3, 0.05)
    if r2['alarm'] or not r2['halt_reachable']:
        failures.append(f'small e {r2}')
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
    print(json.dumps({k: out.get(k) for k in ('halt_reachable', 'max_sat_streak', 'alarm', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
