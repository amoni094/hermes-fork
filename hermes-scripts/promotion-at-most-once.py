#!/usr/bin/env python3
"""promotion-at-most-once.py — Lynch at-most-once of SPRT PROMOTE.

A flag may be recorded as promoted at most once. Duplicate PROMOTE in the
decision stream is a coordination failure (two crons / replay).

Usage:
  python3 promotion-at-most-once.py --self-test
  python3 promotion-at-most-once.py
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
LEDGER = CACHE / 'promotion-ledger.json'
OUT = CACHE / 'promotion-at-most-once.json'


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def check(decisions: list[dict], ledger: dict) -> tuple[dict, dict]:
    promoted = dict(ledger.get('promoted') or {})
    dups = []
    new = []
    seen_this = set()
    for d in decisions:
        if d.get('decision') != 'PROMOTE':
            continue
        flag = str(d.get('flag') or '')
        if not flag:
            continue
        if flag in seen_this or flag in promoted:
            dups.append(flag)
        else:
            seen_this.add(flag)
            new.append(flag)
            promoted[flag] = {'ts': datetime.now(timezone.utc).isoformat()}
    report = {
        'n_new': len(new),
        'n_dup': len(dups),
        'dups': dups,
        'new': new,
        'alarm': len(dups) > 0,
        'theorem': 'Lynch at-most-once / put_if_absent on promotion',
    }
    return report, {'promoted': promoted}


def run() -> dict:
    decisions = []
    try:
        obj = json.loads((CACHE / 'shadow-sprt-decisions.json').read_text())
        decisions = list(obj.get('decisions') or [])
    except (OSError, json.JSONDecodeError):
        pass
    ledger = {}
    try:
        ledger = json.loads(LEDGER.read_text())
        if not isinstance(ledger, dict):
            ledger = {}
    except (OSError, json.JSONDecodeError):
        ledger = {}
    report, new_ledger = check(decisions, ledger)
    report['ts'] = datetime.now(timezone.utc).isoformat()
    try:
        _atomic_write(LEDGER, new_ledger)
        _atomic_write(OUT, report)
        report['output'] = str(OUT)
    except OSError as exc:
        report['write_error'] = str(exc)
    return report


def self_test() -> int:
    failures = []
    r, led = check([{'decision': 'PROMOTE', 'flag': 'a'}], {'promoted': {}})
    if r['alarm'] or r['n_new'] != 1:
        failures.append(str(r))
    r2, _ = check([{'decision': 'PROMOTE', 'flag': 'a'}], led)
    if not r2['alarm']:
        failures.append('dup missed')
    r3, _ = check([{'decision': 'PROMOTE', 'flag': 'x'}, {'decision': 'PROMOTE', 'flag': 'x'}], {'promoted': {}})
    if not r3['alarm']:
        failures.append('intra-batch dup')
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
    print(json.dumps({k: out.get(k) for k in ('n_new', 'n_dup', 'alarm', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
