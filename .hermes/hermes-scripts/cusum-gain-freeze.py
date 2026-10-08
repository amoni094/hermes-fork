#!/usr/bin/env python3
"""cusum-gain-freeze.py — Liberzon: freeze PID gains after CUSUM.

If Page CUSUM alarms a mean shift, continuing to integrate with the old
gains is unsafe. Recommend freeze (no Ki update) until retune.

Usage:
  python3 cusum-gain-freeze.py --self-test
  python3 cusum-gain-freeze.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT = CACHE / 'cusum-gain-freeze.json'


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def decide(cusum_alarm: bool, passivity_alarm: bool, circle_alarm: bool) -> dict:
    freeze = bool(cusum_alarm or passivity_alarm or circle_alarm)
    return {
        'cusum_alarm': cusum_alarm,
        'passivity_alarm': passivity_alarm,
        'circle_alarm': circle_alarm,
        'freeze_ki': freeze,
        'freeze_kp': cusum_alarm,
        'recommendation': 'freeze_gains' if freeze else 'gains_live',
        'alarm': freeze,
        'theorem': 'Liberzon optimal control: freeze integrator after detected plant change',
    }


def _alarm(name: str) -> bool:
    try:
        obj = json.loads((CACHE / name).read_text())
        return bool(obj.get('alarm'))
    except (OSError, json.JSONDecodeError):
        return False


def run() -> dict:
    out = decide(
        _alarm('loop-cusum-changepoint.json'),
        _alarm('pid-passivity-index.json'),
        _alarm('pid-circle-criterion.json'),
    )
    out['ts'] = datetime.now(timezone.utc).isoformat()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    r = decide(False, False, False)
    if r['alarm'] or r['freeze_ki']:
        failures.append('quiet')
    r2 = decide(True, False, False)
    if not r2['freeze_ki'] or not r2['freeze_kp']:
        failures.append('cusum freeze')
    r3 = decide(False, True, False)
    if not r3['freeze_ki'] or r3['freeze_kp']:
        failures.append('passivity freezes Ki only')
    if failures:
        print(json.dumps({'self_test': 'FAIL', 'failures': failures}))
        return 1
    print(json.dumps({'self_test': 'PASS'}))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    out = run()
    print(json.dumps({k: out.get(k) for k in ('recommendation', 'freeze_ki', 'freeze_kp', 'alarm', 'output')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
