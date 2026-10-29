#!/usr/bin/env python3
"""Read calibration-log.jsonl and update Condorcet consistency thresholds.
Called by cron or manually. Implements calibration loop closure (ARCHITECTURE.md gap).
"""
import json
import math
import os
import sys
import time
from pathlib import Path
from collections import defaultdict

_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (_hermes_base / "profiles" / _hermes_profile) if _hermes_profile and "profiles" not in str(_hermes_base) else _hermes_base
LOG_PATH = _hermes_root / "cache" / "calibration-log.jsonl"
THRESH_PATH = _hermes_root / "cache" / "condorcet-thresholds.json"
CAL_MAP_PATH = _hermes_root / "cache" / "calibration-map.json"
_CAL_MAP_MAX_AGE_S = 86400  # 24 hours
_KISH_RHO_DEFAULT = 0.2  # Stureborg et al. 2024 LLM-judge ICC mid-conservative


def kish_effective_n(n, rho=_KISH_RHO_DEFAULT):
    """Kish (1965, Survey Sampling §6.5) design-effect correction.

    n_eff = n / (1 + (n - 1) * rho)

    When Condorcet judges are LLMs (or variants of one model) their votes are
    correlated, so the nominal n inflates precision. rho is the intra-cluster
    correlation. Default 0.2 is conservative but defensible for LLM judges
    (Stureborg et al. 2024, 'Is LLM-as-a-Judge Robust?' found 0.1-0.4 for
    GPT-4 judge panels). Clamped to [1, n].
    """
    n = float(n)
    if n <= 1:
        return 1.0
    n_eff = n / (1.0 + (n - 1.0) * float(rho))
    return max(1.0, min(n, n_eff))


def wilson_ci_effective(p_hat, n_eff, z=1.96):
    """Wilson score interval using Kish effective sample size in place of n.

    p_hat is the observed proportion (agreements / n), NOT the raw hit count.
    n_eff is the Kish-corrected effective sample size (a float <= n).

    Formula (Wilson 1927, applied to n_eff):
      z2 = z*z
      denom = 1 + z2/n_eff
      centre = (p_hat + z2/(2*n_eff)) / denom
      half_width = z * sqrt(p_hat*(1-p_hat)/n_eff + z2/(4*n_eff*n_eff)) / denom

    Returns (p_hat, max(0, centre-half_width), min(1, centre+half_width)).

    See Kish (1965) 'Survey Sampling' §6.5 for n_eff; Stureborg et al. (2024)
    'Is LLM-as-a-Judge Robust?' for the rho=0.2 default used to form n_eff.
    """
    n_eff = float(n_eff)
    n_eff = max(n_eff, 1.0)
    p_hat = float(p_hat)
    p_hat = max(0.0, min(1.0, p_hat))
    z2 = z * z
    denom = 1.0 + z2 / n_eff
    centre = (p_hat + z2 / (2.0 * n_eff)) / denom
    inner = p_hat * (1.0 - p_hat) / n_eff + z2 / (4.0 * n_eff * n_eff)
    inner = max(inner, 0.0)
    half_width = z * math.sqrt(inner) / denom
    return (p_hat, max(0.0, centre - half_width), min(1.0, centre + half_width))


def bonferroni_joint_alpha(k, alpha=0.05):
    """Bonferroni joint alpha for k independent tests. Union bound: P(any error) <= k*alpha. Grimmett & Stirzaker (2001) section 1.3 Booles inequality; Billingsley (1995) section 4."""
    return min(1.0, k * alpha)


def sidak_joint_alpha(k, alpha=0.05):
    """Sidak (1967) joint alpha for k independent tests. P(at least one error) = 1 - (1-alpha)^k. Sidak (1967) Rectangular confidence regions JASA 62(317) pages 626-633."""
    return 1.0 - (1.0 - alpha) ** k


def _load_calibration_bounds():
    """Load low_thresh/high_thresh from calibration-map.json if <24h old.

    The calibration map is written by calibration_loop.py (Platt-scaling /
    PAV isotonic regression breakpoints).  We derive sanity bounds from the
    breakpoints: low_thresh = min calibrated probability (y at lowest x),
    high_thresh = max calibrated probability (y at highest x).

    Returns (low_thresh, high_thresh) or None if unavailable/stale.
    """
    try:
        if not CAL_MAP_PATH.exists():
            return None
        age = time.time() - CAL_MAP_PATH.stat().st_mtime
        if age > _CAL_MAP_MAX_AGE_S:
            return None
        with open(CAL_MAP_PATH) as _f:
            cal_map = json.load(_f)
        bps = cal_map.get("breakpoints", [])
        if not bps:
            return None
        ys = [bp[1] for bp in bps if len(bp) >= 2]
        if not ys:
            return None
        return min(ys), max(ys)
    except Exception:
        return None


def main():
    if not LOG_PATH.exists():
        print('No calibration log found - using defaults')
        return

    scope_stats = defaultdict(lambda: {'total': 0, 'agreements': 0, 'predicted_sum': 0.0})

    for line in LOG_PATH.read_text().splitlines():
        try:
            row = json.loads(line)
            scope = row.get('scope', 'L2')
            predicted = float(row.get('predicted_confidence', 0.5))
            agreed = bool(row.get('agreed', True))
            scope_stats[scope]['total'] += 1
            scope_stats[scope]['predicted_sum'] += predicted
            if agreed:
                scope_stats[scope]['agreements'] += 1
        except Exception:
            continue

    # Load existing thresholds so EMA accumulates across runs (M1 fix)
    existing_thresholds = {}
    try:
        if THRESH_PATH.exists():
            existing_thresholds = json.loads(THRESH_PATH.read_text())
    except Exception:
        pass

    thresholds = {}
    for scope, stats in scope_stats.items():
        n = stats['total']
        if n < 10:
            thresholds[scope] = {'threshold': 0.5, 'observed_rate': None, 'n': n}
            continue
        observed_rate = stats['agreements'] / n
        n_eff = kish_effective_n(n)
        _, ci_lo, ci_hi = wilson_ci_effective(observed_rate, n_eff)
        predicted_rate = stats['predicted_sum'] / n
        drift = abs(predicted_rate - observed_rate)
        if drift > 0.15:
            print(f'CALIBRATION DRIFT: scope={scope} predicted={predicted_rate:.2f} '
                  f'observed={observed_rate:.2f} drift={drift:.2f}')
        # Exponential moving average toward observed rate, seeded from prior run (not hardcoded 0.5)
        prior = existing_thresholds.get(scope, {}).get('threshold', 0.5)
        updated = prior * 0.9 + observed_rate * 0.1
        # Calibration-map sanity bound (calibration_loop.py → calibration-threshold-updater feedback).
        # If calibration-map.json is fresh (<24h), clamp the EMA result to
        # [low_thresh * 0.8, high_thresh * 1.2] so the threshold never wanders
        # outside the range that the PAV isotonic calibrator considers meaningful.
        cal_bounds = _load_calibration_bounds()
        clamped_by_cal_map = False
        if cal_bounds is not None:
            low_thresh, high_thresh = cal_bounds
            lo_bound = low_thresh * 0.8
            hi_bound = high_thresh * 1.2
            raw_updated = updated
            updated = max(lo_bound, min(hi_bound, updated))
            if updated != raw_updated:
                clamped_by_cal_map = True
                print(f'CAL_MAP_CLAMP: scope={scope} raw={raw_updated:.4f} '
                      f'clamped={updated:.4f} bounds=[{lo_bound:.4f}, {hi_bound:.4f}] '
                      f'(calibration-map low={low_thresh:.4f} high={high_thresh:.4f})')
        thresholds[scope] = {
            'threshold': round(updated, 3),
            'observed_rate': round(observed_rate, 3),
            'n': n,
            'n_eff': round(n_eff, 4),
            'ci_lo': round(ci_lo, 4),
            'ci_hi': round(ci_hi, 4),
            'rho': _KISH_RHO_DEFAULT,
            'ts': time.time(),
            'clamped_by_cal_map': clamped_by_cal_map,
        }
        print(f'scope={scope}: threshold={updated:.3f} (observed={observed_rate:.2f}, n={n})')
        print(f'scope={scope}: n={n} n_eff={n_eff:.1f} (rho={_KISH_RHO_DEFAULT}) CI=[{ci_lo:.3f}, {ci_hi:.3f}]')

    THRESH_PATH.parent.mkdir(parents=True, exist_ok=True)
    # M7 fix: atomic write via tmp+rename to prevent Condorcet threshold corruption
    _thresh_tmp = THRESH_PATH.with_suffix('.tmp')
    _thresh_tmp.write_text(json.dumps(thresholds, indent=2))
    _thresh_tmp.rename(THRESH_PATH)
    print(f'Written: {THRESH_PATH}')
    k_gates = 3
    joint = sidak_joint_alpha(k_gates, 0.05)
    per_bonf = 0.05 / 3.0
    per_sidak = 1.0 - (1.0 - 0.05) ** (1.0 / 3.0)
    print(
        f'[joint-alpha] 3 gates each at alpha=0.05 -> Sidak joint miscoverage={joint:.4f} ({joint * 100:.2f}%)'
    )
    print(
        f'[joint-alpha] To maintain 5% joint, run each gate at alpha={per_bonf:.4f} (Bonferroni) or {per_sidak:.4f} (Sidak)'
    )


def _self_test():
    n_eff = kish_effective_n(100, rho=0.2)
    expected = 100.0 / (1.0 + 99.0 * 0.2)
    assert abs(n_eff - expected) < 1e-9, (n_eff, expected)
    assert 1.0 <= n_eff <= 100.0
    assert kish_effective_n(1) == 1.0
    assert kish_effective_n(10, rho=0.0) == 10.0
    p, lo, hi = wilson_ci_effective(0.5, 100.0)   # p_hat=0.5, n_eff=100
    assert abs(p - 0.5) < 1e-9
    assert 0.0 <= lo <= p <= hi <= 1.0
    n_eff10 = kish_effective_n(10)
    assert n_eff10 < 10.0
    p1, lo1, hi1 = wilson_ci_effective(0.2, n_eff10)  # p_hat=0.2, n_eff small
    assert 0.0 <= lo1 <= p1 <= hi1 <= 1.0
    print('self-test OK')


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        _self_test()
    else:
        main()
