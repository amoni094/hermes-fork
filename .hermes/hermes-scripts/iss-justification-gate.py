#!/usr/bin/env python3
"""iss-justification-gate.py — ISS small-gain is only valid if passivity+sector hold.

Khalil Thm 9.x / Sontag: cascade/small-gain requires ISS subsystems. Saturated
PID is ISS only inside the circle-criterion sector and when the supply-rate
inequality holds. If composite Lyapunov+ISS+timescale is ok but passivity or
circle fail, overall_ok is unjustified.

Usage:
  python3 iss-justification-gate.py --self-test
  python3 iss-justification-gate.py
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
OUT = CACHE / 'iss-justification.json'


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def justify(composite: dict, passivity: dict, circle: dict, nyquist_bridge: dict) -> dict:
    lyap = bool(composite.get('overall_ok') or (
        composite.get('lyapunov_ok') and composite.get('iss_ok') and composite.get('two_timescale_ok')))
    # ADV21-013: missing prereq files => not justified (fail-closed)
    pas_missing = bool(passivity.get('_missing'))
    cir_missing = bool(circle.get('_missing'))
    nyq_missing = bool(nyquist_bridge.get('_missing'))
    composite_missing = bool(composite.get('_missing'))
    pas_ok = (not pas_missing) and (not bool(passivity.get('alarm')))
    cir_ok = (not cir_missing) and (not bool(circle.get('alarm')))
    nyq_ok = (not nyq_missing) and (not bool(nyquist_bridge.get('alarm')))
    lyap = (not composite_missing) and bool(composite.get('overall_ok'))
    justified = lyap and pas_ok and cir_ok and nyq_ok
    return {
        'composite_ok': lyap,
        'passivity_ok': pas_ok,
        'circle_ok': cir_ok,
        'nyquist_ok': nyq_ok,
        'justified_ok': justified,
        'alarm': lyap and not justified,
        'reason': None if justified else 'ISS composition not justified by passivity/sector/nyquist',
        'theorem': 'Khalil ISS small-gain requires ISS (passive, in-sector) subsystems',
    }


def _load(name: str) -> dict:
    """ADV21-013: missing file returns sentinel so justify() fails closed."""
    try:
        obj = json.loads((CACHE / name).read_text())
        return obj if isinstance(obj, dict) else {'_missing': True}
    except (OSError, json.JSONDecodeError):
        return {'_missing': True}


def run() -> dict:
    out = justify(
        _load('loop-stability-composite.json'),
        _load('pid-passivity-index.json'),
        _load('pid-circle-criterion.json'),
        _load('nyquist-timescale-bridge.json'),
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
    r = justify({'overall_ok': True}, {'alarm': False}, {'alarm': False}, {'alarm': False})
    if r['alarm'] or not r['justified_ok']:
        failures.append('all ok')
    r2 = justify({'overall_ok': True}, {'alarm': True}, {'alarm': False}, {'alarm': False})
    if not r2['alarm'] or r2['justified_ok']:
        failures.append('passivity should unjustify')
    r3 = justify({'overall_ok': False}, {'alarm': True}, {'alarm': True}, {'alarm': True})
    if r3['alarm']:
        failures.append('already-failed composite is not extra alarm')
    r4 = justify({'overall_ok': True}, {'_missing': True}, {'alarm': False}, {'alarm': False})
    if r4['justified_ok'] or not r4['alarm']:
        failures.append('missing passivity must fail closed')
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
    print(json.dumps({k: out.get(k) for k in ('justified_ok', 'alarm', 'reason', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
