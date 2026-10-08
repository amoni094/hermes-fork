#!/usr/bin/env python3
"""routing-switching-detector.py — CUSUM / discounted-mean shift on beta posteriors.

Non-stationary bandits: if a skill mean jumps by > tau vs EMA, emit SWITCH alarm
so EXP3 gamma should increase (adversarial/nonstationary regime).

Source: Auer switching bandits; discounted UCB; Page CUSUM.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

EMA = 0.9
TAU = 0.2
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


def means_from_beta(beta: dict) -> dict:
    out = {}
    if not isinstance(beta, dict):
        return out
    for k, v in beta.items():
        if not isinstance(v, dict):
            continue
        try:
            a = float(v.get('alpha', 1.0))
            b = float(v.get('beta', 1.0))
        except (TypeError, ValueError):
            continue
        out[k] = a / max(a + b, EPS)
    return out


def update_ema(prev_ema: dict, now: dict, decay: float = EMA) -> dict:
    keys = set(prev_ema) | set(now)
    out = {}
    for k in keys:
        p = float(prev_ema.get(k, now.get(k, 0.5)))
        x = float(now.get(k, p))
        out[k] = decay * p + (1.0 - decay) * x
    return out


def cusum_jumps(prev_ema: dict, now: dict, tau: float = TAU) -> list:
    jumps = []
    for k, x in now.items():
        p = float(prev_ema.get(k, x))
        delta = x - p
        if abs(delta) >= tau:
            jumps.append({'skill': k, 'ema': round(p, 6), 'now': round(x, 6),
                          'delta': round(delta, 6)})
    return jumps


def compute(beta: dict, prev_state: dict) -> dict:
    now = means_from_beta(beta)
    prev_ema = prev_state.get('ema') if isinstance(prev_state, dict) else {}
    if not isinstance(prev_ema, dict):
        prev_ema = {}
    jumps = cusum_jumps(prev_ema, now, TAU)
    ema = update_ema(prev_ema, now, EMA)
    return {
        'ts': time.time(),
        'tau': TAU,
        'ema_decay': EMA,
        'n_skills': len(now),
        'n_jumps': len(jumps),
        'alarm': len(jumps) > 0,
        'jumps': jumps,
        'recommend_gamma': 0.3 if jumps else 0.1,
        'ema': {k: round(v, 6) for k, v in ema.items()},
    }


def run(cache: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    beta = _load_json(cache / 'skill-beta-state.json', {})
    prev_path = cache / 'routing-switching-state.json'
    prev = _load_json(prev_path, {})
    result = compute(beta if isinstance(beta, dict) else {}, prev if isinstance(prev, dict) else {})
    persist = {'ema': result.get('ema', {}), 'ts': result['ts']}
    try:
        _atomic_write_json(prev_path, persist)
        slim = {k: v for k, v in result.items() if k != 'ema'}
        slim['n_ema'] = len(result.get('ema') or {})
        _atomic_write_json(cache / 'routing-switching-detector.json', slim)
    except Exception:
        pass
    slim = {k: v for k, v in result.items() if k != 'ema'}
    slim['n_ema'] = len(result.get('ema') or {})
    return slim


def self_test() -> dict:
    failures = []
    try:
        beta = {'a': {'alpha': 9, 'beta': 1}}  # mean 0.9
        prev = {'ema': {'a': 0.2}}
        r = compute(beta, prev)
        assert r['alarm'] is True
        assert r['recommend_gamma'] == 0.3
    except Exception as e:
        failures.append(f'jump: {e}')
    try:
        r = compute({'a': {'alpha': 2, 'beta': 2}}, {'ema': {'a': 0.5}})
        assert r['alarm'] is False
    except Exception as e:
        failures.append(f'stable: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            r = run(cache=Path(td))
            json.dumps(r)
    except Exception as e:
        failures.append(f'missing: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        print(json.dumps(run(), indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
