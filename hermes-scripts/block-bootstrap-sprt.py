#!/usr/bin/env python3
"""block-bootstrap-sprt.py — Wald SPRT with block-bootstrap thresholds.

Wald SPRT assumes i.i.d. observations. Loop metrics (PID error) are AR(1).
At rho=0.6, sprt-oc-eval.py measured empirical alpha ~0.24 vs target 0.05
(5x overshoot). This script:

  1. Runs classical Wald SPRT (A=log((1-beta)/alpha)).
  2. Resamples moving blocks of length L=ceil(sqrt(n)) (Kunsch 1989) to
     preserve short-range autocorrelation.
  3. From B bootstrap H0 paths, takes the empirical (1-alpha) quantile of
     max_t LLR_t as A_boot, replacing the i.i.d. Wald A.
  4. Reports Wald vs bootstrap alpha on AR(1) Monte Carlo.

LLR increment for N(mu0, sigma^2) vs N(mu1, sigma^2):
  llr += x*(mu1-mu0)/sigma^2 - (mu1^2 - mu0^2)/(2*sigma^2)
Defaults match sprt-oc-eval.py: mu0=3.5, mu1=4.0, sigma=1, alpha=beta=0.05.

Usage:
  python3 block-bootstrap-sprt.py --self-test
  python3 block-bootstrap-sprt.py [--n 200] [--rho 0.6] [--B 500]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
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
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'block-bootstrap-sprt.json'

MU_0 = 3.5
MU_1 = 4.0
SIGMA = 1.0
ALPHA = 0.05
BETA = 0.05
N_MAX = 200
B_DEFAULT = 500


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def wald_bounds(alpha: float = ALPHA, beta: float = BETA) -> tuple[float, float]:
    a = math.log((1.0 - beta) / alpha)
    b = math.log(beta / (1.0 - alpha))
    return a, b


def llr_increment(x: float, mu0: float = MU_0, mu1: float = MU_1, sigma: float = SIGMA) -> float:
    s2 = sigma * sigma
    return x * (mu1 - mu0) / s2 - (mu1 * mu1 - mu0 * mu0) / (2.0 * s2)


def ar1_sample(n: int, mu: float, sigma: float, rho: float, rng: random.Random) -> list[float]:
    innov = sigma * math.sqrt(max(0.0, 1.0 - rho * rho))
    x_prev = mu
    out = []
    for _ in range(n):
        x = mu + rho * (x_prev - mu) + rng.gauss(0.0, innov)
        out.append(x)
        x_prev = x
    return out


def sprt_path(xs: list[float], a: float, b: float, mu0: float = MU_0, mu1: float = MU_1, sigma: float = SIGMA) -> dict:
    llr = 0.0
    max_llr = 0.0
    min_llr = 0.0
    decision = 'truncate'
    n_stop = len(xs)
    for t, x in enumerate(xs, start=1):
        llr += llr_increment(x, mu0, mu1, sigma)
        max_llr = max(max_llr, llr)
        min_llr = min(min_llr, llr)
        if llr >= a:
            decision = 'reject_H0'
            n_stop = t
            break
        if llr <= b:
            decision = 'accept_H0'
            n_stop = t
            break
    return {
        'decision': decision,
        'n': n_stop,
        'llr': llr,
        'max_llr': max_llr,
        'min_llr': min_llr,
    }


def block_length(n: int) -> int:
    return max(1, math.ceil(math.sqrt(n)))


def moving_block_resample(xs: list[float], L: int, rng: random.Random) -> list[float]:
    n = len(xs)
    if n == 0:
        return []
    L = min(max(1, L), n)
    last_start = n - L
    out: list[float] = []
    while len(out) < n:
        start = rng.randrange(0, last_start + 1)
        out.extend(xs[start:start + L])
    return out[:n]


def empirical_quantile(values: list[float], q: float) -> float:
    if not values:
        return float('nan')
    xs = sorted(values)
    if q <= 0:
        return xs[0]
    if q >= 1:
        return xs[-1]
    idx = q * (len(xs) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return xs[lo]
    w = idx - lo
    return xs[lo] * (1.0 - w) + xs[hi] * w


def max_llr_unstopped(xs: list[float], mu0: float = MU_0, mu1: float = MU_1, sigma: float = SIGMA) -> float:
    """Peak LLR on the full sample — do not stop at Wald A (that would cap the quantile)."""
    llr = 0.0
    peak = 0.0
    for x in xs:
        llr += llr_increment(x, mu0, mu1, sigma)
        peak = max(peak, llr)
    return peak


def calibrate_threshold(
    xs_h0: list[float],
    B: int,
    alpha: float,
    beta: float,
    seed: int = 0,
) -> dict:
    n = len(xs_h0)
    L = block_length(n)
    a_wald, b_wald = wald_bounds(alpha, beta)
    rng = random.Random(seed)
    max_llrs = []
    wald_reject = 0
    for i in range(B):
        boot = moving_block_resample(xs_h0, L, rng)
        max_llrs.append(max_llr_unstopped(boot))
        path = sprt_path(boot, a_wald, b_wald)
        if path['decision'] == 'reject_H0':
            wald_reject += 1
    a_boot = empirical_quantile(max_llrs, 1.0 - alpha)
    # Never take a threshold below Wald A — bootstrap noise can undershoot on short n.
    if not math.isfinite(a_boot) or a_boot < a_wald:
        a_boot = a_wald
    b_boot = b_wald
    return {
        'n': n,
        'L': L,
        'B': B,
        'A_wald': a_wald,
        'B_wald': b_wald,
        'A_boot': a_boot,
        'B_boot': b_boot,
        'wald_alpha_hat_on_bootstrap': (wald_reject / B) if B else None,
        'max_llr_q95': empirical_quantile(max_llrs, 0.95),
        'max_llr_median': empirical_quantile(max_llrs, 0.5),
    }


def mc_alpha_beta(
    a: float,
    b: float,
    n: int,
    rho: float,
    n_sims: int,
    seed: int,
) -> dict:
    rng = random.Random(seed)
    n_rej_h0 = 0
    n_acc_h1 = 0
    asn_h0 = 0.0
    asn_h1 = 0.0
    for i in range(n_sims):
        h0 = ar1_sample(n, MU_0, SIGMA, rho, rng)
        p0 = sprt_path(h0, a, b)
        asn_h0 += p0['n']
        if p0['decision'] == 'reject_H0':
            n_rej_h0 += 1
        h1 = ar1_sample(n, MU_1, SIGMA, rho, rng)
        p1 = sprt_path(h1, a, b)
        asn_h1 += p1['n']
        if p1['decision'] == 'accept_H0':
            n_acc_h1 += 1
    return {
        'rho': rho,
        'n_sims': n_sims,
        'empirical_alpha': n_rej_h0 / n_sims,
        'empirical_beta': n_acc_h1 / n_sims,
        'asn_h0': asn_h0 / n_sims,
        'asn_h1': asn_h1 / n_sims,
    }


def load_metric_series() -> list[float]:
    for p in (
        _hermes_root / 'cache' / 'loop-pid-state.json',
        _hermes_base / 'cache' / 'loop-pid-state.json',
    ):
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        xs = []
        for step in data.get('history') or []:
            if isinstance(step, dict) and 'e' in step:
                try:
                    xs.append(float(step['e']))
                except (TypeError, ValueError):
                    continue
        if xs:
            return xs
    return []


def run(n: int = N_MAX, rho: float = 0.6, B: int = B_DEFAULT, n_sims: int = 400, seed: int = 1) -> dict:
    rng = random.Random(seed)
    # Governance SPRT is N(3.5,1) vs N(4.0,1) — NOT raw PID error. Calibrate on
    # AR(1) H0 draws matching sprt-oc-eval.py. Live PID errors are attached only
    # as diagnostics (wrong location family; would collapse A_boot to 0).
    h0_series = ar1_sample(n, MU_0, SIGMA, rho, rng)
    source = 'synthetic_ar1_h0'
    live = load_metric_series()
    cal = calibrate_threshold(h0_series, B=B, alpha=ALPHA, beta=BETA, seed=seed + 17)
    a_wald, b_wald = cal['A_wald'], cal['B_wald']
    a_boot, b_boot = cal['A_boot'], cal['B_boot']
    # Monte Carlo OC under AR(1) for Wald vs bootstrap thresholds.
    # Keep n_sims modest: stdlib, B=500 already paid.
    wald_oc = mc_alpha_beta(a_wald, b_wald, n=n, rho=rho, n_sims=n_sims, seed=seed + 101)
    boot_oc = mc_alpha_beta(a_boot, b_boot, n=n, rho=rho, n_sims=n_sims, seed=seed + 202)
    iid_oc = mc_alpha_beta(a_wald, b_wald, n=n, rho=0.0, n_sims=n_sims, seed=seed + 303)
    alarm = boot_oc['empirical_alpha'] > ALPHA * 1.5 and wald_oc['empirical_alpha'] > ALPHA * 2
    out = {
        'ts': datetime.now(UTC).isoformat(),
        'theorem': (
            'Wald SPRT i.i.d. assumption fails under AR(1); Kunsch moving-block '
            'bootstrap calibrates A so P_H0(max LLR >= A_boot) ~= alpha'
        ),
        'source': source,
        'n_series': len(h0_series),
        'n_live_pid': len(live),
        'live_pid_mean': (sum(live) / len(live)) if live else None,
        'rho_eval': rho,
        'mu0': MU_0,
        'mu1': MU_1,
        'sigma': SIGMA,
        'alpha_target': ALPHA,
        'beta_target': BETA,
        'calibration': cal,
        'oc_wald_rho': wald_oc,
        'oc_boot_rho': boot_oc,
        'oc_wald_iid': iid_oc,
        'wald_overshoot': wald_oc['empirical_alpha'] / ALPHA if ALPHA else None,
        'boot_overshoot': boot_oc['empirical_alpha'] / ALPHA if ALPHA else None,
        'alarm': bool(alarm),
        'note': (
            'A_boot replaces Wald A for autocorrelated loop metrics. '
            'If boot alpha still overshoots, raise A further or use mSPRT.'
        ),
    }
    try:
        _atomic_write(OUT_PATH, out)
        out['output'] = str(OUT_PATH)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    a, b = wald_bounds(0.05, 0.05)
    if abs(a - math.log(19)) > 1e-9 or abs(b + math.log(19)) > 1e-9:
        failures.append('wald bounds')
    rng = random.Random(0)
    xs = [0.0] * 16
    boot = moving_block_resample(xs, L=4, rng=rng)
    if len(boot) != 16:
        failures.append('block resample length')
    if block_length(100) != 10:
        failures.append('L=ceil(sqrt(n))')
    # i.i.d. H0 should not wildly exceed alpha at Wald A (allow Monte Carlo noise)
    iid = mc_alpha_beta(a, b, n=80, rho=0.0, n_sims=200, seed=3)
    if iid['empirical_alpha'] > 0.20:
        failures.append(f'iid alpha too high {iid["empirical_alpha"]}')
    # AR(1) rho=0.6 Wald alpha should exceed iid alpha (the bug we are fixing)
    ar = mc_alpha_beta(a, b, n=80, rho=0.6, n_sims=200, seed=4)
    if ar['empirical_alpha'] < iid['empirical_alpha']:
        failures.append(
            f'expected AR(1) alpha overshoot; iid={iid["empirical_alpha"]} ar={ar["empirical_alpha"]}'
        )
    # bootstrap threshold should be >= Wald A under positive autocorrelation
    series = ar1_sample(120, MU_0, SIGMA, 0.6, random.Random(5))
    cal = calibrate_threshold(series, B=80, alpha=0.05, beta=0.05, seed=6)
    if not math.isfinite(cal['A_boot']):
        failures.append('A_boot nonfinite')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({
        'self_test': 'PASS',
        'iid_alpha': iid['empirical_alpha'],
        'ar_alpha': ar['empirical_alpha'],
        'A_wald': a,
        'A_boot': cal['A_boot'],
        'L': cal['L'],
    }))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--n', type=int, default=N_MAX)
    p.add_argument('--rho', type=float, default=0.6)
    p.add_argument('--B', type=int, default=B_DEFAULT)
    p.add_argument('--n-sims', type=int, default=400)
    p.add_argument('--seed', type=int, default=1)
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run(n=args.n, rho=args.rho, B=args.B, n_sims=args.n_sims, seed=args.seed)
    print(json.dumps({
        k: out.get(k) for k in (
            'source', 'n_series', 'rho_eval', 'wald_overshoot', 'boot_overshoot',
            'alarm', 'output',
        )
    }))
    print(json.dumps({
        'A_wald': (out.get('calibration') or {}).get('A_wald'),
        'A_boot': (out.get('calibration') or {}).get('A_boot'),
        'L': (out.get('calibration') or {}).get('L'),
        'oc_wald_alpha': (out.get('oc_wald_rho') or {}).get('empirical_alpha'),
        'oc_boot_alpha': (out.get('oc_boot_rho') or {}).get('empirical_alpha'),
        'oc_iid_alpha': (out.get('oc_wald_iid') or {}).get('empirical_alpha'),
    }))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
