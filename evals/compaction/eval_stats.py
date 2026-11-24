#!/usr/bin/env python3
"""Statistical CI + SPRT utilities for compaction / routing A/B evals.

Stdlib only (no scipy). Wilson score interval, two-proportion sample size,
Wald SPRT, Hoeffding n.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

Z95 = 1.96
Z80 = 0.842  # Φ^{-1}(0.80) for 80% power (one-sided)


def _z_two_sided(alpha: float) -> float:
    if abs(float(alpha) - 0.05) < 1e-12:
        return Z95
    if abs(float(alpha) - 0.01) < 1e-12:
        return 2.576
    if abs(float(alpha) - 0.10) < 1e-12:
        return 1.645
    # Beasley-Springer/Moro-style rational approx of N(0,1) upper quantile
    p = min(max(float(alpha), 1e-12), 1.0 - 1e-12) / 2.0
    t = math.sqrt(-2.0 * math.log(p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    return t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t)


def _z_power(power: float) -> float:
    if abs(float(power) - 0.80) < 1e-12:
        return Z80
    # one-sided Φ^{-1}(power)
    p = min(max(1.0 - float(power), 1e-12), 1.0 - 1e-12)
    t = math.sqrt(-2.0 * math.log(p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    return t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t)


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval; returns (lo, hi) in [0, 1]."""
    n = int(n)
    k = int(k)
    if n <= 0:
        return 0.0, 1.0
    k = max(0, min(k, n))
    z = _z_two_sided(alpha)
    z2 = z * z
    p = k / n
    denom = n + z2
    center = (k + z2 / 2.0) / denom
    half = z * math.sqrt(n * p * (1.0 - p) + z2 / 4.0) / denom
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return (lo, hi)


def cohen_n_per_arm(p1: float, p2: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Sample size per arm for a two-proportion z-test."""
    p1 = min(max(float(p1), 0.0), 1.0)
    p2 = min(max(float(p2), 0.0), 1.0)
    diff = p1 - p2
    if abs(diff) < 1e-15:
        return 10**9
    z_a = _z_two_sided(alpha)
    z_b = _z_power(power)
    num = (z_a + z_b) ** 2 * (p1 * (1.0 - p1) + p2 * (1.0 - p2))
    n = num / (diff * diff)
    return math.ceil(n - 1e-12)


def sprt_decide(
    observations: list[int],
    p0: float = 0.40,
    p1: float = 0.30,
    alpha: float = 0.05,
    beta: float = 0.10,
    n_max: int = 30,
) -> dict:
    """Wald sequential test on 0/1 observations.

    H0: p = p0 (healthy), H1: p = p1 (degraded). Fail-closed truncation.
    """
    eps = 1e-12
    p0 = min(max(float(p0), eps), 1.0 - eps)
    p1 = min(max(float(p1), eps), 1.0 - eps)
    alpha = min(max(float(alpha), eps), 1.0 - eps)
    beta = min(max(float(beta), eps), 1.0 - eps)
    A = math.log((1.0 - beta) / alpha)
    B = math.log(beta / (1.0 - alpha))
    llr = 0.0
    n = 0
    decision = 'continue'
    log_p1_p0 = math.log(p1 / p0)
    log_q1_q0 = math.log((1.0 - p1) / (1.0 - p0))
    for x in observations or []:
        xi = 1 if int(x) else 0
        llr += (log_p1_p0 if xi else log_q1_q0)
        n += 1
        if llr >= A:
            decision = 'accept_h1'
            break
        if llr <= B:
            decision = 'accept_h0'
            break
        if n >= int(n_max):
            decision = 'truncated_reject'
            break
    else:
        if n >= int(n_max) and decision == 'continue':
            decision = 'truncated_reject'
    return {
        'decision': decision,
        'llr': llr,
        'n': n,
        'A': A,
        'B': B,
    }


def hoeffding_n(eps: float, delta: float) -> int:
    """n >= log(2/delta) / (2 eps^2) so P(|mean-mu| > eps) <= delta."""
    eps = abs(float(eps))
    delta = min(max(float(delta), 1e-15), 1.0)
    if eps < 1e-15:
        return 10**9
    n = math.log(2.0 / delta) / (2.0 * eps * eps)
    return math.ceil(n - 1e-12)


def _self_test() -> int:
    failures: list[str] = []
    w60 = wilson_ci(24, 60)
    w30 = wilson_ci(15, 30)
    width60 = w60[1] - w60[0]
    width30 = w30[1] - w30[0]
    if not (width60 < width30):
        failures.append(f'wilson width n=60 ({width60:.4f}) !< n=30 ({width30:.4f})')
    lo0, hi0 = wilson_ci(0, 10)
    if lo0 != 0.0:
        failures.append(f'wilson_ci(0,10) lo={lo0!r} != 0.0 (hi={hi0})')
    n_arm = cohen_n_per_arm(0.50, 0.40)
    if n_arm < 100:
        failures.append(f'cohen_n_per_arm(0.50,0.40)={n_arm} < 100')
    miss = sprt_decide([0] * 20)
    if miss['decision'] not in {'accept_h1', 'truncated_reject'}:
        failures.append(f'sprt all-miss decision={miss["decision"]!r}')
    hit = sprt_decide([1] * 20)
    if hit['decision'] != 'accept_h0':
        failures.append(f'sprt all-hit decision={hit["decision"]!r} expected accept_h0')
    hn = hoeffding_n(0.10, 0.05)
    if hn <= 100:
        failures.append(f'hoeffding_n(0.10,0.05)={hn} <= 100')
    lo, hi = wilson_ci(30, 60)
    width_n60 = hi - lo
    # old hardcoded ±24pt at N=60 is ~0.48 full-width in percent-points terms;
    # true Wilson at p=0.5, n=60 is ~0.245. Accept the 0.20–0.50 band.
    if not (0.20 <= width_n60 <= 0.50):
        failures.append(f'wilson_ci(30,60) width={width_n60:.4f} not in [0.20,0.50]')
    # bounds
    a, b = wilson_ci(60, 60)
    if not (0.0 <= a <= b <= 1.0):
        failures.append(f'wilson_ci(60,60) out of bounds {(a,b)}')
    if failures:
        print('self-test FAIL', file=sys.stderr)
        for f in failures:
            print(' -', f, file=sys.stderr)
        return 1
    print('self-test PASS')
    print(json.dumps({
        'wilson_24_60': w60,
        'wilson_15_30': w30,
        'wilson_0_10': [lo0, hi0],
        'cohen_n_0.50_0.40': n_arm,
        'sprt_miss': miss,
        'sprt_hit': {k: hit[k] for k in ('decision', 'llr', 'n')},
        'hoeffding_n': hn,
        'wilson_30_60_width': width_n60,
    }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Wilson CI / Cohen n / SPRT / Hoeffding utilities')
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    p.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
