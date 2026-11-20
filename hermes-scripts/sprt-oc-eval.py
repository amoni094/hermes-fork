#!/usr/bin/env python3
"""sprt-oc-eval.py — Monte Carlo OC/ASN calibration for the hermes-fork SPRT gate.

Simulates the Wald SPRT (A = log(19), B = log(1/19), N_max = 200) under a
range of true means mu_0 and AR(1) autocorrelation rho values, and reports:
  - empirical alpha (P(reject H0 | H0 true))
  - empirical beta  (P(accept H0 | H1 true))
  - ASN             (average sample number)
  - P(truncate)     (hit N_max before crossing a boundary)
  - P(error_rate veto triggered)   (parallel hard veto at error_rate >= 0.10)

Motivation: the current SPRT uses A = log(19) targeting alpha=beta=0.05.
Under AR(1) data the effective sample size shrinks; peeking at nightly windows
causes alpha overshoot (Fischer-Ramdas arXiv:2410.16076).

Usage:
  python3 sprt-oc-eval.py                    # emit full calibration JSON
  python3 sprt-oc-eval.py --self-test        # run internal unit tests
  python3 sprt-oc-eval.py --mu 3.5 --rho 0.0 --n-sims 5000

Writes: cache/sprt-oc-calibration.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)
CACHE = _hermes_root / 'cache'

# SPRT parameters matching hermes-fork governance
MU_0 = 3.5        # H0 mean (normal operation; error probability baseline)
MU_1 = 4.0        # H1 mean (degraded; tunable)
SIGMA = 1.0       # assumed observation noise (normalised)
A = math.log(19)  # upper boundary: log((1-beta)/alpha) with alpha=beta=0.05
B = -A            # lower boundary: log(beta/(1-alpha))
N_MAX = 200       # truncation (fail-closed on timeout)
ERROR_RATE_VETO = 0.10   # hard parallel veto threshold


def _ar1_sample(n: int, mu: float, sigma: float, rho: float, seed: int = 0) -> list[float]:
    """Generate n AR(1) samples: X_t = mu + rho*(X_{t-1}-mu) + eps_t."""
    rng = random.Random(seed)
    innov_sigma = sigma * math.sqrt(max(0.0, 1.0 - rho ** 2))
    x_prev = mu
    samples = []
    for _ in range(n):
        eps = rng.gauss(0.0, innov_sigma)
        x = mu + rho * (x_prev - mu) + eps
        samples.append(x)
        x_prev = x
    return samples


def _sprt_run(
    mu_true: float,
    mu_0: float,
    mu_1: float,
    sigma: float,
    a: float,
    b: float,
    n_max: int,
    rho: float,
    seed: int,
) -> dict:
    """Single SPRT trajectory. Returns dict with outcome and sample count.

    Observations x_t are Gaussian (AR(1)) representing the monitored metric
    (e.g., normalised error count or loop residual). The error_rate veto is a
    SEPARATE parallel mechanism modelled as a Bernoulli process with the true
    error probability p_err (here approximated as mu_true / 10 for the scalar
    metric). Veto fires when running proportion >= ERROR_RATE_VETO.
    """
    samples = _ar1_sample(n_max + 1, mu_true, sigma, rho, seed)
    # Bernoulli error events independent of the metric (p_err ~ mu_true/20 for illustration)
    rng_err = random.Random(seed + 99999)
    p_err = min(0.5, max(0.0, (mu_true - mu_0) / (mu_0 * 4)))  # small probability, grows with mu
    llr = 0.0
    n_errors = 0
    for t, x in enumerate(samples, start=1):
        # log-likelihood ratio under Gaussian H1 vs H0:
        # log(f1(x)/f0(x)) = x*(mu_1-mu_0)/sigma^2 - (mu_1^2-mu_0^2)/(2*sigma^2)
        # Drifts +KL(P1||P0) = (mu_1-mu_0)^2/(2*sigma^2) per step under H1.
        llr += x * (mu_1 - mu_0) / (sigma ** 2) - (mu_1 ** 2 - mu_0 ** 2) / (2 * sigma ** 2)
        # Separate Bernoulli error events for the hard veto simulation
        if rng_err.random() < p_err:
            n_errors += 1
        # hard error_rate veto: if running proportion >= ERROR_RATE_VETO, force reject H0
        if t > 10 and (n_errors / t) >= ERROR_RATE_VETO:
            return {'outcome': 'veto_reject', 'n': t, 'llr': llr}
        if llr >= a:
            return {'outcome': 'reject_h0', 'n': t, 'llr': llr}
        if llr <= b:
            return {'outcome': 'accept_h0', 'n': t, 'llr': llr}
    # truncation: fail-closed = treat as reject (alarm)
    return {'outcome': 'truncate_reject', 'n': n_max, 'llr': llr}


def simulate(
    mu_true: float,
    n_sims: int,
    mu_0: float = MU_0,
    mu_1: float = MU_1,
    sigma: float = SIGMA,
    a: float = A,
    b: float = B,
    n_max: int = N_MAX,
    rho: float = 0.0,
) -> dict:
    """Run n_sims Monte Carlo trajectories and compute OC/ASN table."""
    outcomes = {'reject_h0': 0, 'accept_h0': 0, 'truncate_reject': 0, 'veto_reject': 0}
    total_n = 0
    for seed in range(n_sims):
        r = _sprt_run(mu_true, mu_0, mu_1, sigma, a, b, n_max, rho, seed)
        outcomes[r['outcome']] = outcomes.get(r['outcome'], 0) + 1
        total_n += r['n']

    n_alarm = outcomes['reject_h0'] + outcomes['truncate_reject'] + outcomes.get('veto_reject', 0)
    n_accept = outcomes['accept_h0']
    p_alarm = n_alarm / n_sims
    p_accept = n_accept / n_sims
    asn = total_n / n_sims
    p_truncate = outcomes['truncate_reject'] / n_sims
    p_veto = outcomes.get('veto_reject', 0) / n_sims

    # Under H0 true: alpha = P(alarm); Under H1 true: beta = P(accept)
    is_h0 = (abs(mu_true - mu_0) < 1e-9)
    is_h1 = (abs(mu_true - mu_1) < 1e-9)
    return {
        'mu_true': mu_true,
        'rho': rho,
        'n_sims': n_sims,
        'p_alarm': round(p_alarm, 5),
        'p_accept': round(p_accept, 5),
        'asn': round(asn, 2),
        'p_truncate': round(p_truncate, 5),
        'p_veto': round(p_veto, 5),
        'empirical_alpha': round(p_alarm, 5) if is_h0 else None,
        'empirical_beta': round(p_accept, 5) if is_h1 else None,
        'outcomes': outcomes,
        'alarm': (
            (is_h0 and p_alarm > 0.10) or      # alpha overshoot
            (is_h1 and p_accept > 0.10) or      # beta overshoot
            (p_truncate > 0.20)                 # too many truncations
        ),
    }


def run_full_calibration(n_sims: int = 2000) -> dict:
    """Standard calibration grid: mu in {3.0, 3.5, 4.0} x rho in {0.0, 0.3, 0.6}."""
    results = []
    mus = [MU_0 - 0.5, MU_0, MU_1, MU_1 + 0.5]
    rhos = [0.0, 0.3, 0.6]
    for mu in mus:
        for rho in rhos:
            r = simulate(mu, n_sims=n_sims, rho=rho)
            results.append(r)

    alarm_conditions = [r for r in results if r.get('alarm')]
    recommendations = []
    # Check alpha at H0
    h0_results = [r for r in results if abs(r['mu_true'] - MU_0) < 1e-9 and r['rho'] == 0.0]
    if h0_results:
        alpha = h0_results[0]['empirical_alpha']
        if alpha is not None and alpha > 0.10:
            recommendations.append(
                f'CRITICAL: empirical alpha={alpha:.3f} > 0.10 at H0, rho=0. '
                'Switch SPRT to mSPRT/always-valid (Johari arXiv:1512.04922).'
            )
        elif alpha is not None and alpha > 0.07:
            recommendations.append(
                f'WARNING: empirical alpha={alpha:.3f} > 0.07. '
                'Peeking bias present. Consider mSPRT or reduce peek frequency.'
            )

    high_rho = [r for r in results if r['rho'] >= 0.6 and abs(r['mu_true'] - MU_0) < 1e-9]
    if high_rho and high_rho[0].get('empirical_alpha', 0) > 0.15:
        recommendations.append(
            'CRITICAL: AR(1) rho=0.6 causes severe alpha overshoot. '
            'Loop observations are likely autocorrelated. Use block bootstrap or mSPRT.'
        )

    high_trunc = [r for r in results if r['p_truncate'] > 0.30]
    if high_trunc:
        recommendations.append(
            f'N_MAX={N_MAX} causes >30% truncation under some conditions. '
            'Increase N_MAX or use always-valid test to avoid boundary forcing.'
        )

    return {
        'ts': time.time(),
        'sprt_params': {'A': round(A, 6), 'B': round(B, 6), 'N_MAX': N_MAX,
                        'mu_0': MU_0, 'mu_1': MU_1, 'sigma': SIGMA},
        'n_sims': n_sims,
        'results': results,
        'n_alarm_conditions': len(alarm_conditions),
        'recommendations': recommendations,
        'calibration_ok': len([r for r in results if r['alarm']]) == 0,
    }


def self_test() -> int:
    failures = []
    # 1. Under H0 (mu=mu_0, rho=0), alpha should be ~0.05 (expect 0.02-0.12 at N_sims=500)
    r = simulate(MU_0, n_sims=500, rho=0.0)
    if r['empirical_alpha'] is None:
        failures.append('H0 simulation should produce empirical_alpha')
    elif not (0.0 <= r['empirical_alpha'] <= 0.15):
        # At N_sims=500, 3-sigma range for alpha=0.05 is roughly [0.02, 0.08].
        # Upper bound 0.15 catches badly miscalibrated SPRT while tolerating MC noise.
        failures.append(f'empirical_alpha={r["empirical_alpha"]} out of range [0, 0.15]')
    # 2. Under H1, beta should be < 0.50
    r1 = simulate(MU_1, n_sims=500, rho=0.0)
    if r1['empirical_beta'] is None:
        failures.append('H1 simulation should produce empirical_beta')
    elif r1['empirical_beta'] > 0.50:
        failures.append(f'empirical_beta={r1["empirical_beta"]} too high (>0.50)')
    # 3. ASN should be finite and < N_MAX
    if not (1 <= r['asn'] <= N_MAX):
        failures.append(f'ASN={r["asn"]} out of [1, N_MAX]')
    # 4. p_truncate + p_alarm + p_accept should sum to 1
    total = r['p_alarm'] + r['p_accept'] + r['p_truncate']
    # p_veto is counted inside p_alarm; check without double-count
    if abs(total - 1.0) > 0.05:
        failures.append(f'probabilities do not sum to 1: {total:.4f}')
    # 5. AR(1) sample should have correct mean
    s = _ar1_sample(10000, mu=5.0, sigma=1.0, rho=0.5)
    mean_s = sum(s) / len(s)
    if abs(mean_s - 5.0) > 0.2:
        failures.append(f'AR(1) mean={mean_s:.3f} far from target 5.0')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS', 'n_checks': 5}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--mu', type=float, default=None)
    ap.add_argument('--rho', type=float, default=0.0)
    ap.add_argument('--n-sims', type=int, default=2000)
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.mu is not None:
        r = simulate(args.mu, n_sims=args.n_sims, rho=args.rho)
        print(json.dumps(r, indent=2))
        return 0

    result = run_full_calibration(n_sims=args.n_sims)
    CACHE.mkdir(parents=True, exist_ok=True)
    out_path = CACHE / 'sprt-oc-calibration.json'
    tmp = out_path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(result, indent=2) + '\n')
    os.replace(tmp, out_path)
    result['output'] = str(out_path)
    print(json.dumps({
        'calibration_ok': result['calibration_ok'],
        'n_alarm_conditions': result['n_alarm_conditions'],
        'recommendations': result['recommendations'],
        'output': str(out_path),
    }, indent=2))
    return 0 if result['calibration_ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
