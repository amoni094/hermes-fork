#!/usr/bin/env python3
"""loop-model-comparison.py — Sequential Bayesian comparison of PID error models.

Berger statistical decision theory; DeGroot optimal statistical decisions.
M0: PID-suitable — errors are AR(1) with |phi|<1 (mean-reverting).
M1: non-stationary — errors are a random walk (phi=1).

Bayes factor BF = P(data|M0)/P(data|M1) via Gaussian log-likelihoods
(BIC-penalized: M0 has extra phi). BF < 0.1 => evidence for M1 => recommend
switching from PID to MPC/rollout.

Usage:
  python3 loop-model-comparison.py --self-test
  python3 loop-model-comparison.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

OUT_PATH = _hermes_root / 'cache' / 'loop-model-comparison.json'
PHI_CLIP = 0.99
BF_M1_THRESH = 0.1
MIN_N = 4


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _gauss_ll(residuals: list[float]) -> tuple[float, float]:
    n = len(residuals)
    if n < 1:
        return float('-inf'), float('nan')
    sse = sum(r * r for r in residuals)
    sigma2 = max(sse / n, 1e-12)
    ll = -0.5 * n * math.log(2.0 * math.pi * sigma2) - 0.5 * n
    return ll, sigma2


def ar1_phi(xs: list[float]) -> float:
    num = 0.0
    den = 0.0
    for t in range(1, len(xs)):
        num += xs[t] * xs[t - 1]
        den += xs[t - 1] * xs[t - 1]
    if den <= 1e-18:
        return 0.0
    phi = num / den
    if phi > PHI_CLIP:
        return PHI_CLIP
    if phi < -PHI_CLIP:
        return -PHI_CLIP
    return phi


def loglik_m0(xs: list[float]) -> dict:
    phi = ar1_phi(xs)
    resid = [xs[t] - phi * xs[t - 1] for t in range(1, len(xs))]
    ll, sigma2 = _gauss_ll(resid)
    k = 2  # phi, sigma
    n = len(resid)
    bic = -2.0 * ll + k * math.log(max(n, 2))
    return {'ll': ll, 'sigma2': sigma2, 'phi': phi, 'k': k, 'bic': bic, 'n': n}


def loglik_m1(xs: list[float]) -> dict:
    resid = [xs[t] - xs[t - 1] for t in range(1, len(xs))]
    ll, sigma2 = _gauss_ll(resid)
    k = 1  # sigma
    n = len(resid)
    bic = -2.0 * ll + k * math.log(max(n, 2))
    return {'ll': ll, 'sigma2': sigma2, 'phi': 1.0, 'k': k, 'bic': bic, 'n': n}


def compare(xs: list[float]) -> dict:
    if len(xs) < MIN_N:
        return {
            'bayes_factor': None,
            'preferred_model': 'unknown',
            'recommendation': 'insufficient_history',
            'n': len(xs),
            'observability_ok': False,
        }
    m0 = loglik_m0(xs)
    m1 = loglik_m1(xs)
    # BIC approximation to BF_01 = P(data|M0)/P(data|M1)
    # BF_01 ≈ exp((BIC1 - BIC0)/2)
    delta = (m1['bic'] - m0['bic']) / 2.0
    # clamp for numerical safety
    delta = max(-50.0, min(50.0, delta))
    bf = math.exp(delta)
    if bf < BF_M1_THRESH:
        preferred = 'M1_random_walk'
        rec = 'switch_to_mpc_rollout'
    elif bf > (1.0 / BF_M1_THRESH):
        preferred = 'M0_ar1_pid'
        rec = 'keep_pid'
    else:
        preferred = 'inconclusive'
        rec = 'collect_more_error_samples'
    return {
        'bayes_factor': bf,
        'log_bf': delta,
        'preferred_model': preferred,
        'recommendation': rec,
        'm0': m0,
        'm1': m1,
        'n': len(xs),
        'observability_ok': True,
        'theorem': 'Berger/DeGroot Bayes factor; BIC approx; AR(1) vs random walk',
    }


def load_errors() -> tuple[list[float], dict]:
    meta = {'source': None}
    candidates = [
        _hermes_root / 'cache' / 'loop-pid-state.json',
        _hermes_base / 'cache' / 'loop-pid-state.json',
        _hermes_root / 'cache' / 'loop-pid-sessions',
    ]
    xs: list[float] = []
    for p in candidates:
        try:
            if p.is_file():
                data = json.loads(p.read_text(encoding='utf-8'))
                hist = data.get('history') or []
                for step in hist:
                    if isinstance(step, dict) and 'e' in step:
                        try:
                            xs.append(float(step['e']))
                        except (TypeError, ValueError):
                            continue
                meta['source'] = str(p)
                break
            if p.is_dir():
                for sp in sorted(p.glob('*.json')):
                    try:
                        data = json.loads(sp.read_text(encoding='utf-8'))
                    except (OSError, json.JSONDecodeError):
                        continue
                    for step in data.get('history') or []:
                        if isinstance(step, dict) and 'e' in step:
                            try:
                                xs.append(float(step['e']))
                            except (TypeError, ValueError):
                                continue
                if xs:
                    meta['source'] = str(p)
                    break
        except (OSError, json.JSONDecodeError):
            continue
    return xs, meta


def run() -> dict:
    xs, meta = load_errors()
    out = compare(xs)
    out['ts'] = datetime.now(timezone.utc).isoformat()
    out['source'] = meta.get('source')
    try:
        _atomic_write(OUT_PATH, out)
        out['output'] = str(OUT_PATH)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    # Mean-reverting AR(1): x_t = 0.4 x_{t-1}
    xs0 = [1.0]
    x = 1.0
    for i in range(30):
        x = 0.4 * x
        xs0.append(x)
    c0 = compare(xs0)
    if c0['preferred_model'] not in ('M0_ar1_pid', 'inconclusive'):
        failures.append(f'AR1 series should prefer M0/inconclusive, got {c0}')
    # Random walk
    xs1 = [0.0]
    step = 0.3
    acc = 0.0
    for i in range(30):
        acc += step if (i % 2 == 0) else step * 0.5
        xs1.append(acc)
    c1 = compare(xs1)
    if c1['bayes_factor'] is None:
        failures.append('RW should compute BF')
    # drifting series should not strongly prefer M0
    if c1.get('bayes_factor', 1) > 10 and c1['preferred_model'] == 'M0_ar1_pid':
        # strong evidence for M0 on a drift is a miss
        failures.append(f'drift series preferred M0 strongly: {c1}')
    short = compare([0.1, 0.2])
    if short['preferred_model'] != 'unknown':
        failures.append('short series should be unknown')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}, default=str))
        return 1
    print(json.dumps({
        'self_test': 'PASS',
        'ar1_pref': c0['preferred_model'],
        'ar1_bf': c0['bayes_factor'],
        'rw_pref': c1['preferred_model'],
        'rw_bf': c1['bayes_factor'],
    }))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({
        'bayes_factor': out.get('bayes_factor'),
        'preferred_model': out.get('preferred_model'),
        'recommendation': out.get('recommendation'),
        'n': out.get('n'),
        'output': out.get('output'),
    }))
    if out.get('recommendation') == 'switch_to_mpc_rollout':
        print('ALARM: PID model misspecified; prefer MPC/rollout')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
