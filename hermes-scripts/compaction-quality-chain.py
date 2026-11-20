#!/usr/bin/env python3
"""compaction-quality-chain.py — Multiplicative stage retention (chain rule).

Theory: Per-stage retention q_i = 1 - d_i. Total Q = prod(q_i).
Silent failure: Q < Q_min even when every d_i <= STAGE_MAX.
"""
from __future__ import annotations
import argparse, json, math, os, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'compaction-quality-chain.json'
Q_MIN = 0.40
STAGE_MAX = 0.50

def chain_retention(stage_d, q_min=Q_MIN, stage_max=STAGE_MAX):
    qs = [max(0.0, min(1.0, 1.0 - float(d))) for d in stage_d]
    Q = 1.0
    for q in qs: Q *= q
    per_ok = all(d <= stage_max for d in stage_d)
    return {
        'Q': round(Q, 6), 'n_stages': len(qs),
        'per_stage_ok': per_ok, 'alarm': Q < q_min,
        'silent_fail': (Q < q_min) and per_ok,
        'worst_stage': round(min(qs) if qs else 1.0, 6),
    }

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def run(dry_run=False):
    src = CACHE / 'compaction-distortions.json'
    if src.exists():
        try: stage_d = json.loads(src.read_text()).get('distortions', [])
        except Exception: stage_d = []
    else:
        stage_d = []
    result = {'ts': int(time.time()), 'source': str(src), **chain_retention(stage_d)}
    if not dry_run: _atomic_write(OUT, result)
    return result

def self_test():
    # Three stages d=0.4: each passes gate, Q=0.6^3=0.216 < 0.40 -> silent_fail
    r = chain_retention([0.4, 0.4, 0.4])
    assert r['per_stage_ok'], f"per_stage_ok false: {r}"
    assert r['alarm'], f"alarm false: {r}"
    assert r['silent_fail'], f"silent_fail false: {r}"
    assert abs(r['Q'] - 0.6**3) < 1e-9, f"Q wrong: {r}"
    # One stage d=0.9: alarm but NOT silent_fail (0.9 > STAGE_MAX)
    r2 = chain_retention([0.9, 0.0, 0.0])
    assert r2['alarm'], f"alarm false for d=0.9: {r2}"
    assert not r2['silent_fail'], f"silent_fail wrong for d=0.9: {r2}"
    # Empty: Q=1, no alarm
    r3 = chain_retention([])
    assert r3['Q'] == 1.0 and not r3['alarm'], f"empty wrong: {r3}"
    # Monotone: adding stages with d>0 decreases Q
    q_prev = 1.0
    for n in range(1, 5):
        rn = chain_retention([0.3]*n)
        assert rn['Q'] <= q_prev + 1e-12, f"Q not monotone at n={n}"
        q_prev = rn['Q']
    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    if args.self_test: self_test(); return
    print(json.dumps(run(args.dry_run), indent=2))

if __name__ == '__main__': main()
