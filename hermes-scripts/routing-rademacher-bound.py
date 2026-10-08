#!/usr/bin/env python3
"""routing-rademacher-bound.py — empirical Rademacher complexity of BM25 scoring.

For a linear class with ||w||_2 <= B and ||x||_2 <= X, R_m <= B X / sqrt(m).
gen_error <= emp_error + 2 R_m + sqrt(log(1/delta)/(2m)).
Alarm if gen bound > 0.4.

Source: Shalev-Shwartz & Ben-David, Understanding ML, Ch 26 (Rademacher).
"""
from __future__ import annotations
import argparse
import json
import math
import os
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

DELTA = 0.05
ALARM = 0.4
B_NORM = 1.0


def feature_norm(token_map):
    # X = max l2 of binary token vectors ~ sqrt(max df-less length)
    mx = 0.0
    for toks in token_map.values():
        mx = max(mx, math.sqrt(float(len(toks))))
    return max(mx, 1.0)


def rademacher(B, X, m):
    m = max(int(m), 1)
    return (B * X) / math.sqrt(m)


def gen_bound(emp, R, m, delta=DELTA):
    m = max(int(m), 1)
    return min(1.0, max(0.0, emp + 2.0 * R + math.sqrt(math.log(1.0 / max(delta, EPS)) / (2.0 * m))))


def compute(beta, index):
    token_map = {}
    skills = index.get('skills') if isinstance(index, dict) else []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get('name'):
                token_map[s['name']] = {t.lower() for t in (s.get('tokens') or []) if isinstance(t, str)}
    names = list(token_map) or (list(beta.keys()) if isinstance(beta, dict) else [])
    m = 0.0
    means = []
    if isinstance(beta, dict):
        for nm in names:
            e = beta.get(nm) if isinstance(beta.get(nm), dict) else {}
            try:
                a = float(e.get('alpha', 1.0)); b = float(e.get('beta', 1.0))
            except (TypeError, ValueError):
                a, b = 1.0, 1.0
            m += max(0.0, a + b - 2.0)
            means.append(a / max(a + b, EPS))
    m = max(m, 1.0)
    emp = 1.0 - (sum(means) / len(means) if means else 0.5)
    X = feature_norm(token_map) if token_map else 1.0
    R = rademacher(B_NORM, X, m)
    gb = gen_bound(emp, R, m)
    return {
        'ts': time.time(),
        'm': m,
        'n_skills': len(names),
        'emp_error': round(emp, 6),
        'feature_norm_X': round(X, 6),
        'rademacher_R': round(R, 6),
        'gen_error_bound': round(gb, 6),
        'alarm': gb > ALARM,
        'alarm_threshold': ALARM,
        'reason': 'rademacher_gen>0.4' if gb > ALARM else 'ok',
    }


def run(cache=None):
    cache = cache or _cache_dir()
    result = compute(_load_json(cache / 'skill-beta-state.json', {}),
                     _load_json(cache / 'skill-router-index.json', {}))
    try:
        _atomic_write_json(cache / 'routing-rademacher-bound.json', result)
    except Exception:
        pass
    return result


def self_test():
    failures = []
    try:
        r10 = rademacher(1.0, 2.0, 10)
        r100 = rademacher(1.0, 2.0, 100)
        assert r100 < r10
        g = gen_bound(0.1, 0.05, 100)
        assert g >= 0.1
    except Exception as e:
        failures.append(f'mono: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            r = run(cache=d)
            assert (d / 'routing-rademacher-bound.json').exists()
            json.dumps(r)
    except Exception as e:
        failures.append(f'io: {e}')
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
