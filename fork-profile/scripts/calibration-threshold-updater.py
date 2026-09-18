#!/usr/bin/env python3
"""Read calibration-log.jsonl and update Condorcet consistency thresholds.
Called by cron or manually. Implements calibration loop closure (ARCHITECTURE.md gap).
"""
import json
import time
from pathlib import Path
from collections import defaultdict

LOG_PATH = Path('~/.hermes/cache/calibration-log.jsonl').expanduser()
THRESH_PATH = Path('~/.hermes/cache/condorcet-thresholds.json').expanduser()


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
        thresholds[scope] = {
            'threshold': round(updated, 3),
            'observed_rate': round(observed_rate, 3),
            'n': n,
            'ts': time.time()
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
