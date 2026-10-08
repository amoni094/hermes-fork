#!/usr/bin/env python3
"""nyquist-timescale-bridge.py — Consistency of Nyquist aliasing vs two-timescale.

Vetterli/Nyquist: jobs with T > 1/(2B) alias. Khalil Ch 11: T_slow/T_fast >= 10.
Contradiction: two-timescale reports ok (hooks vs memory well separated) WHILE
Nyquist reports aliased cron jobs (slow sampling of a wideband process). That
is a false sense of timescale health — memory jobs can still alias.

Usage:
  python3 nyquist-timescale-bridge.py --self-test
  python3 nyquist-timescale-bridge.py
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

OUT_PATH = _hermes_root / 'cache' / 'nyquist-timescale-bridge.json'


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _load(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
        return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def compose(nyquist: dict, timescale: dict) -> dict:
    n_aliased = int(nyquist.get('n_aliased') or 0)
    ts_ok = bool(timescale.get('ok', False)) if timescale else False
    contradiction = bool(nyquist) and bool(timescale) and ts_ok and n_aliased > 0
    missing = not nyquist or not timescale
    return {
        'ts': datetime.now(timezone.utc).isoformat(),
        'theorem': 'Nyquist fs>=2B vs Khalil two-time-scale; contradiction => false health',
        'nyquist_n_aliased': n_aliased,
        'two_timescale_ok': ts_ok,
        'contradiction': contradiction,
        'missing_input': missing,
        'alarm': contradiction,
        'note': (
            'two-timescale ok AND aliased jobs: memory period still undersamples '
            'the context-pressure bandwidth'
            if contradiction else
            ('missing nyquist or two-timescale cache' if missing else 'consistent')
        ),
    }


def run() -> dict:
    ny = _load(_hermes_root / 'cache' / 'nyquist-bandwidth.json')
    if not ny:
        ny = _load(_hermes_base / 'cache' / 'nyquist-bandwidth.json')
    ts = _load(_hermes_root / 'cache' / 'two-timescale.json')
    if not ts:
        ts = _load(_hermes_base / 'cache' / 'two-timescale.json')
    out = compose(ny, ts)
    try:
        _atomic_write(OUT_PATH, out)
        out['output'] = str(OUT_PATH)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    c = compose({'n_aliased': 3}, {'ok': True})
    if not c['contradiction'] or not c['alarm']:
        failures.append('aliased+ok should contradict')
    c2 = compose({'n_aliased': 0}, {'ok': True})
    if c2['contradiction']:
        failures.append('clean should not contradict')
    c3 = compose({}, {})
    if not c3['missing_input'] or c3['alarm']:
        failures.append('missing should not alarm')
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
    print(json.dumps({k: out.get(k) for k in (
        'nyquist_n_aliased', 'two_timescale_ok', 'contradiction', 'alarm', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
