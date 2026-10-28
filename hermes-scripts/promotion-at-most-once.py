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
from datetime import datetime, timezone, UTC
from pathlib import Path
import time

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
            promoted[flag] = {'ts': datetime.now(UTC).isoformat()}
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
    EFFECTIVE = CACHE / 'effective-shadow-decisions.json'
    SHADOW = CACHE / 'shadow-sprt-decisions.json'
    ts = datetime.now(UTC).isoformat()
    # WIRE-004: never fall back to raw SPRT. Skip if effective is missing or older than shadow.
    if not EFFECTIVE.exists():
        report = {
            'status': 'skipped',
            'reason': 'effective_not_ready',
            'ts': ts,
            'alarm': False,
            'n_new': 0,
            'n_dup': 0,
        }
        try:
            _atomic_write(OUT, report)
            report['output'] = str(OUT)
        except OSError as exc:
            report['write_error'] = str(exc)
        return report
    if SHADOW.exists() and EFFECTIVE.stat().st_mtime < SHADOW.stat().st_mtime:
        report = {
            'status': 'skipped',
            'reason': 'effective_not_ready',
            'ts': ts,
            'alarm': False,
            'n_new': 0,
            'n_dup': 0,
        }
        try:
            _atomic_write(OUT, report)
            report['output'] = str(OUT)
        except OSError as exc:
            report['write_error'] = str(exc)
        return report
    decisions = []
    try:
        decisions_raw = json.loads(EFFECTIVE.read_text())
        decisions = list(decisions_raw.get('decisions') or []) if isinstance(decisions_raw, dict) else []
    except (OSError, json.JSONDecodeError):
        report = {
            'status': 'skipped',
            'reason': 'effective_not_ready',
            'ts': ts,
            'alarm': False,
            'n_new': 0,
            'n_dup': 0,
        }
        try:
            _atomic_write(OUT, report)
            report['output'] = str(OUT)
        except OSError as exc:
            report['write_error'] = str(exc)
        return report
    ledger = {}
    try:
        ledger = json.loads(LEDGER.read_text())
        if not isinstance(ledger, dict):
            ledger = {}
    except (OSError, json.JSONDecodeError):
        ledger = {}
    report, new_ledger = check(decisions, ledger)
    report['ts'] = ts
    report['status'] = 'ok'
    try:
        _atomic_write(LEDGER, new_ledger)
        _atomic_write(OUT, report)
        report['output'] = str(OUT)
    except OSError as exc:
        report['write_error'] = str(exc)
    return report


def self_test() -> int:
    import tempfile
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
    global CACHE, LEDGER, OUT
    orig = (CACHE, LEDGER, OUT)
    try:
        td = Path(tempfile.mkdtemp())
        CACHE = td
        LEDGER = td / 'promotion-ledger.json'
        OUT = td / 'promotion-at-most-once.json'
        skipped = run()
        if skipped.get('status') != 'skipped' or skipped.get('reason') != 'effective_not_ready':
            failures.append(f'WIRE-004 missing effective: {skipped}')
        if LEDGER.exists():
            failures.append('WIRE-004 skip wrote ledger')
        # stale effective (mtime < shadow) also skips; never reads shadow content
        shadow = td / 'shadow-sprt-decisions.json'
        shadow.write_text(json.dumps({'decisions': [{'flag': 'raw', 'decision': 'PROMOTE'}]}), encoding='utf-8')
        eff = td / 'effective-shadow-decisions.json'
        eff.write_text(json.dumps({'decisions': [{'flag': 'eff', 'decision': 'PROMOTE'}]}), encoding='utf-8')
        os.utime(eff, (time.time() - 120, time.time() - 120))
        os.utime(shadow, (time.time(), time.time()))
        stale = run()
        if stale.get('status') != 'skipped' or stale.get('reason') != 'effective_not_ready':
            failures.append(f'WIRE-004 stale effective: {stale}')
    finally:
        CACHE, LEDGER, OUT = orig
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
    if out.get('status') == 'skipped':
        print(json.dumps({k: out.get(k) for k in ('status', 'reason', 'output')}))
        return 0
    print(json.dumps({k: out.get(k) for k in ('n_new', 'n_dup', 'alarm', 'output')}))
    # Alarm is a successful write of business-logic state; cron last_status=ok (ADV2-017).
    return 1 if out.get('write_error') else 0


if __name__ == '__main__':
    sys.exit(main())
