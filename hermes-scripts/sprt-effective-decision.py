#!/usr/bin/env python3
"""sprt-effective-decision.py — Merge SPRT + vetoes into one effective decision.

Raw SPRT PROMOTE is not executable if handshake HOLDs, truncation REJECTS,
inner/outer misaligns, or measurement tamper alarms. This is the file other
systems should read.

Priority (fail-closed): TAMPER > TRUNCATE_REJECT > HOLD_NO_FO > INNER_OUTER > SPRT.

Usage:
  python3 sprt-effective-decision.py --self-test
  python3 sprt-effective-decision.py
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
OUT = CACHE / 'sprt-effective-decision.json'


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _load(name: str) -> dict:
    try:
        obj = json.loads((CACHE / name).read_text())
        return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def merge(sprt: dict, handshake: dict, trunc: dict, inner: dict, tamper: dict) -> dict:
    tamper_on = bool(tamper.get('alarm'))
    hold_flags = {h.get('flag') for h in (handshake.get('holds') or [])}
    trunc_flags = {f.get('flag') for f in (trunc.get('forced') or [])}
    mesa_flags = {f.get('flag') for f in (inner.get('flags') or [])}
    out_decisions = []
    n_blocked = 0
    for d in sprt.get('decisions') or []:
        flag = d.get('flag')
        raw = d.get('decision')
        eff = raw
        reason = 'sprt'
        if tamper_on and raw == 'PROMOTE':
            eff, reason = 'HOLD', 'measurement_tamper'
        elif flag in trunc_flags:
            eff, reason = 'REJECT', 'truncated'
        elif flag in hold_flags:
            eff, reason = 'HOLD', 'no_failure_observable'
        elif flag in mesa_flags:
            eff, reason = 'HOLD', 'inner_outer_misaligned'
        if eff != raw:
            n_blocked += 1
        out_decisions.append({'flag': flag, 'raw': raw, 'effective': eff, 'reason': reason})
    n_promote = sum(1 for x in out_decisions if x['effective'] == 'PROMOTE')
    return {
        'decisions': out_decisions,
        'n_blocked': n_blocked,
        'n_effective_promote': n_promote,
        'alarm': n_blocked > 0,
        'theorem': 'Fail-closed composition of Wald + Popper + Hubinger + Hendrycks',
    }


def run() -> dict:
    out = merge(
        _load('shadow-sprt-decisions.json'),
        _load('sprt-falsifiability-handshake.json'),
        _load('sprt-truncation.json'),
        _load('sprt-inner-outer-alignment.json'),
        _load('sprt-measurement-tamper.json'),
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
    r = merge(
        {'decisions': [
            {'flag': 'a', 'decision': 'PROMOTE'},
            {'flag': 'b', 'decision': 'PROMOTE'},
            {'flag': 'c', 'decision': 'CONTINUE'},
        ]},
        {'holds': [{'flag': 'a'}]},
        {'forced': [{'flag': 'c'}]},
        {'flags': [{'flag': 'b'}]},
        {'alarm': False},
    )
    by = {x['flag']: x['effective'] for x in r['decisions']}
    if by['a'] != 'HOLD' or by['b'] != 'HOLD' or by['c'] != 'REJECT':
        failures.append(str(by))
    r2 = merge({'decisions': [{'flag': 'z', 'decision': 'PROMOTE'}]},
               {}, {}, {}, {'alarm': True})
    if r2['decisions'][0]['effective'] != 'HOLD':
        failures.append('tamper')
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
    print(json.dumps({k: out.get(k) for k in ('n_blocked', 'n_effective_promote', 'alarm', 'output')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
