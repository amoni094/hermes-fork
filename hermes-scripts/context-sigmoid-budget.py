#!/usr/bin/env python3
"""context-sigmoid-budget.py — Sigmoid gate on remaining context budget for skill-load k.

Theory (3B1B neural networks): f = sigmoid((B_remain - B0) / tau).
k = k_min + (k_max - k_min) * f. Smooth interpolation: low budget -> few skills.
"""
from __future__ import annotations
import argparse, json, math, os, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'context-sigmoid-budget.json'
B0 = 4000; TAU = 1000; K_MIN = 3; K_MAX = 15

def sigmoid(z):
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)

def k_load(B_remain, B0=B0, tau=TAU, k_min=K_MIN, k_max=K_MAX):
    f = sigmoid((B_remain - B0) / max(tau, 1e-9))
    k = k_min + (k_max - k_min) * f
    return {'f': round(f, 6), 'k_load': round(k),
            'B_remain': B_remain, 'B0': B0, 'tau': tau,
            'k_min': k_min, 'k_max': k_max}

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def run(dry_run=False, B_remain=None):
    if B_remain is None:
        # Try to read from session context budget monitor
        src = CACHE / 'context-budget-potential.json'
        if src.exists():
            try: B_remain = json.loads(src.read_text()).get('remaining_tokens', B0)
            except Exception: B_remain = B0
        else:
            B_remain = B0
    result = {'ts': int(time.time()), **k_load(B_remain)}
    if not dry_run: _atomic_write(OUT, result)
    return result

def self_test():
    # B_remain = B0: f=0.5
    r = k_load(B0)
    assert abs(r['f'] - 0.5) < 1e-9, f"f at B0 wrong: {r['f']}"
    expected_k = round(K_MIN + (K_MAX - K_MIN) * 0.5)
    assert r['k_load'] == expected_k, f"k_load at B0: {r['k_load']} vs {expected_k}"

    # B_remain = B0 + 10*TAU: f > 0.99
    r2 = k_load(B0 + 10 * TAU)
    assert r2['f'] > 0.99, f"f not > 0.99 at B0+10*tau: {r2['f']}"
    assert r2['k_load'] <= K_MAX, f"k_load exceeds k_max: {r2['k_load']}"

    # B_remain = B0 - 10*TAU: f < 0.01
    r3 = k_load(B0 - 10 * TAU)
    assert r3['f'] < 0.01, f"f not < 0.01 at B0-10*tau: {r3['f']}"
    assert r3['k_load'] >= K_MIN, f"k_load below k_min: {r3['k_load']}"

    # k_load in [K_MIN, K_MAX] always
    for b in [0, 1000, 4000, 8000, 100000]:
        r = k_load(b)
        assert K_MIN <= r['k_load'] <= K_MAX, f"k_load out of range at B={b}: {r}"

    # Monotone: larger B_remain -> larger f
    prev_f = 0.0
    for b in [0, 2000, 4000, 6000, 8000, 20000]:
        f = k_load(b)['f']
        assert f >= prev_f - 1e-12, f"f not monotone at B={b}"
        prev_f = f

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--b-remain', type=int, default=None)
    args = p.parse_args()
    if args.self_test: self_test(); return
    print(json.dumps(run(args.dry_run, args.b_remain), indent=2))

if __name__ == '__main__': main()
