#!/usr/bin/env python3
"""
routing-weight-updater.py — FTRL routing weight feedback loop closure.

Reads routing-calibration.jsonl (written by memory-query-router.py via
_log_routing_decision), computes per-route success rates over the last 48h,
and applies an EMA (FTRL-style) weight update to routing-weights.json.

FTRL theory: w_{t+1} = argmin_w [sum loss_s(w) + R(w)]
EMA approximation: new_weight = old_weight * 0.9 + success_rate * 0.1
Reward signal: result_count > 0 (route returned at least one result)
Weights clamped to [0.1, 2.0].

Mirrors the pattern in calibration-threshold-updater.py (Shalev-Shwartz Ch 11).

Source: Memory in LLM Era v3 (arXiv:2604.01707) — bottleneck #2 closure.
"""
import json
import time
from pathlib import Path
from collections import defaultdict

import os as _os
_hermes_base = Path(_os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = _os.environ.get("HERMES_PROFILE", "")
_hermes_root = (_hermes_base / "profiles" / _hermes_profile) if _hermes_profile and "profiles" not in str(_hermes_base) else _hermes_base
LOG_PATH = _hermes_root / "cache" / "routing-calibration.jsonl"
WEIGHTS_PATH = _hermes_root / "cache" / "routing-weights.json"

WINDOW_SECONDS = 48 * 3600  # 48h lookback
WEIGHT_MIN = 0.1
WEIGHT_MAX = 2.0
EMA_DECAY = 0.9    # weight on prior run
EMA_NEW = 0.1     # weight on new observation
MIN_SAMPLES = 5   # minimum entries before updating (avoid noise from tiny samples)

_DEFAULT_ROUTES = ['semantic', 'temporal', 'relational', 'exact']


def _load_known_routes(weights_path: Path, log_path: Path) -> list:
    """Dynamic route discovery.

    Priority:
    1. Keys already present in routing-weights.json (persisted from prior runs).
    2. Fall back to _DEFAULT_ROUTES if the file is absent or unreadable.
    3. Any route key seen in the calibration log that is NOT yet known is
       zero-initialised (weight=0.0) so FTRL can learn from incoming data.
    """
    known: list = list(_DEFAULT_ROUTES)

    # 1. Seed from existing weights file
    if weights_path.exists():
        try:
            stored = json.loads(weights_path.read_text())
            if isinstance(stored, dict):
                for k in stored:
                    if k not in known:
                        known.append(k)
        except Exception:
            pass  # fall back to defaults

    # 2. Discover any new routes from the calibration log
    if log_path.exists():
        try:
            for line in log_path.read_text().splitlines():
                try:
                    row = json.loads(line)
                    route = row.get('route', '')
                    if route and route not in known:
                        known.append(route)
                except Exception:
                    continue
        except Exception:
            pass

    return known


def main():
    now = time.time()
    cutoff = now - WINDOW_SECONDS

    # ------------------------------------------------------------------ #
    # Discover known routes dynamically (replaces hardcoded KNOWN_ROUTES)
    # ------------------------------------------------------------------ #
    KNOWN_ROUTES = _load_known_routes(WEIGHTS_PATH, LOG_PATH)

    # ------------------------------------------------------------------ #
    # Load calibration log
    # ------------------------------------------------------------------ #
    route_stats = defaultdict(lambda: {'total': 0, 'successes': 0})

    if not LOG_PATH.exists():
        print('No routing calibration log found — using defaults')
    else:
        for line in LOG_PATH.read_text().splitlines():
            try:
                row = json.loads(line)
                ts = float(row.get('ts', 0))
                if ts < cutoff:
                    continue
                route = row.get('route', '')
                if not route:
                    continue
                result_count = int(row.get('result_count', -1))
                route_stats[route]['total'] += 1
                if result_count > 0:
                    route_stats[route]['successes'] += 1
            except Exception:
                continue

    # ------------------------------------------------------------------ #
    # Load existing weights (EMA seed from prior run)
    # ------------------------------------------------------------------ #
    existing_weights = {}
    try:
        if WEIGHTS_PATH.exists():
            existing_weights = json.loads(WEIGHTS_PATH.read_text())
    except Exception:
        pass

    # ------------------------------------------------------------------ #
    # FTRL-EMA update
    # ------------------------------------------------------------------ #
    updated_weights = {}
    summary_rows = []

    for route in KNOWN_ROUTES:
        stats = route_stats.get(route, {})
        n = stats.get('total', 0)
        successes = stats.get('successes', 0)

        # Routes present in defaults or weights file start at 1.0 if unseen;
        # routes discovered only from the calibration log are zero-initialised
        # so FTRL learns from evidence rather than assuming high quality.
        default_prior = 0.0 if route not in _DEFAULT_ROUTES and route not in existing_weights else 1.0
        prior = float(existing_weights.get(route, {}).get('weight', default_prior)
                      if isinstance(existing_weights.get(route), dict)
                      else existing_weights.get(route, default_prior))

        if n < MIN_SAMPLES:
            # Insufficient data — carry prior forward unchanged
            new_weight = prior
            success_rate = None
            note = f'n={n} < min_samples={MIN_SAMPLES}, prior kept'
        else:
            success_rate = successes / n
            # EMA: new = prior * 0.9 + success_rate * 0.1
            new_weight = prior * EMA_DECAY + success_rate * EMA_NEW
            # Clamp
            new_weight = max(WEIGHT_MIN, min(WEIGHT_MAX, new_weight))
            note = f'n={n}, success_rate={success_rate:.3f}'
            print(f'route={route}: weight={new_weight:.4f} ({note})')

        updated_weights[route] = {
            'weight': round(new_weight, 4),
            'n': n,
            'success_rate': round(success_rate, 3) if success_rate is not None else None,
            'ts': now,
            'note': note,
        }
        summary_rows.append({
            'route': route,
            'weight': round(new_weight, 4),
            'n': n,
            'success_rate': round(success_rate, 3) if success_rate is not None else None,
        })

    # ------------------------------------------------------------------ #
    # Write weights
    # ------------------------------------------------------------------ #
    try:
        WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _tmp_w = WEIGHTS_PATH.with_suffix('.tmp')
        _tmp_w.write_text(json.dumps(updated_weights, indent=2))
        _tmp_w.rename(WEIGHTS_PATH)
        print(f'Written: {WEIGHTS_PATH}')
    except Exception as e:
        print(f'ERROR writing weights: {e}')

    # ------------------------------------------------------------------ #
    # Print JSON summary (for cron delivery / stdout capture)
    # ------------------------------------------------------------------ #
    summary = {
        'ts': now,
        'window_hours': 48,
        'routes': summary_rows,
        'weights_path': str(WEIGHTS_PATH),
    }
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
