#!/usr/bin/env python3
"""sprt-truncation-gate.py — Wald truncated SPRT (no infinite CONTINUE).

Open-ended SPRT can CONTINUE forever. At n >= N_max, decide by sign of LLR
but never PROMOTE on truncation (safety): LLR>=0 still REJECT if not past A.

Usage:
  python3 sprt-truncation-gate.py --self-test
  python3 sprt-truncation-gate.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT = CACHE / 'sprt-truncation.json'
N_MAX = 50
A = math.log(19.0)


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def truncate(decisions: list[dict], n_max: int = N_MAX) -> dict:
    forced = []
    for d in decisions:
        if d.get('decision') != 'CONTINUE':
            continue
        n = int(d.get('n') or d.get('n_obs') or 0)
        llr = float(d.get('llr') or 0.0)
        if n < n_max:
            continue
        # never promote on truncation
        forced.append({
            'flag': d.get('flag'),
            'n': n,
            'llr': llr,
            'forced': 'REJECT',
            'reason': 'truncated SPRT; PROMOTE forbidden on truncation',
        })
    return {
        'n_max': n_max,
        'n_truncated': len(forced),
        'forced': forced,
        'alarm': len(forced) > 0,
        'theorem': 'Wald truncated SPRT; fail-closed (no PROMOTE at N_max)',
    }


def run() -> dict:
    decisions = []
    try:
        obj = json.loads((CACHE / 'shadow-sprt-decisions.json').read_text())
        decisions = list(obj.get('decisions') or [])
    except (OSError, json.JSONDecodeError):
        pass
    out = truncate(decisions)
    out['ts'] = datetime.now(timezone.utc).isoformat()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    r = truncate([{'decision': 'CONTINUE', 'n': 8, 'llr': 1.0, 'flag': 'a'}])
    if r['alarm']:
        failures.append('short continue')
    r2 = truncate([{'decision': 'CONTINUE', 'n': 50, 'llr': 2.0, 'flag': 'b'}])
    if not r2['alarm'] or r2['forced'][0]['forced'] != 'REJECT':
        failures.append(str(r2))
    r3 = truncate([{'decision': 'PROMOTE', 'n': 80, 'llr': 5.0, 'flag': 'c'}])
    if r3['alarm']:
        failures.append('already promote not truncation')
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
    print(json.dumps({k: out.get(k) for k in ('n_truncated', 'alarm', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
