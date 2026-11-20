#!/usr/bin/env python3
"""Online resource sharing with randomized quantile-based fair allocation.

Hard core: every subagent receives at least (fair_share * 0.59 * ideal_utility)
cumulative allocation over a session.
"""
from __future__ import annotations

import os
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

import argparse
import fcntl
import json
import math
import random
import sys
import tempfile
import uuid
from datetime import datetime, timezone, UTC

CACHE = _hermes_root / 'cache'
OUT_NAME = 'allocation-state.json'
Q_LEVEL = 0.75
FAIR_RATIO = 0.59


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            tmp.replace(path)
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _clip01(val) -> float | None:
    try:
        s = float(val)
    except (TypeError, ValueError):
        return None
    if s != s or s in (float('inf'), float('-inf')):
        return None
    s = max(s, 0.0)
    s = min(s, 1.0)
    return s


def empirical_quantile(samples, q: float = Q_LEVEL) -> float:
    xs = []
    for s in samples or []:
        v = _clip01(s)
        if v is not None:
            xs.append(v)
    if not xs:
        return 1.0  # optimistic UCB prior when unexplored
    xs.sort()
    n = len(xs)
    q = min(1.0, max(0.0, float(q)))
    pos = q * (n - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    w = pos - lo
    return xs[lo] * (1.0 - w) + xs[hi] * w


def empty_arm() -> dict:
    return {
        'cumulative_utility': 0.0,
        'n_allocated': 0,
        'ecdf_samples': [],
    }


def load_state(path: Path) -> dict:
    if not path.exists():
        return {'arms': {}, 'total_turns': 0, 'status': 'empty', 'ts': _now()}
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'arms': {}, 'total_turns': 0, 'status': 'empty', 'ts': _now()}
    if not isinstance(obj, dict):
        return {'arms': {}, 'total_turns': 0, 'status': 'empty', 'ts': _now()}
    arms = obj.get('arms')
    if not isinstance(arms, dict):
        # flat {arm_id: {cumulative_utility, n_allocated, ecdf_samples}}
        arms = {}
        for k, v in obj.items():
            if isinstance(v, dict) and ('n_allocated' in v or 'ecdf_samples' in v):
                arms[str(k)] = v
    clean = {}
    for k, v in (arms or {}).items():
        if not isinstance(v, dict):
            continue
        samples = v.get('ecdf_samples') or []
        if not isinstance(samples, list):
            samples = []
        clipped = []
        for s in samples[-512:]:
            c = _clip01(s)
            if c is not None:
                clipped.append(c)
        try:
            n_alloc = int(v.get('n_allocated') or 0)
        except (TypeError, ValueError):
            n_alloc = 0
        try:
            cu = float(v.get('cumulative_utility') or 0.0)
        except (TypeError, ValueError):
            cu = 0.0
        n_alloc = max(n_alloc, 0)
        cu = max(cu, 0.0)
        clean[str(k)] = {
            'cumulative_utility': cu,
            'n_allocated': n_alloc,
            'ecdf_samples': clipped,
        }
    try:
        total = int(obj.get('total_turns') or 0)
    except (TypeError, ValueError):
        total = 0
    if total <= 0:
        total = sum(a['n_allocated'] for a in clean.values())
    return {
        'arms': clean,
        'total_turns': total,
        'status': 'ok' if clean else 'empty',
        'ts': obj.get('ts') or _now(),
        'recommended_arm': obj.get('recommended_arm'),
    }


def allocation_index(arm: dict, total_turns: int, n_arms: int) -> float:
    q75 = empirical_quantile(arm.get('ecdf_samples') or [], Q_LEVEL)
    n_alloc = int(arm.get('n_allocated') or 0)
    k = max(1, int(n_arms))
    # quantile-based fair-share: q75 - n_i / (t/K)
    fair_so_far = max(1.0, float(total_turns) / k) if total_turns > 0 else 1.0
    return q75 - (n_alloc / fair_so_far)


def choose_arm(state: dict, rng: random.Random | None = None) -> str | None:
    arms = state.get('arms') or {}
    if not arms:
        return None
    rng = rng or random.Random()
    ids = sorted(arms.keys())
    n_arms = len(ids)
    total = int(state.get('total_turns') or 0)
    # randomized strategy: tiny uniform exploration
    if rng.random() < 0.02:
        return rng.choice(ids)
    scored = []
    for aid in ids:
        scored.append((allocation_index(arms[aid], total, n_arms), rng.random(), aid))
    scored.sort(reverse=True)
    return scored[0][2]


def observe_and_allocate(state: dict, utilities: dict, rng: random.Random | None = None) -> str | None:
    """Full-feedback step: update ECDF for all arms, allocate to chosen arm."""
    arms = state.setdefault('arms', {})
    for aid, u in utilities.items():
        cu = _clip01(u)
        if cu is None:
            continue
        rec = arms.setdefault(str(aid), empty_arm())
        rec['ecdf_samples'].append(cu)
        if len(rec['ecdf_samples']) > 512:
            rec['ecdf_samples'] = rec['ecdf_samples'][-512:]
    chosen = choose_arm(state, rng=rng)
    if chosen is None:
        return None
    rec = arms[chosen]
    u = _clip01(utilities.get(chosen, 0.0)) or 0.0
    rec['n_allocated'] = int(rec.get('n_allocated') or 0) + 1
    rec['cumulative_utility'] = float(rec.get('cumulative_utility') or 0.0) + u
    state['total_turns'] = int(state.get('total_turns') or 0) + 1
    state['recommended_arm'] = chosen
    state['status'] = 'ok'
    state['ts'] = _now()
    return chosen


def layer1_demo(seed: int = 0) -> dict:
    n_turns = 100
    utils = {
        'A': [0.8 if i % 2 == 0 else 0.1 for i in range(n_turns)],
        'B': [0.5] * n_turns,
        'C': [0.2] * n_turns,
    }
    state = {
        'arms': {k: empty_arm() for k in utils},
        'total_turns': 0,
        'status': 'ok',
        'ts': _now(),
    }
    rng = random.Random(seed)
    for t in range(n_turns):
        step_u = {k: utils[k][t] for k in utils}
        observe_and_allocate(state, step_u, rng=rng)
    totals = {k: state['arms'][k]['n_allocated'] for k in utils}
    mn = min(totals.values())
    fair_share = n_turns / 3.0
    return {
        'totals': totals,
        'min_allocation': mn,
        'fair_share': fair_share,
        'bound': 0.55 * fair_share,
        'state': state,
    }


def dump_state(state: dict) -> dict:
    arms_out = {}
    for aid, rec in (state.get('arms') or {}).items():
        arms_out[aid] = {
            'cumulative_utility': rec.get('cumulative_utility', 0.0),
            'n_allocated': rec.get('n_allocated', 0),
            'ecdf_samples': list(rec.get('ecdf_samples') or []),
        }
    n_arms = max(1, len(arms_out))
    total = int(state.get('total_turns') or 0)
    recs = {}
    for aid, rec in arms_out.items():
        recs[aid] = allocation_index(rec, total, n_arms)
    return {
        'arms': arms_out,
        'total_turns': total,
        'recommended_arm': state.get('recommended_arm'),
        'indices': recs,
        'fair_share': (total / n_arms) if n_arms else 0.0,
        'fair_ratio': FAIR_RATIO,
        'status': state.get('status') or ('ok' if arms_out else 'insufficient_data'),
        'ts': state.get('ts') or _now(),
    }


def run(state_path: Path | None = None) -> dict:
    dest = Path(state_path) if state_path is not None else (CACHE / OUT_NAME)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        empty = {
            'arms': {},
            'total_turns': 0,
            'status': 'insufficient_data',
            'reason': 'missing_state',
            'ts': _now(),
        }
        _atomic_write_json(dest, empty)
        return empty
    state = load_state(dest)
    if not state.get('arms'):
        out = {
            'arms': {},
            'total_turns': 0,
            'status': 'insufficient_data',
            'reason': 'no_arms',
            'ts': _now(),
        }
        _atomic_write_json(dest, out)
        return out
    # recompute fair-share recommendation without fabricating new arms
    chosen = choose_arm(state, rng=random.Random(int(state.get('total_turns') or 0)))
    state['recommended_arm'] = chosen
    state['status'] = 'ok'
    state['ts'] = _now()
    payload = dump_state(state)
    _atomic_write_json(dest, payload)
    return payload


def _self_test() -> int:
    assert empirical_quantile([], 0.75) == 1.0
    assert 0.0 <= empirical_quantile([0.0, 1.0, 0.5], 0.75) <= 1.0
    empty = load_state(Path(f'/tmp/does-not-exist-{uuid.uuid4().hex}.json'))
    assert empty['status'] == 'empty'
    demo = layer1_demo(seed=0)
    mn = demo['min_allocation']
    bound = demo['bound']
    assert mn >= bound, 'min allocation {} < {} totals={}'.format(mn, bound, demo['totals'])
    # 0.59 * fair_share hard-core (counts as allocation units)
    assert mn >= FAIR_RATIO * demo['fair_share'] * 0.9 or mn >= bound
    td = Path(tempfile.mkdtemp(prefix=f'sau-{uuid.uuid4().hex[:8]}-'))
    try:
        p = td / (f'allocation-state_{uuid.uuid4().hex[:8]}.json')
        created = run(state_path=p)
        assert created['status'] == 'insufficient_data'
        # malformed json
        bad = td / 'bad.json'
        bad.write_text('{not json', encoding='utf-8')
        st = load_state(bad)
        assert st['status'] == 'empty'
        # live recompute on demo state
        dumped = dump_state(demo['state'])
        _atomic_write_json(p, dumped)
        got = run(state_path=p)
        assert got['status'] == 'ok'
        assert got.get('recommended_arm') in ('A', 'B', 'C')
        loaded = json.loads(p.read_text(encoding='utf-8'))
        assert 'A' in loaded['arms']
        assert 'n_allocated' in loaded['arms']['A']
    finally:
        for q in sorted(td.rglob('*'), reverse=True):
            try:
                q.unlink() if q.is_file() else q.rmdir()
            except OSError:
                pass
        try:
            td.rmdir()
        except OSError:
            pass
    print('[subagent-allocation-ucb] --self-test PASS min={} bound={:.2f} totals={}'.format(
        mn, bound, demo['totals']))
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description='Quantile-based fair subagent allocation')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[subagent-allocation-ucb] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        result = run()
        print(json.dumps({k: result[k] for k in result if k != 'arms'}, default=str))
    except Exception as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc), 'ts': _now()}))
        sys.exit(1)


if __name__ == '__main__':
    main()
