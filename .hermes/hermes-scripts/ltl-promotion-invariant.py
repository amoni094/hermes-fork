#!/usr/bin/env python3
"""ltl-promotion-invariant.py — Clarke LTL G(PROMOTE -> failure_observable).

Model-checks the SPRT decision trace against the promotion safety formula.
Distinct from the handshake (which HOLDs); this is the checker that records
trace satisfaction for the ledger.

Usage:
  python3 ltl-promotion-invariant.py --self-test
  python3 ltl-promotion-invariant.py
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
OUT = CACHE / 'ltl-promotion-invariant.json'
MIN_CHARS = 20


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def model_check(decisions: list[dict]) -> dict:
    # G(PROMOTE -> FO)  iff  no state with PROMOTE and not FO
    violations = []
    for i, d in enumerate(decisions):
        if d.get('decision') != 'PROMOTE':
            continue
        fo = d.get('failure_observable')
        ok = isinstance(fo, str) and len(fo.strip()) > MIN_CHARS
        if not ok:
            violations.append({'index': i, 'flag': d.get('flag')})
    return {
        'formula': 'G(PROMOTE -> failure_observable)',
        'n_states': len(decisions),
        'n_violations': len(violations),
        'violations': violations,
        'satisfied': len(violations) == 0,
        'alarm': len(violations) > 0,
        'theorem': 'Clarke Model Checking LTL G(p->q) on SPRT trace',
    }


def run() -> dict:
    decisions = []
    try:
        obj = json.loads((CACHE / 'shadow-sprt-decisions.json').read_text())
        decisions = list(obj.get('decisions') or [])
    except (OSError, json.JSONDecodeError):
        pass
    # handshake holds are already non-PROMOTE in spirit; still check raw SPRT
    out = model_check(decisions)
    out['ts'] = datetime.now(timezone.utc).isoformat()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    r = model_check([{'decision': 'PROMOTE', 'flag': 'a'}])
    if r['satisfied'] or not r['alarm']:
        failures.append('bare PROMOTE should violate')
    r2 = model_check([{'decision': 'PROMOTE', 'flag': 'a',
                       'failure_observable': 'error_rate exceeds 10 percent for 3 days'}])
    if not r2['satisfied']:
        failures.append('FO should satisfy G')
    r3 = model_check([{'decision': 'CONTINUE'}])
    if not r3['satisfied']:
        failures.append('no PROMOTE => G holds vacuously')
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
    print(json.dumps({k: out.get(k) for k in ('satisfied', 'n_violations', 'alarm', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
