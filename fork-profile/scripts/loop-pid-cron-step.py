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
U_MAX, U_MIN = 1.0, 0.0  # must match loop-pid.py (lyapunov-check uses these)
KAW = 0.5               # anti-windup back-calculation gain (must match loop-pid.py)
SETPOINT = 1.0        # default; overridden by majority setpoint in existing history
HISTORY_CAP = 500
U_CLIP = U_MAX         # alias for clip helper
INT_CLIP = 20.0        # generous; anti-windup controls integrator instead


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


def _majority_setpoint(history: list, default: float = SETPOINT) -> float:
    """Return the most common setpoint in the history, or default if absent."""
    from collections import Counter
    counts = Counter(
        h.get('setpoint') for h in history
        if isinstance(h, dict) and h.get('setpoint') is not None
    )
    if not counts:
        return default
    return counts.most_common(1)[0][0]


def step(state_path: Path, setpoint=None, rng=None) -> dict:  # setpoint: float|None, rng: Random|None
    rng = rng or random
    state = _load_state(state_path)
    history = state.get('history') or []
    # Inherit majority setpoint from existing history to avoid setpoint mixing
    effective_setpoint = setpoint if setpoint is not None else _majority_setpoint(history, SETPOINT)
    # Load last plant state: e is stored; recover y = setpoint - e.
    last_e = 0.9
    if history and isinstance(history[-1], dict) and history[-1].get('e') is not None:
        try:
            last_e = float(history[-1]['e'])
        except (TypeError, ValueError):
            pass
    last_measurement = history[-1].get('measurement', effective_setpoint - last_e) if history else effective_setpoint - last_e
    try:
        last_y = float(last_measurement)
    except (TypeError, ValueError):
        last_y = effective_setpoint - last_e

    # Compute PID output for the current error.
    e = effective_setpoint - last_y
    prev_err = state.get('prev_error')
    try:
        prev_f = float(prev_err) if prev_err is not None else e
    except (TypeError, ValueError):
        prev_f = e
    deriv = e - prev_f
    integrator = float(state.get('integrator') or 0.0)
    u_raw = KP * e + KI * integrator + KD * deriv
    u = _clip(u_raw, U_MIN, U_CLIP)
    windup = abs(u_raw - u) > 1e-9
    # Anti-windup matches loop-pid.py (KAW back-calculation)
    if windup:
        integrator += KAW * (u - u_raw) / KI if KI > 0 else 0.0
    else:
        integrator += e
    integrator = _clip(integrator, -INT_CLIP, INT_CLIP)
    # Plant update: y[k+1] = 0.5*y[k] + 0.5*u[k] + noise (DC gain=1, stable)
    y_next = 0.5 * last_y + 0.5 * u + rng.gauss(0.0, 0.003)
    if not math.isfinite(y_next):
        y_next = last_y
    measurement = y_next
    setpoint = effective_setpoint  # for record
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
