#!/usr/bin/env python3
"""loop-cusum-changepoint.py — Page CUSUM on PID error (Wald/Page).

Detects a mean shift in loop-pid error that would invalidate fixed PID gains.
Two-sided CUSUM: S+ and S- with allowance k and threshold h.
Alarm => recommend retune / switch to MPC (pairs with loop-model-comparison).

Usage:
  python3 loop-cusum-changepoint.py --self-test
  python3 loop-cusum-changepoint.py
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

OUT_PATH = _hermes_root / 'cache' / 'loop-cusum-changepoint.json'
K_DEFAULT = 0.25
H_DEFAULT = 4.0


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def cusum(xs: list[float], mu0: float = 0.0, k: float = K_DEFAULT, h: float = H_DEFAULT) -> dict:
    sp = 0.0
    sm = 0.0
    max_sp = 0.0
    max_sm = 0.0
    alarm_at = None
    for i, x in enumerate(xs):
        sp = max(0.0, sp + (x - mu0) - k)
        sm = max(0.0, sm - (x - mu0) - k)
        if sp > max_sp:
            max_sp = sp
        if sm > max_sm:
            max_sm = sm
        if alarm_at is None and (sp > h or sm > h):
            alarm_at = i
    return {
        'n': len(xs),
        'mu0': mu0,
        'k': k,
        'h': h,
        'S_plus': sp,
        'S_minus': sm,
        'max_S_plus': max_sp,
        'max_S_minus': max_sm,
        'alarm': alarm_at is not None,
        'alarm_index': alarm_at,
        'theorem': 'Page CUSUM; Wald sequential analysis',
    }


def load_errors() -> list[float]:
    xs: list[float] = []
    for p in (
        _hermes_root / 'cache' / 'loop-pid-state.json',
        _hermes_base / 'cache' / 'loop-pid-state.json',
    ):
        try:
            if not p.is_file():
                continue
            data = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        for step in data.get('history') or []:
            if isinstance(step, dict) and 'e' in step:
                try:
                    xs.append(float(step['e']))
                except (TypeError, ValueError):
                    continue
        if xs:
            return xs
    return xs


def run() -> dict:
    xs = load_errors()
    # ADV21-018: load frozen baseline from prior window to avoid lookahead bias
    baseline_path = _hermes_root / 'cache' / 'loop-cusum-baseline.json'
    mu0 = 0.0
    try:
        bl = json.loads(baseline_path.read_text())
        mu0 = float(bl.get('mu0', 0.0))
    except Exception:
        # First run: estimate from full series AND persist for next run
        mu0 = (sum(xs) / len(xs)) if xs else 0.0
        try:
            tmp_bl = baseline_path.with_suffix('.tmp')
            tmp_bl.write_text(json.dumps({'mu0': mu0, 'n': len(xs)}, ensure_ascii=False))
            os.replace(tmp_bl, baseline_path)
        except Exception:
            pass
    out = cusum(xs, mu0=mu0)
    out['ts'] = datetime.now(timezone.utc).isoformat()
    out['recommendation'] = 'retune_pid_or_mpc' if out['alarm'] else 'pid_gains_stable'
    try:
        _atomic_write(OUT_PATH, out)
        out['output'] = str(OUT_PATH)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    # in-control noise around 0
    ok = cusum([0.05, -0.04, 0.03, -0.02, 0.01] * 4, mu0=0.0, k=0.25, h=4.0)
    if ok['alarm']:
        failures.append('in-control should not alarm')
    # step change to 2.0
    xs = [0.0] * 8 + [2.0] * 12
    bad = cusum(xs, mu0=0.0, k=0.25, h=4.0)
    if not bad['alarm']:
        failures.append('step change should alarm')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS', 'alarm_index': bad['alarm_index']}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({k: out.get(k) for k in (
        'n', 'alarm', 'alarm_index', 'recommendation', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
