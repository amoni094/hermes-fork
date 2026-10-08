#!/usr/bin/env python3
"""routing-tsallis-inf.py — 1/2-Tsallis-INF (best-of-both-worlds) mix over skills.

p_i ∝ 1 / (η * (L_i - min L) + 1)^2  (α=1/2 Tsallis potential).
Stochastic: O(log T) on gaps; adversarial: O(sqrt(T n)). Alarm if mix degenerates (max p > 1-1/n).

Source: Zimmert & Lattimore Tsallis-INF; Lattimore & Szepesvari best-of-both-worlds.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import random
import sys
import tempfile
import time
from collections import defaultdict, deque, Counter
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

EPS = 1e-15


def _cache_dir() -> Path:
    override = os.environ.get('HERMES_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write_json(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n')
        os.replace(str(tmp), str(path))
    except Exception:
        try:
            tmp = path.with_suffix(path.suffix + '.tmp')
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, FileNotFoundError, json.JSONDecodeError):
        return default

ETA = 0.5


def tsallis_p(cum_loss, eta=ETA):
    n = len(cum_loss)
    if n == 0:
        return []
    m = min(cum_loss)
    raw = []
    for L in cum_loss:
        den = eta * (L - m) + 1.0
        raw.append(1.0 / max(den * den, EPS))
    s = sum(raw) or float(n)
    return [x / s for x in raw]


def update_loss(cum_loss, played, reward, p):
    # importance-weighted estimated loss  (1-r)/p
    out = list(cum_loss)
    if 0 <= played < len(out):
        pi = max(p[played], EPS)
        r = 0.0 if reward < 0 else (1.0 if reward > 1 else float(reward))
        out[played] += (1.0 - r) / pi
    return out


def run(cache=None, skill=None, reward=0.0):
    cache = cache or _cache_dir()
    index = _load_json(cache / 'skill-router-index.json', {})
    beta = _load_json(cache / 'skill-beta-state.json', {})
    state = _load_json(cache / 'routing-tsallis-inf.json', {})
    names = []
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        names = [s.get('name') for s in skills if isinstance(s, dict) and s.get('name')]
    if not names and isinstance(beta, dict):
        names = sorted(beta.keys())
    if not names:
        names = list((state.get('loss') or {}).keys()) or ['dummy']
    lmap = (state.get('loss') if isinstance(state, dict) else None) or {}
    loss = [float(lmap.get(nm, 0.0)) for nm in names]
    p = tsallis_p(loss)
    if skill and skill in names:
        loss = update_loss(loss, names.index(skill), reward, p)
        p = tsallis_p(loss)
    mx = max(p) if p else 0.0
    n = max(len(names), 1)
    alarm = mx > (1.0 - 1.0 / n) and n > 1
    out = {
        'ts': time.time(),
        'n': n,
        'eta': ETA,
        'top1': names[max(range(len(p)), key=lambda i: p[i])] if p else None,
        'p_max': round(mx, 6),
        'alarm': alarm,
        'reason': 'degenerate_mix' if alarm else 'ok',
        'p': {names[i]: p[i] for i in range(len(names))},
        'loss': {names[i]: loss[i] for i in range(len(names))},
    }
    try:
        _atomic_write_json(cache / 'routing-tsallis-inf.json', out)
    except Exception:
        pass
    return out


def self_test():
    failures = []
    try:
        p = tsallis_p([0.0, 0.0, 0.0])
        assert abs(sum(p) - 1.0) < 1e-9
        p2 = tsallis_p([0.0, 10.0, 10.0])
        assert p2[0] > p2[1]
        assert all(x > 0 for x in p2)
    except Exception as e:
        failures.append(f'mix: {e}')
    try:
        loss = [0.0, 0.0]
        p = tsallis_p(loss)
        loss2 = update_loss(loss, 0, 1.0, p)  # reward 1 => estimated loss 0
        assert loss2[0] == loss[0]
        loss3 = update_loss(loss, 0, 0.0, p)
        assert loss3[0] > loss[0]
    except Exception as e:
        failures.append(f'iw: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d, skill='dummy', reward=0.0)
            assert (d / 'routing-tsallis-inf.json').exists()
            json.dumps(r)
    except Exception as e:
        failures.append(f'io: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--skill', default=None)
    ap.add_argument('--reward', type=float, default=0.0)
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        r = run(skill=args.skill, reward=args.reward)
        print(json.dumps({k: v for k, v in r.items() if k != 'loss'}, indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
