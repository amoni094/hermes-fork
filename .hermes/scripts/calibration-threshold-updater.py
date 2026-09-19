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
            'ts': time.time(),
            'clamped_by_cal_map': clamped_by_cal_map,
        }
        print(f'scope={scope}: threshold={updated:.3f} (observed={observed_rate:.2f}, n={n})')

    THRESH_PATH.parent.mkdir(parents=True, exist_ok=True)
    # M7 fix: atomic write via tmp+rename to prevent Condorcet threshold corruption
    _thresh_tmp = THRESH_PATH.with_suffix('.tmp')
    _thresh_tmp.write_text(json.dumps(thresholds, indent=2))
    _thresh_tmp.rename(THRESH_PATH)
    print(f'Written: {THRESH_PATH}')


if __name__ == '__main__':
    main()
