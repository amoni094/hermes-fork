#!/usr/bin/env python3
"""Read calibration-log.jsonl and update Condorcet consistency thresholds.
Called by cron or manually. Implements calibration loop closure (ARCHITECTURE.md gap).
"""
import json
import time
from pathlib import Path
from collections import defaultdict

import os as _os
_hermes_base = Path(_os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = _os.environ.get("HERMES_PROFILE", "")
_hermes_root = (_hermes_base / "profiles" / _hermes_profile) if _hermes_profile and "profiles" not in str(_hermes_base) else _hermes_base
LOG_PATH = _hermes_root / "cache" / "calibration-log.jsonl"
THRESH_PATH = _hermes_root / "cache" / "condorcet-thresholds.json"
CAL_MAP_PATH = _hermes_root / "cache" / "calibration-map.json"
_CAL_MAP_MAX_AGE_S = 86400  # 24 hours


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




# CausalEMA advisory (Pearl Ch.3 back-door adjustment)
# Wired from causal_ema.py — stratum-aware EMA deconfounds session-type bias.
# Currently advisory only: writes causal_threshold to the output but doesn't override 'threshold'.


def _bayesian_threshold(agreements: int, n: int, alpha_prior: float = 1.0, beta_prior: float = 1.0) -> float:
    """Beta-Binomial posterior mean for calibration threshold.

    Theoretical basis: Gelman et al. BDA3 §2.4 (Beta-Binomial conjugate).
    After k agreements in n trials with Beta(alpha, beta) prior:
        posterior_mean = (alpha + k) / (alpha + beta + n)

    Default prior: Beta(1,1) = uniform (no prior knowledge).
    Vs. raw EMA: Beta-Binomial is conservative for small n
        (3/3 raw = 1.0 vs 4/5 Bayesian = 0.8 — avoids 100% confidence from 3 samples).

    Returns float in (0, 1).
    """
    return (alpha_prior + agreements) / (alpha_prior + beta_prior + n)

def _causal_ema_advisory(scope_stats: dict, existing_thresholds: dict) -> dict:
    """Compute Simpson-safe causal EMA per scope, advisory only.

    Reference: causal_ema.py (Pearl Ch.3 back-door criterion).
    Stratifies by session type (tool_heavy vs message_heavy) using
    scope as a proxy (L2=factual → message_heavy, L3=code → tool_heavy).
    """
    ALPHA = 0.15
    scope_stratum = {'L2': 'message_heavy', 'L3': 'tool_heavy', 'L1': 'message_heavy'}
    # Build per-stratum observations
    stratum_obs: dict = {'tool_heavy': [], 'message_heavy': []}
    for scope, stats in scope_stats.items():
        stratum = scope_stratum.get(scope, 'message_heavy')
        n = stats['total']
        if n >= 5:
            rate = stats['agreements'] / n
            stratum_obs[stratum].append(rate)
    # Per-stratum EMA (simple: mean of observations as update signal)
    stratum_ema = {}
    for stratum, rates in stratum_obs.items():
        if rates:
            stratum_mean = sum(rates) / len(rates)
            # Seed from existing (stored under causal_ema_ key)
            prior_key = f'causal_ema_{stratum}'
            prior = existing_thresholds.get(prior_key, stratum_mean)
            stratum_ema[stratum] = prior + ALPHA * (stratum_mean - prior)
        else:
            stratum_ema[stratum] = existing_thresholds.get(f'causal_ema_{stratum}', 0.5)
    # Back-door adjustment: count-weighted average
    total = sum(len(v) for v in stratum_obs.values())
    if total > 0:
        adjusted = sum(
            stratum_ema[s] * (len(stratum_obs[s]) / total)
            for s in stratum_ema
        )
    else:
        adjusted = 0.5
    return {
        'causal_threshold': round(adjusted, 3),
        'stratum_ema': {k: round(v, 3) for k, v in stratum_ema.items()},
        'causal_ema_tool_heavy': round(stratum_ema.get('tool_heavy', 0.5), 3),
        'causal_ema_message_heavy': round(stratum_ema.get('message_heavy', 0.5), 3),
    }

def main():
    if not LOG_PATH.exists():
        print('No calibration log found - writing default thresholds')
        # Write defaults so downstream tools (consistency_scorer, staleness-monitor) have a file to read
        _default = {
            "L2": {"threshold": 0.6, "ci_lower": 0.5, "ci_upper": 0.7, "n": 0},
            "L3": {"threshold": 0.7, "ci_lower": 0.6, "ci_upper": 0.8, "n": 0},
        }
        THRESH_PATH.parent.mkdir(parents=True, exist_ok=True)
        _tmp = THRESH_PATH.with_suffix('.tmp')
        _tmp.write_text(json.dumps(_default, indent=2))
        _tmp.rename(THRESH_PATH)
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
        bayesian_thresh = _bayesian_threshold(stats['agreements'], n)
        thresholds[scope] = {
            'threshold': round(updated, 3),
            'bayesian_threshold': round(bayesian_thresh, 3),
            'observed_rate': round(observed_rate, 3),
            'n': n,
            'ts': time.time(),
            'clamped_by_cal_map': clamped_by_cal_map,
        }
        print(f'scope={scope}: threshold={updated:.3f} (observed={observed_rate:.2f}, n={n})')

    # Annotate output with causal EMA advisory (Pearl back-door adjustment)
    try:
        causal_advisory = _causal_ema_advisory(scope_stats, existing_thresholds)
        for scope in thresholds:
            thresholds[scope].update({
                'causal_threshold': causal_advisory['causal_threshold'],
                'causal_stratum_ema': causal_advisory['stratum_ema'],
            })
        # Persist stratum EMA state for next run
        for stratum in ('tool_heavy', 'message_heavy'):
            existing_thresholds[f'causal_ema_{stratum}'] = causal_advisory[f'causal_ema_{stratum}']
        print(f"[CausalEMA] adjusted={causal_advisory['causal_threshold']:.3f} "
              f"strata={causal_advisory['stratum_ema']}")
    except Exception as _ce:
        print(f"[CausalEMA] advisory failed (ignored): {_ce}")

    THRESH_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Persist causal EMA stratum state (A-08 fix): merge into output so it survives across runs.
    # Stored under "_causal_state" key; re-loaded into existing_thresholds on next run.
    _causal_state_keys = {k: v for k, v in existing_thresholds.items() if k.startswith('causal_ema_')}
    if _causal_state_keys:
        thresholds['_causal_state'] = _causal_state_keys
    # M7 fix: atomic write via tmp+rename to prevent Condorcet threshold corruption
    _thresh_tmp = THRESH_PATH.with_suffix('.tmp')
    _thresh_tmp.write_text(json.dumps(thresholds, indent=2))
    _thresh_tmp.rename(THRESH_PATH)
    print(f'Written: {THRESH_PATH}')


if __name__ == '__main__':
    main()
