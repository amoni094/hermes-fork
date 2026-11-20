#!/usr/bin/env python3
"""Allocate observation budget. Empty/malformed input is unmeasured."""
import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'observation-budget.json'
MAX_AGE = 8


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def decide_recheck(intent_age_gens, query_cost, invalidation_risk, max_age=MAX_AGE):
    if invalidation_risk is None or intent_age_gens is None or query_cost is None:
        return None
    try:
        age = float(intent_age_gens)
        cost = float(query_cost)
        risk = float(invalidation_risk)
    except (TypeError, ValueError):
        return None
    if age >= max_age:
        return True
    return (age * risk) > cost


def allocate_budget(intents, total_budget: float) -> dict:
    if intents is None or not isinstance(intents, (list, tuple)) or len(intents) == 0:
        return {
            'generated_at': datetime.now(UTC).isoformat(),
            'status': 'insufficient_data',
            'n': 0,
            'allocations': [],
            'total_budget': total_budget,
        }
    scored = []
    for it in intents:
        if not isinstance(it, dict):
            continue
        name = it.get('name') or it.get('id') or 'intent'
        age = it.get('age', it.get('intent_age_gens'))
        cost = it.get('cost', it.get('query_cost'))
        risk = it.get('risk', it.get('invalidation_risk'))
        rec = decide_recheck(age, cost, risk)
        if rec is None:
            continue
        scored.append({'name': name, 'recheck': rec, 'age': age, 'cost': cost, 'risk': risk})
    if not scored:
        return {
            'generated_at': datetime.now(UTC).isoformat(),
            'status': 'insufficient_data',
            'n': 0,
            'allocations': [],
            'total_budget': total_budget,
        }
    rechecks = [s for s in scored if s['recheck'] is True]
    n = len(rechecks) or len(scored)
    share = float(total_budget) / n if n else 0.0
    alloc = []
    for s in scored:
        s = dict(s)
        s['budget'] = round(share if s['recheck'] else 0.0, 6)
        alloc.append(s)
    return {
        'generated_at': datetime.now(UTC).isoformat(),
        'status': 'ok',
        'n': len(alloc),
        'allocations': alloc,
        'total_budget': total_budget,
    }


def self_test() -> dict:
    assert decide_recheck(None, 1, 1) is None
    assert decide_recheck(9, 1, 0.1) is True
    empty = allocate_budget(None, 10)
    assert empty['status'] == 'insufficient_data' and empty['n'] == 0
    bad = allocate_budget('not-a-list', 10)
    assert bad['status'] == 'insufficient_data'
    r = allocate_budget(
        [{'name': 'a', 'age': 9, 'cost': 1, 'risk': 0.5}, {'name': 'b', 'age': 1, 'cost': 5, 'risk': 0.1}],
        10,
    )
    assert r['status'] == 'ok' and r['n'] == 2
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    _atomic_write(tmp, r)
    try:
        assert tmp.exists()
    finally:
        tmp.unlink(missing_ok=True)
    return {'self_test': 'PASS', 'sample': r}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--json', default='')
    ap.add_argument('--budget', type=float, default=10.0)
    args = ap.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2))
        sys.exit(0)
    try:
        raw = args.json
        if not raw and not sys.stdin.isatty():
            raw = sys.stdin.read()
        intents = []
        if raw:
            try:
                obj = json.loads(raw)
                intents = obj if isinstance(obj, list) else obj.get('intents') or obj.get('observations') or []
            except json.JSONDecodeError:
                intents = []
        r = allocate_budget(intents, args.budget)
        if r.get('status') != 'insufficient_data':
            try:
                _atomic_write(OUT_PATH, r)
            except Exception:
                pass
        print(json.dumps(r, indent=2))
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e)}))
        sys.exit(0)


if __name__ == '__main__':
    main()
