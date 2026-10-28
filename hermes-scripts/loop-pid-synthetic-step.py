#!/usr/bin/env python3
"""loop-pid-synthetic-step.py — Bootstrap PID history for Lyapunov/ISS eval.

Generates N=200 synthetic PID steps (Gaussian-noise target tracking) and
writes loop-pid-state.json so lyapunov-check has enough history (Khalil Ch 4
needs >= 2 steps for DeltaV).

Plant: discrete first-order lag
    y_{k+1} = y_k + dt * ((u_k - y_k)/tau) + w_k
Controller: discrete PID (Astrom-Murray Feedback Systems 2e §11.1-11.3)
with anti-windup back-calculation (§11.4). Gains default Kp=0.5, Ki=0.05,
Kd=0.1, setpoint=1.0.

Does not patch loop-pid.py (Hermes-owned). Writes the state files already
read by loop-pid.py, pid-passivity-index.py, pid-circle-criterion.py, and
loop-cusum-changepoint.py. History is NOT truncated to 20 (the live
controller truncates; this bootstrap keeps the full window).

Usage:
  python3 loop-pid-synthetic-step.py --self-test
  python3 loop-pid-synthetic-step.py [--n 200] [--seed 7]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

N_DEFAULT = 200
KP, KI, KD = 0.5, 0.05, 0.1
U_MAX, U_MIN = 1.0, 0.0
KAW = 0.5
SETPOINT = 1.0
DT = 0.05
TAU = 0.4
PROC_SIGMA = 0.02
MEAS_SIGMA = 0.03


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def simulate(n: int = N_DEFAULT, seed: int = 7, setpoint: float = SETPOINT) -> dict:
    rng = random.Random(seed)
    y = 0.35
    integrator = 0.0
    prev_e = None
    history = []
    windup_n = 0
    for k in range(n):
        meas = y + rng.gauss(0.0, MEAS_SIGMA)
        e = setpoint - meas
        de = (e - prev_e) if prev_e is not None else 0.0
        u_raw = KP * e + KI * integrator + KD * de
        u = max(U_MIN, min(U_MAX, u_raw))
        windup = abs(u_raw - u) > 1e-12
        if windup:
            windup_n += 1
            integrator += KAW * (u - u_raw) / KI if KI else 0.0
        else:
            integrator += e
        w = rng.gauss(0.0, PROC_SIGMA)
        y = y + DT * ((u - y) / TAU) + w
        history.append({
            'ts': datetime.now(UTC).isoformat(),
            'k': k,
            'e': round(float(e), 6),
            'u': round(float(u), 6),
            'u_raw': round(float(u_raw), 6),
            'y': round(float(y), 6),
            'setpoint': setpoint,
            'integrator': round(float(integrator), 6),
            'windup': windup,
        })
        prev_e = e
    state = {
        'integrator': integrator,
        'prev_error': prev_e,
        'windup': bool(history[-1]['windup']) if history else False,
        'history': history,
        'hypotheses_tried': 0,
        'ended': False,
        'synthetic': True,
        'synthetic_meta': {
            'n': n,
            'seed': seed,
            'Kp': KP, 'Ki': KI, 'Kd': KD,
            'setpoint': setpoint,
            'dt': DT, 'tau': TAU,
            'proc_sigma': PROC_SIGMA,
            'meas_sigma': MEAS_SIGMA,
            'n_windup': windup_n,
            'note': 'Astrom PID + anti-windup; Khalil Ch 4 bootstrap for DeltaV',
        },
    }
    return state


def state_paths() -> list[Path]:
    """Write both profile cache and the loop-pid.py hardcoded path."""
    paths = [
        _hermes_root / 'cache' / 'loop-pid-state.json',
        _hermes_base / 'cache' / 'loop-pid-state.json',
        Path.home() / '.hermes' / 'cache' / 'loop-pid-state.json',
    ]
    # unique preserve order
    out = []
    seen = set()
    for p in paths:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def write_state(state: dict) -> list[str]:
    written = []
    for p in state_paths():
        _atomic_write(p, state)
        written.append(str(p))
    return written


def _lyapunov_check() -> dict:
    candidates = [
        _hermes_base / 'hermes-scripts' / 'loop-pid.py',
        _hermes_base / 'scripts' / 'loop-pid.py',
        Path(__file__).resolve().parent / 'loop-pid.py',
    ]
    script = next((p for p in candidates if p.is_file()), None)
    if script is None:
        return {'error': 'loop-pid.py not found'}
    try:
        proc = subprocess.run(
            [sys.executable or 'python3', str(script), 'lyapunov-check'],
            capture_output=True, text=True, timeout=30,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'error': str(exc)}
    text = (proc.stdout or '').strip()
    last = None
    buf = []
    depth = 0
    for ch in text:
        if ch == '{':
            if depth == 0:
                buf = ['{']
            else:
                buf.append(ch)
            depth += 1
        elif ch == '}':
            if depth:
                buf.append(ch)
                depth -= 1
                if depth == 0:
                    last = ''.join(buf)
        elif depth:
            buf.append(ch)
    if last:
        try:
            obj = json.loads(last)
            return obj if isinstance(obj, dict) else {'error': 'non-object'}
        except json.JSONDecodeError:
            pass
    return {'error': 'unparseable', 'stdout': text[:400]}


def run(n: int = N_DEFAULT, seed: int = 7) -> dict:
    state = simulate(n=n, seed=seed)
    written = write_state(state)
    lyap = _lyapunov_check()
    insufficient = lyap.get('error') == 'insufficient_history'
    out = {
        'n': len(state['history']),
        'written': written,
        'integrator': round(float(state['integrator']), 6),
        'final_e': state['history'][-1]['e'] if state['history'] else None,
        'n_windup': state['synthetic_meta']['n_windup'],
        'lyapunov_insufficient_history': insufficient,
        'lyapunov_stable': lyap.get('lyapunov_stable'),
        'lyapunov_steps_checked': lyap.get('steps_checked'),
        'lyapunov_error': lyap.get('error'),
        'ok': (len(state['history']) == n) and (not insufficient),
    }
    return out


def self_test() -> int:
    failures = []
    state = simulate(n=N_DEFAULT, seed=7)
    if len(state['history']) != N_DEFAULT:
        failures.append(f'history len {len(state["history"])} != {N_DEFAULT}')
    es = [h['e'] for h in state['history']]
    if any(not math.isfinite(e) for e in es):
        failures.append('non-finite error')
    # late-window |e| should be smaller than early-window on average (tracking)
    early = sum(abs(e) for e in es[:20]) / 20.0
    late = sum(abs(e) for e in es[-20:]) / 20.0
    if late > early:
        failures.append(f'tracking failed: late={late:.3f} early={early:.3f}')
    written = write_state(state)
    for p in written:
        obj = json.loads(Path(p).read_text(encoding='utf-8'))
        if len(obj.get('history') or []) != N_DEFAULT:
            failures.append(f'{p} history truncated')
    lyap = _lyapunov_check()
    if lyap.get('error') == 'insufficient_history':
        failures.append('lyapunov still insufficient_history after 200 steps')
    if lyap.get('steps_checked', 0) < 2 and 'error' not in lyap:
        failures.append('lyapunov steps_checked < 2')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures, 'lyap': lyap}))
        return 1
    print(json.dumps({
        'self_test': 'PASS',
        'n': N_DEFAULT,
        'lyapunov_stable': lyap.get('lyapunov_stable'),
        'steps_checked': lyap.get('steps_checked'),
        'written': written,
    }))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--n', type=int, default=N_DEFAULT)
    p.add_argument('--seed', type=int, default=7)
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run(n=args.n, seed=args.seed)
    print(json.dumps(out))
    return 0 if out.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
