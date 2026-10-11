#!/usr/bin/env python3
"""cusum-h-calibrator.py — Calibrate Page CUSUM threshold h for ARL_0 >= 500.

loop-cusum-changepoint.py currently uses h=4.0 with no ARL target (AUDIT-10).
This calibrator:

  1. Reads loop-pid-state.json (or synthesises AR(1) if history is short).
  2. Estimates mu_0, sigma from the first W=50 steps (pre-change window).
  3. Studentizes z = e / sigma (task spec) and runs two-sided Page CUSUM
     with allowance k (default 0.25) on (z - mu0/sigma).
  4. Estimates in-control ARL via moving-block bootstrap (B=200 trials).
  5. Binary-searches h* such that ARL_0 >= 500.

Page / Wald sequential analysis; block bootstrap preserves AR(1) structure
the same way block-bootstrap-sprt.py does.

Usage:
  python3 cusum-h-calibrator.py --self-test
  python3 cusum-h-calibrator.py [--arl-target 500] [--B 200]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'cusum-h-calibration.json'

W_PRE = 50
K_DEFAULT = 0.25
H_DEFAULT = 4.0
ARL_TARGET = 500
B_DEFAULT = 200
MAX_RUN = 4000


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def load_errors() -> list[float]:
    for p in (
        _hermes_root / 'cache' / 'loop-pid-state.json',
        _hermes_base / 'cache' / 'loop-pid-state.json',
        Path.home() / '.hermes' / 'cache' / 'loop-pid-state.json',
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


def mean_std(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    if n == 0:
        return 0.0, 1.0
    mu = sum(xs) / n
    if n < 2:
        return mu, 1.0
    var = sum((x - mu) ** 2 for x in xs) / (n - 1)
    sig = math.sqrt(var) if var > 0 else 1e-9
    return mu, max(sig, 1e-9)


def studentize(xs: list[float], sigma: float) -> list[float]:
    s = sigma if sigma > 0 else 1e-9
    return [x / s for x in xs]


def cusum_run_length(zs: list[float], mu0: float, k: float, h: float, max_run: int | None = None) -> int:
    """Return first alarm index+1, or len(zs) if no alarm (censored)."""
    sp = 0.0
    sm = 0.0
    limit = len(zs) if max_run is None else min(len(zs), max_run)
    for i in range(limit):
        x = zs[i]
        sp = max(0.0, sp + (x - mu0) - k)
        sm = max(0.0, sm - (x - mu0) - k)
        if sp > h or sm > h:
            return i + 1
    return limit


def block_length(n: int) -> int:
    return max(1, math.ceil(math.sqrt(n)))


def moving_block_resample(xs: list[float], L: int, n_out: int, rng: random.Random) -> list[float]:
    n = len(xs)
    if n == 0:
        return [0.0] * n_out
    L = min(max(1, L), n)
    last_start = n - L
    out: list[float] = []
    while len(out) < n_out:
        start = rng.randrange(0, last_start + 1)
        out.extend(xs[start:start + L])
    return out[:n_out]


def linear_detrend(xs: list[float]) -> tuple[list[float], float]:
    n = len(xs)
    if n < 2:
        return list(xs), 0.0
    xbar = (n - 1) / 2.0
    ybar = sum(xs) / n
    sxx = sum((i - xbar) ** 2 for i in range(n))
    sxy = sum((i - xbar) * (xs[i] - ybar) for i in range(n))
    slope = (sxy / sxx) if sxx else 0.0
    resid = [xs[i] - (ybar + slope * (i - xbar)) for i in range(n)]
    return resid, slope


def arl0_block_bootstrap(
    pre_z: list[float],
    mu0: float,
    k: float,
    h: float,
    B: int,
    arl_target: int,
    seed: int,
) -> dict:
    # Bootstrap centered residuals so a tracking transient does not look like
    # a perpetual mean shift when blocks are concatenated.
    centered = [z - mu0 for z in pre_z]
    L = block_length(len(centered))
    rng = random.Random(seed)
    n_out = max(arl_target * 4, MAX_RUN)
    rls = []
    n_censored = 0
    for i in range(B):
        resid = moving_block_resample(centered, L, n_out, rng)
        series = [r + mu0 for r in resid]
        rl = cusum_run_length(series, mu0=mu0, k=k, h=h, max_run=n_out)
        if rl >= n_out:
            n_censored += 1
        rls.append(rl)
    arl = (sum(rls) / len(rls)) if rls else 0.0
    return {
        'h': h,
        'k': k,
        'B': B,
        'L': L,
        'n_out': n_out,
        'ARL0': arl,
        'n_censored': n_censored,
        'min_rl': min(rls) if rls else None,
        'max_rl': max(rls) if rls else None,
        'censored': n_censored > 0,
    }


def search_h(
    pre_z: list[float],
    mu0: float,
    k: float,
    B: int,
    arl_target: int,
    seed: int,
    h_lo: float = 0.5,
    h_hi: float = 40.0,
    n_iter: int = 12,
) -> dict:
    """Binary search smallest h in [h_lo, h_hi] with ARL0 >= target.

    Because ARL is increasing in h, search the lower bound of the feasible set.
    """
    history = []
    best = None
    lo, hi = h_lo, h_hi
    for i in range(n_iter):
        mid = 0.5 * (lo + hi)
        est = arl0_block_bootstrap(pre_z, mu0, k, mid, B, arl_target, seed + i * 17)
        history.append({'h': mid, 'ARL0': est['ARL0'], 'n_censored': est['n_censored']})
        if est['ARL0'] >= arl_target:
            best = est
            hi = mid
        else:
            lo = mid
    if best is None:
        # Even h_hi failed — return the high end as the recommendation.
        best = arl0_block_bootstrap(pre_z, mu0, k, h_hi, B, arl_target, seed + 999)
        best['hit_target'] = best['ARL0'] >= arl_target
    else:
        best['hit_target'] = True
    best['search'] = history
    best['h_star'] = best['h']
    return best


def synthetic_prechange(n: int = W_PRE, seed: int = 0) -> list[float]:
    rng = random.Random(seed)
    # In-control PID residual: small AR(1) around 0.
    rho = 0.3
    x_prev = 0.0
    xs = []
    for _ in range(n):
        x = rho * x_prev + rng.gauss(0.0, 0.05)
        xs.append(x)
        x_prev = x
    return xs


def run(arl_target: int = ARL_TARGET, B: int = B_DEFAULT, k: float = K_DEFAULT, seed: int = 2) -> dict:
    xs = load_errors()
    source = 'loop-pid-state'
    if len(xs) < W_PRE:
        xs = synthetic_prechange(n=max(W_PRE, 80), seed=seed)
        source = 'synthetic_prechange'
    pre = xs[:W_PRE]
    mu0_e, sigma = mean_std(pre)
    resid_e, slope_e = linear_detrend(pre)
    _, sigma_resid = mean_std(resid_e)
    # In-control series: detrended, studentized by residual sigma, mean 0.
    z_ic = studentize(resid_e, sigma_resid)
    mu0_z = 0.0
    uncal = arl0_block_bootstrap(z_ic, mu0_z, k, H_DEFAULT, B, arl_target, seed)
    cal = search_h(z_ic, mu0_z, k, B, arl_target, seed + 50)
    out = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'theorem': 'Page CUSUM ARL_0 calibration via Kunsch moving-block bootstrap; AUDIT-10',
        'source': source,
        'n_series': len(xs),
        'W_pre': W_PRE,
        'mu0': mu0_e,
        'sigma': sigma,
        'mu0_studentized': mu0_z,
        'sigma_resid': sigma_resid,
        'prechange_slope': slope_e,
        'k': k,
        'h_default': H_DEFAULT,
        'ARL0_h_default': uncal['ARL0'],
        'h_star': cal['h_star'],
        'ARL0_h_star': cal['ARL0'],
        'hit_target': cal.get('hit_target'),
        'arl_target': arl_target,
        'B': B,
        'L': block_length(len(z_ic)),
        'search': cal.get('search'),
        'uncalibrated': uncal,
        'recommendation': (
            f'replace loop-cusum-changepoint H_DEFAULT={H_DEFAULT} with h*={cal["h_star"]:.3f}'
        ),
        'alarm': not bool(cal.get('hit_target')),
    }
    try:
        _atomic_write(OUT_PATH, out)
        out['output'] = str(OUT_PATH)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    # In-control zeros never alarm
    rl = cusum_run_length([0.0] * 40, mu0=0.0, k=0.25, h=4.0)
    if rl != 40:
        failures.append('in-control zeros should not alarm')
    # Large step should alarm quickly
    rl2 = cusum_run_length([0.0] * 5 + [3.0] * 20, mu0=0.0, k=0.25, h=4.0)
    if rl2 > 20:
        failures.append(f'step should alarm, rl={rl2}')
    mu, sig = mean_std([1.0, 3.0, 5.0])
    if abs(mu - 3.0) > 1e-12:
        failures.append('mean')
    pre = synthetic_prechange(n=50, seed=1)
    z = studentize(pre, mean_std(pre)[1])
    # h large => ARL large; h tiny => ARL small
    hi = arl0_block_bootstrap(z, 0.0, 0.25, 12.0, B=30, arl_target=500, seed=2)
    lo = arl0_block_bootstrap(z, 0.0, 0.25, 0.6, B=30, arl_target=500, seed=3)
    if hi['ARL0'] < lo['ARL0']:
        failures.append(f'ARL not increasing in h: hi={hi["ARL0"]} lo={lo["ARL0"]}')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({
        'self_test': 'PASS',
        'step_rl': rl2,
        'ARL_h12': hi['ARL0'],
        'ARL_h0.6': lo['ARL0'],
    }))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--arl-target', type=int, default=ARL_TARGET)
    p.add_argument('--B', type=int, default=B_DEFAULT)
    p.add_argument('--k', type=float, default=K_DEFAULT)
    p.add_argument('--seed', type=int, default=2)
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run(arl_target=args.arl_target, B=args.B, k=args.k, seed=args.seed)
    print(json.dumps({
        k: out.get(k) for k in (
            'source', 'n_series', 'mu0', 'sigma', 'h_default', 'ARL0_h_default',
            'h_star', 'ARL0_h_star', 'hit_target', 'recommendation', 'output',
        )
    }))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
