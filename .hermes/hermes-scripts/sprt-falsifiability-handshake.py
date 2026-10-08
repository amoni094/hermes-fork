#!/usr/bin/env python3
"""sprt-falsifiability-handshake.py — PROMOTE requires failure_observable.

Clarke LTL: G(PROMOTE → failure_observable). Critch/Popper: a promotion
without a falsifier is unfalsifiable self-modification.

Reads cache/shadow-sprt-decisions.json + improvement-proposals.jsonl.
Any SPRT PROMOTE whose flag has no non-trivial failure_observable is
downgraded to HOLD and alarmed.

Usage:
  python3 sprt-falsifiability-handshake.py --self-test
  python3 sprt-falsifiability-handshake.py
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
OUT = CACHE / 'sprt-falsifiability-handshake.json'
MIN_CHARS = 20


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


def _proposals() -> list[dict]:
    rows = []
    for p in (
        _hermes_base / 'logs' / 'improvement-proposals.jsonl',
        _hermes_root / 'logs' / 'improvement-proposals.jsonl',
    ):
        try:
            text = p.read_text(encoding='utf-8')
        except OSError:
            continue
        for line in text.splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def observable_ok(text) -> bool:
    return isinstance(text, str) and len(text.strip()) > MIN_CHARS


def handshake(decisions: list[dict], proposals: list[dict]) -> dict:
    by_target: dict[str, dict] = {}
    for rec in proposals:
        key = str(rec.get('target') or rec.get('flag') or rec.get('id') or '')
        if key:
            by_target[key] = rec
    holds = []
    ok_promotes = []
    for d in decisions:
        if d.get('decision') != 'PROMOTE':
            continue
        flag = str(d.get('flag') or '')
        rec = by_target.get(flag) or {}
        fo = rec.get('failure_observable') or d.get('failure_observable')
        if observable_ok(fo):
            ok_promotes.append(flag)
        else:
            holds.append({'flag': flag, 'reason': 'PROMOTE without failure_observable'})
    return {
        'n_promote': sum(1 for d in decisions if d.get('decision') == 'PROMOTE'),
        'n_hold': len(holds),
        'n_ok': len(ok_promotes),
        'holds': holds,
        'ok_promotes': ok_promotes,
        'alarm': len(holds) > 0,
        'theorem': 'Clarke G(PROMOTE -> FO); Popper/Critch falsifiability',
    }


def run() -> dict:
    sprt = _load(CACHE / 'shadow-sprt-decisions.json')
    out = handshake(sprt.get('decisions') or [], _proposals())
    out['ts'] = datetime.now(timezone.utc).isoformat()
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def self_test() -> int:
    failures = []
    r = handshake(
        [{'flag': 'x', 'decision': 'PROMOTE'},
         {'flag': 'y', 'decision': 'PROMOTE', 'failure_observable': 'mean_score below 3.0 for seven days'}],
        [{'target': 'x'}],
    )
    if not r['alarm'] or r['n_hold'] != 1 or 'y' not in r['ok_promotes']:
        failures.append(str(r))
    r2 = handshake([{'flag': 'z', 'decision': 'CONTINUE'}], [])
    if r2['alarm']:
        failures.append('CONTINUE should not alarm')
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
    print(json.dumps({k: out.get(k) for k in ('n_promote', 'n_hold', 'n_ok', 'alarm', 'output')}))
    return 1 if out.get('alarm') else 0


if __name__ == '__main__':
    sys.exit(main())
