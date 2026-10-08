#!/usr/bin/env python3
"""sprt-inner-outer-alignment.py — Hubinger mesa: inner score vs outer error.

If a flag is SPRT-PROMOTE (inner optimiser looks good) while error_rate is
elevated but below the hard veto, treat as possible inner/outer misalignment.

Usage:
  python3 sprt-inner-outer-alignment.py --self-test
  python3 sprt-inner-outer-alignment.py
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
OUT = CACHE / 'sprt-inner-outer-alignment.json'
SOFT = 0.05  # below 0.10 veto, still concerning


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def check(decisions: list[dict]) -> dict:
    flags = []
    for d in decisions:
        if d.get('decision') != 'PROMOTE':
            continue
        er = d.get('error_rate')
        try:
            er_f = float(er)
        except (TypeError, ValueError):
            continue
        if er_f >= SOFT:
            flags.append({'flag': d.get('flag'), 'error_rate': er_f, 'decision': 'PROMOTE'})
    return {
        'n_promote': sum(1 for d in decisions if d.get('decision') == 'PROMOTE'),
        'n_misaligned': len(flags),
        'flags': flags,
        'alarm': len(flags) > 0,
        'theorem': 'Hubinger mesa-optimization: inner SPRT vs outer error_rate',
    }


def run() -> dict:
    decisions = []
    try:
        obj = json.loads((CACHE / 'shadow-sprt-decisions.json').read_text())
        decisions = list(obj.get('decisions') or [])
    except (OSError, json.JSONDecodeError):
        pass
    out = check(decisions)
    out['ts'] = datetime.now(timezone.utc).isoformat()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    r = check([{'decision': 'PROMOTE', 'flag': 'a', 'error_rate': 0.08}])
    if not r['alarm']:
        failures.append('soft error promote')
    r2 = check([{'decision': 'PROMOTE', 'flag': 'b', 'error_rate': 0.01}])
    if r2['alarm']:
        failures.append('low error should pass')
    r3 = check([{'decision': 'CONTINUE', 'error_rate': 0.09}])
    if r3['alarm']:
        failures.append('CONTINUE not mesa')
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
    print(json.dumps({k: out.get(k) for k in ('n_promote', 'n_misaligned', 'alarm', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
