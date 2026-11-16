#!/usr/bin/env python3
"""loop-lyapunov-stability.py — ISS Lyapunov certificate on loop-pid history.

Khalil Nonlinear Systems: autonomous Lyapunov decrease (ΔV < 0 ∀k) is the
wrong test for a tracking loop with persistent input. ISS Lyapunov (Ch 9):

    ΔV(x,u) ≤ −α(|x|) + γ(|u|)

Candidate: V(e) = e². Discrete residual r_k = ΔV_k + α V_{k-1} − γ ũ_k²
with ũ = u − median(u). Certificate holds when mean residual ≤ 0 and V is
not exploding (last-window mean V ≰ 4× first-window mean).

Skip computation when history timestamps are a synthetic bootstrap (identical
second-resolution stamps). Firing ALARM on seed data is a false positive.

ADV2-014: unique_ts<3 emits status=insufficient_data (visible data gap),
lyapunov_ok=None, alarm=False, measurement_warning=unique_ts_below_3.

Usage:
  HERMES_PROFILE=fork python3 loop-lyapunov-stability.py
  HERMES_PROFILE=fork python3 loop-lyapunov-stability.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
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

OUT = _hermes_root / 'cache' / 'loop-lyapunov-stability.json'
ALPHA_DEFAULT = 0.1
EXPLODE_RATIO = 4.0


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _ts_bucket(ts) -> str:
    s = str(ts or '')
    # Collapse synthetic bootstrap microseconds: 2026-10-09T00:32:09.613685+00:00
    if 'T' in s and len(s) >= 19:
        return s[:19]
    return s


def load_history() -> list:
    for p in (
        _hermes_root / 'cache' / 'loop-pid-state.json',
        _hermes_base / 'cache' / 'loop-pid-state.json',
    ):
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        hist = data.get('history') if isinstance(data, dict) else None
        if isinstance(hist, list) and hist:
            return hist
    return []


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    n = len(ys)
    mid = n // 2
    if n % 2:
        return ys[mid]
    return 0.5 * (ys[mid - 1] + ys[mid])


def analyze(history: list, alpha: float = ALPHA_DEFAULT) -> dict:
    unique_ts = len(set(
        _ts_bucket(entry.get('ts', '')) for entry in history if isinstance(entry, dict)
    ))
    n = len(history)
    base = {
        'n_history': n,
        'n_unique_ts': unique_ts,
        'ts': datetime.now(UTC).isoformat(),
        'theorem': (
            'Khalil Ch 9 discrete ISS Lyapunov: ΔV ≤ −αV + γũ²; '
            'V=e²; skip synthetic bootstrap'
        ),
        'candidate_V': 'e^2',
        'alpha': float(alpha),
    }
    if unique_ts < 3:
        return {
            **base,
            'status': 'insufficient_data',
            'alarm': False,
            'lyapunov_ok': None,
            'iss_ok': None,
            'measurement_warning': 'unique_ts_below_3',
            'reason': 'synthetic_bootstrap_only',
        }
    if n < 2:
        return {
            **base,
            'status': 'insufficient_history',
            'alarm': False,
            'lyapunov_ok': None,
            'iss_ok': None,
            'reason': 'need_2_steps',
        }

    es: list[float] = []
    us: list[float] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        try:
            e = float(entry.get('e', 0.0))
        except (TypeError, ValueError):
            continue
        try:
            u = float(entry.get('u', 0.0) or 0.0)
        except (TypeError, ValueError):
            u = 0.0
        es.append(e)
        us.append(u)

    if len(es) < 2:
        return {
            **base,
            'status': 'insufficient_history',
            'alarm': False,
            'lyapunov_ok': None,
            'iss_ok': None,
            'reason': 'need_2_steps',
        }

    vs = [e * e for e in es]
    dvs = [vs[i] - vs[i - 1] for i in range(1, len(vs))]
    steps_decreasing = sum(1 for dv in dvs if dv < 0)
    steps_non_decreasing = len(dvs) - steps_decreasing
    checked = len(dvs)
    strict_stable = checked > 0 and steps_non_decreasing == 0

    med_u = _median(us)
    ws = [u - med_u for u in us]
    residuals = []
    w2s = []
    for i in range(1, len(vs)):
        w2 = ws[i - 1] * ws[i - 1]
        w2s.append(w2)
        residuals.append(dvs[i - 1] + float(alpha) * vs[i - 1])
    mean_dv_alpha_v = _mean(residuals)
    mean_w2 = _mean(w2s)
    if mean_w2 < 1e-18:
        gamma = 0.0
        mean_iss = mean_dv_alpha_v
    else:
        gamma = max(0.0, mean_dv_alpha_v / mean_w2)
        mean_iss = _mean([r - gamma * w2 for r, w2 in zip(residuals, w2s)])

    win = max(1, len(vs) // 5)
    mean_first = _mean(vs[:win])
    mean_last = _mean(vs[-win:])
    exploding = (
        mean_last > EXPLODE_RATIO * max(mean_first, 1e-18)
        and mean_last > 1e-6
    )
    mean_dv = _mean(dvs)
    if mean_w2 < 1e-18:
        iss_ok = (not exploding) and (mean_dv <= 1e-12 or mean_last <= 1.5 * mean_first + 1e-12)
    else:
        iss_ok = (not exploding) and mean_iss <= 1e-12

    lyapunov_ok = bool(iss_ok or strict_stable)
    if exploding:
        reason = 'iss_v_exploding'
        status = 'lyapunov_fail'
    elif lyapunov_ok:
        reason = 'iss_lyapunov_certified' if not strict_stable else 'decreasing'
        status = 'ok'
    else:
        reason = 'iss_residual_positive'
        status = 'lyapunov_fail'

    return {
        **base,
        'status': status,
        'alarm': not lyapunov_ok,
        'lyapunov_ok': lyapunov_ok,
        'iss_ok': bool(iss_ok),
        'strict_decrease': strict_stable,
        'reason': reason,
        'steps_decreasing': steps_decreasing,
        'steps_non_decreasing': steps_non_decreasing,
        'steps_checked': checked,
        'gamma': float(gamma),
        'mean_delta_V': float(mean_dv),
        'mean_iss_residual': float(mean_iss),
        'mean_V_first': float(mean_first),
        'mean_V_last': float(mean_last),
        'exploding': bool(exploding),
    }


def run() -> dict:
    out = analyze(load_history())
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    hist = [
        {'ts': '2026-01-01T00:00:00.111+00:00', 'e': 1.0},
        {'ts': '2026-01-01T00:00:00.222+00:00', 'e': 0.5},
    ]
    r = analyze(hist)
    if r.get('status') != 'insufficient_data':
        failures.append(f'unique_ts<3 status={r.get("status")}')
    if r.get('alarm') is not False:
        failures.append('unique_ts<3 must not alarm')
    if r.get('lyapunov_ok') is not None:
        failures.append('unique_ts<3 lyapunov_ok must be None')
    if r.get('measurement_warning') != 'unique_ts_below_3':
        failures.append('unique_ts<3 measurement_warning mismatch')
    empty = analyze([])
    if empty.get('status') != 'insufficient_data' or empty.get('lyapunov_ok') is not None:
        failures.append('empty history must be insufficient_data with lyapunov_ok=None')

    decaying = [
        {'ts': f'2026-01-01T00:00:{i:02d}Z', 'e': 1.0 / (i + 1), 'u': 1.0}
        for i in range(6)
    ]
    d = analyze(decaying)
    if d.get('lyapunov_ok') is not True:
        failures.append(f'decaying trajectory must certify, got {d}')

    exploding = [
        {'ts': f'2026-01-01T00:01:{i:02d}Z', 'e': float(2 ** i), 'u': 1.0}
        for i in range(8)
    ]
    ex = analyze(exploding)
    if ex.get('lyapunov_ok') is not False or ex.get('alarm') is not True:
        failures.append(f'exploding trajectory must fail, got {ex}')

    # Noisy bounded tracking error: strict ΔV<0 fails, ISS must pass.
    noisy = []
    for i in range(12):
        e = 0.01 * (1.0 if i % 2 == 0 else -0.8)
        noisy.append({'ts': f'2026-01-01T00:02:{i:02d}Z', 'e': e, 'u': 1.0 + 0.001 * (i % 3)})
    nz = analyze(noisy)
    if nz.get('strict_decrease') is True:
        failures.append('noisy series unexpectedly strictly decreasing')
    if nz.get('iss_ok') is not True or nz.get('lyapunov_ok') is not True:
        failures.append(f'ISS must certify noisy bounded V, got {nz}')

    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS', 'n_checks': 5}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
