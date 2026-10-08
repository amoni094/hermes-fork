#!/usr/bin/env python3
"""governance-conflict-epistemic.py — TYPE_A is not common knowledge of DENY.

Fagin/Halpern/Moses/Vardi: if auth-gate believes ALLOW and hard-block believes
DENY, neither K(allowed) nor C(denied) holds. Log a B-type (belief) annotation
and an epistemic regression event. Shoham: joint intention is broken.

Usage:
  python3 governance-conflict-epistemic.py --self-test
  python3 governance-conflict-epistemic.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT = CACHE / 'governance-conflict-epistemic.json'
REGRESS = CACHE / 'epistemic-regressions.jsonl'


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def annotate(conflicts: list[dict]) -> dict:
    events = []
    for c in conflicts:
        ctype = c.get('type') or c.get('conflict_type')
        key = c.get('key') or c.get('tool') or '?'
        if ctype == 'CONFLICT_TYPE_A':
            events.append({
                'domain': f'tool:{key}:allowed',
                'from_type': 'K',
                'to_type': 'B',
                'reason': 'TYPE_A: auth ALLOW vs hard-block DENY; K(allowed) false, C(denied) false',
                'common_knowledge': False,
                'distributed_knowledge': True,
            })
        elif ctype == 'CONFLICT_TYPE_B':
            events.append({
                'domain': f'tool:{key}:denied',
                'from_type': 'K',
                'to_type': 'B',
                'reason': 'TYPE_B: auth DENY vs hard-block ALLOW; principals disagree',
                'common_knowledge': False,
                'distributed_knowledge': True,
            })
    return {
        'n_conflicts': len(conflicts),
        'n_regressions': len(events),
        'events': events,
        'alarm': any(not e['common_knowledge'] for e in events),
        'theorem': 'Fagin S5: C requires agreement; Shoham joint intention fails on TYPE_A/B',
    }


def run() -> dict:
    conflicts = []
    p = CACHE / 'governance-conflicts.jsonl'
    try:
        for line in p.read_text(encoding='utf-8').splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                conflicts.append(obj)
    except OSError:
        pass
    summary = _load_summary()
    if not conflicts and summary.get('most_recent'):
        conflicts = [summary['most_recent']]
    out = annotate(conflicts)
    out['ts'] = datetime.now(timezone.utc).isoformat()
    now = time.time()
    try:
        REGRESS.parent.mkdir(parents=True, exist_ok=True)
        with open(REGRESS, 'a', encoding='utf-8') as fh:
            for e in out['events']:
                fh.write(json.dumps({'ts': now, **e}) + '\n')
    except OSError:
        pass
    try:
        _atomic_write(OUT, out)
        out['output'] = str(OUT)
    except OSError as exc:
        out['write_error'] = str(exc)
    return out


def _load_summary() -> dict:
    try:
        obj = json.loads((CACHE / 'governance-conflict-summary.json').read_text())
        return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def self_test() -> int:
    failures = []
    r = annotate([{'type': 'CONFLICT_TYPE_A', 'key': 'write_file'}])
    if not r['alarm'] or r['n_regressions'] != 1 or r['events'][0]['common_knowledge']:
        failures.append(str(r))
    r2 = annotate([])
    if r2['alarm']:
        failures.append('empty should not alarm')
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
    print(json.dumps({k: out.get(k) for k in ('n_conflicts', 'n_regressions', 'alarm', 'output')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
