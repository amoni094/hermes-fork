#!/usr/bin/env python3
"""Read context pressure JSONL and determine if reduction is needed.
ARCHITECTURE.md TIER 2 gap #6: pressure_flag is logged but never acted on.
This script reads the last N pressure entries and returns actionable status.
"""
import json
from pathlib import Path


def get_pressure_status() -> dict:
    """Read pressure log and return consecutive HIGH count + should_reduce flag."""
    try:
        cache_dir = Path('~/.hermes/cache').expanduser()
        candidates = (
            list(cache_dir.glob('*pressure*.jsonl'))
            + list(cache_dir.glob('turn_usage*.jsonl'))
            + list(cache_dir.glob('*turn*usage*.jsonl'))
        )
        if not candidates:
            return {'consecutive_high': 0, 'should_reduce': False, 'source': 'no_log'}
        log_path = sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]
        lines = log_path.read_text().splitlines()[-10:]
        consecutive = 0
        for line in reversed(lines):
            try:
                row = json.loads(line)
                pf = row.get('pressure_flag') or row.get('pressure') or ''
                if str(pf).upper() == 'HIGH':
                    consecutive += 1
                else:
                    break
            except Exception:
                break
        return {
            'consecutive_high': consecutive,
            'should_reduce': consecutive >= 3,
            'source': str(log_path),
        }
    except Exception as e:
        return {'consecutive_high': 0, 'should_reduce': False, 'error': str(e)}


def main() -> None:
    status = get_pressure_status()
    if status.get('should_reduce'):
        n = status['consecutive_high']
        print(f'PRESSURE ALERT: {n} consecutive HIGH pressure turns - context reduction recommended')
    else:
        n = status.get('consecutive_high', 0)
        print(f'Pressure OK: {n} consecutive HIGH turns (threshold=3)')


if __name__ == '__main__':
    main()
