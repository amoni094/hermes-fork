#!/usr/bin/env python3
"""Cron stepper for the session-stability PID loop.

Reads loop-pid-state.json, simulates a noisy approach to setpoint, applies
one PID step, appends history (cap 500), writes atomically.

Usage:
  python3 loop-pid-cron-step.py
  python3 loop-pid-cron-step.py --state PATH
  python3 loop-pid-cron-step.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import tempfile
import time
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

DEFAULT_STATE = _hermes_root / 'cache' / 'loop-pid-state.json'
KP, KI, KD = 1.0, 0.15, 0.4
SETPOINT = 0.0
HISTORY_CAP = 500
U_CLIP = 2.0
INT_CLIP = 5.0


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {'integrator': 0.0, 'prev_error': None, 'history': []}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'integrator': 0.0, 'prev_error': None, 'history': []}
    if not isinstance(data, dict):
        return {'integrator': 0.0, 'prev_error': None, 'history': []}
    data.setdefault('integrator', 0.0)
    data.setdefault('prev_error', None)
    data.setdefault('history', [])
    if not isinstance(data['history'], list):
        data['history'] = []
    return data


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def step(state_path: Path, setpoint: float = SETPOINT, rng: random.Random | None = None) -> dict:
    rng = rng or random
    state = _load_state(state_path)
    history = state.get('history') or []
    last_error = 0.1
    if history and isinstance(history[-1], dict) and history[-1].get('e') is not None:
        try:
            last_error = float(history[-1]['e'])
        except (TypeError, ValueError):
            last_error = 0.1
    measurement = setpoint - (setpoint - last_error) * 0.95 + rng.gauss(0.0, 0.05)
    if not math.isfinite(measurement):
        measurement = last_error
    e = measurement  # simulated error approaching setpoint
    integrator = float(state.get('integrator') or 0.0) + e
    integrator = _clip(integrator, -INT_CLIP, INT_CLIP)
    prev = state.get('prev_error')
    try:
        prev_f = float(prev) if prev is not None else e
    except (TypeError, ValueError):
        prev_f = e
    deriv = e - prev_f
    u = KP * e + KI * integrator + KD * deriv
    u = _clip(u, -U_CLIP, U_CLIP)
    rec = {
        'ts': time.time(),
        'e': e,
        'u': u,
        'integrator': integrator,
        'measurement': measurement,
        'setpoint': setpoint,
    }
    history = list(history) + [rec]
    if len(history) > HISTORY_CAP:
        history = history[-HISTORY_CAP:]
    out = {
        'integrator': integrator,
        'prev_error': e,
        'history': history,
        'last_u': u,
        'last_e': e,
    }
    _atomic_write_json(state_path, out)
    return rec | {'n_history': len(history)}


def self_test() -> dict:
    failures = []
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'loop-pid-state.json'
        rng = random.Random(0)
        for _ in range(10):
            step(p, rng=rng)
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            return {'self_test': 'FAIL', 'n_failures': 1, 'failures': [str(e)]}
        if len(data.get('history') or []) != 10:
            failures.append(f'len(history)={len(data.get("history") or [])}')
        # missing file starts empty
        p2 = Path(td) / 'missing.json'
        rec = step(p2, rng=random.Random(1))
        if rec.get('n_history') != 1:
            failures.append(f'missing-start: {rec}')
        # malformed JSON
        p3 = Path(td) / 'bad.json'
        p3.write_text('{not json', encoding='utf-8')
        rec3 = step(p3, rng=random.Random(2))
        if rec3.get('n_history') != 1:
            failures.append(f'malformed: {rec3}')
        # history cap
        p4 = Path(td) / 'cap.json'
        _atomic_write_json(p4, {
            'integrator': 0.0,
            'prev_error': 0.1,
            'history': [{'e': 0.1, 'u': 0.0}] * 499,
        })
        rec4 = step(p4, rng=random.Random(3))
        data4 = json.loads(p4.read_text())
        if len(data4['history']) != 500:
            failures.append(f'cap: {len(data4["history"])} rec={rec4}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', type=str, default=str(DEFAULT_STATE))
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r))
        return 0 if r['self_test'] == 'PASS' else 1
    rec = step(Path(args.state))
    print(json.dumps(rec))
    return 0


if __name__ == '__main__':
    sys.exit(main())
