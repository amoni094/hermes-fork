#!/usr/bin/env python3
"""Discrete dynamical system for balanced resource allocation."""
from __future__ import annotations
import argparse, fcntl, json, math, os, random, sys, uuid
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'dynamic-resource-alloc.json'
ALLOC_STATE = CACHE / 'allocation-state.json'
ALPHA = 0.1
EPS = 1e-9
MAX_STEPS = 50
TOL = 1e-4


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix('.lock')
    tmp = path.with_name(path.name + '.tmp')
    with open(str(lock_path), 'a', encoding='utf-8') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
            os.replace(str(tmp), str(path))
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def utility(x, eps=EPS):
    return sum(math.log(xi + eps) for xi in x)


def grad_utility(x, eps=EPS):
    return [1.0 / (xi + eps) for xi in x]


def project_simplex(x):
    x = [max(0.0, float(xi)) for xi in x]
    s = sum(x)
    if s <= 0:
        n = len(x) or 1
        return [1.0 / n] * n
    return [xi / s for xi in x]


def step(x, alpha=ALPHA):
    g = grad_utility(x)
    nxt = [(1.0 - alpha) * xi + alpha * gi for xi, gi in zip(x, g)]
    return project_simplex(nxt)


def allocate(n=4, alpha=ALPHA, max_steps=MAX_STEPS, tol=TOL, x0=None):
    if x0 is None:
        return {
            'ts': _now(), 'status': 'insufficient_data', 'reason': 'no_x0',
            'allocation': [], 'n_workers': 0,
        }
    x = list(x0)
    hist = [list(x)]
    converged = False
    steps = 0
    for t in range(max_steps):
        nxt = step(x, alpha=alpha)
        delta = sum(abs(a - b) for a, b in zip(nxt, x))
        x = nxt
        hist.append(list(x))
        steps = t + 1
        if delta < tol:
            converged = True
            break
    return {
        'ts': _now(), 'status': 'ok',
        'allocation': x, 'utility': utility(x), 'steps': steps,
        'converged': converged, 'n_workers': len(x), 'alpha': alpha,
        'history_tail': hist[-5:],
    }


def load_x0(path: Path | None = None):
    src = path if path is not None else ALLOC_STATE
    if not src.exists():
        return None
    try:
        data = json.loads(src.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    arms = data.get('arms') if isinstance(data, dict) else None
    if not isinstance(arms, dict) or not arms:
        return None
    vals = []
    for _name, rec in arms.items():
        if isinstance(rec, dict):
            v = rec.get('n_allocated', rec.get('utility', rec.get('mean', 1.0)))
        else:
            v = rec
        try:
            vals.append(max(float(v), 0.0))
        except (TypeError, ValueError):
            vals.append(0.0)
    if not vals or sum(vals) <= 0:
        return None
    return project_simplex(vals)


def run(state_path: Path | None = None, dest: Path | None = None, x0=None) -> dict:
    seed = x0 if x0 is not None else load_x0(state_path)
    r = allocate(n=len(seed) if seed else 0, x0=seed)
    _atomic_write(dest if dest is not None else OUT_PATH, r)
    return r


def _self_test() -> int:
    r = allocate(n=4, x0=[0.7, 0.2, 0.05, 0.05])
    assert r['status'] == 'ok'
    assert abs(sum(r['allocation']) - 1.0) < 1e-8
    assert max(r['allocation']) - min(r['allocation']) < 0.15
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    try:
        _atomic_write(tmp, r)
        assert json.loads(tmp.read_text())['converged'] in (True, False)
    finally:
        tmp.unlink(missing_ok=True)
        tmp.with_suffix('.lock').unlink(missing_ok=True)
    empty = allocate(x0=None)
    assert empty['status'] == 'insufficient_data'
    print('[dynamical-resource-allocator] --self-test PASS steps={}'.format(r['steps']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[dynamical-resource-allocator] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        r = run()
        print(json.dumps({k: r[k] for k in r if k != 'history_tail'}, default=str))
    except Exception as e:
        print(json.dumps({'status': 'error', 'reason': str(e), 'ts': _now()}))
    sys.exit(0)


if __name__ == '__main__':
    main()
