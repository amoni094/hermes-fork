#!/usr/bin/env python3
"""memory-access-acceleration.py — 2nd derivative of access counts for adaptive TTL lambda.

Theory (calculus ch.10): acceleration a = d^2x/dt^2. If rate and acceleration both
negative: forgetting is accelerating => increase decay lambda.
lambda_out = lambda0 + alpha*max(0,-r_last) + beta*max(0,-a_last)
"""
from __future__ import annotations
import argparse, json, math, os, sqlite3, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'memory-access-acceleration.json'
LIFECYCLE_DB = _base / 'memory-facts' / 'lifecycle.db'
LAMBDA0, ALPHA, BETA = 0.02, 0.01, 0.02
BINS = 8

def access_accel(counts, lam0=LAMBDA0, alpha=ALPHA, beta=BETA):
    xs = [max(0.0, float(c)) for c in counts]
    if len(xs) < 3:
        return {'lambda': lam0, 'insufficient': True, 'abandoning': False}
    r = [xs[i] - xs[i-1] for i in range(1, len(xs))]
    a = [r[i] - r[i-1] for i in range(1, len(r))]
    r_last = r[-1]; a_last = a[-1] if a else 0.0
    lam = lam0 + alpha * max(0.0, -r_last) + beta * max(0.0, -a_last)
    return {
        'rate': round(r_last, 4), 'accel': round(a_last, 4),
        'lambda': round(lam, 6),
        'abandoning': r_last < 0 and a_last < 0,
        'insufficient': False,
    }

def _load_entries():
    """fact_lifecycle has a single access_count, not a history.

    Proxy: rate = access_count / max(1, age_days). Return per-id dicts.
    """
    if not LIFECYCLE_DB.exists(): return {}
    try:
        conn = sqlite3.connect(LIFECYCLE_DB, timeout=5)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if 'fact_lifecycle' not in tables:
            conn.close()
            return {}
        rows = conn.execute(
            "SELECT fact_id, access_count, created_at, last_accessed "
            "FROM fact_lifecycle"
        ).fetchall()
        conn.close()
        now = int(time.time())
        out = {}
        for mid, ac, created, _last in rows:
            age_days = max(1.0, (now - int(created or now)) / 86400.0)
            rate = float(ac or 0) / age_days
            out[mid] = {'access_count': int(ac or 0), 'age_days': age_days, 'rate': rate}
        return out
    except Exception: return {}

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def run(dry_run=False):
    entries = _load_entries()
    results = []
    for mid, info in entries.items():
        rate = float(info['rate'])
        # Age-normalized rate proxy: low rate => higher decay lambda.
        lam = LAMBDA0 + ALPHA * max(0.0, 1.0 - rate)
        results.append({
            'id': mid,
            'rate': round(rate, 4),
            'accel': 0.0,
            'lambda': round(lam, 6),
            'age_days': round(info['age_days'], 2),
            'access_count': info['access_count'],
            'abandoning': rate < 0.1,
            'insufficient': False,
        })
    results.sort(key=lambda x: -x['lambda'])
    out = {'ts': int(time.time()), 'n': len(results),
           'abandoning_count': sum(1 for r in results if r.get('abandoning')),
           'entries': results[:50]}
    if not dry_run: _atomic_write(OUT, out)
    return out

def self_test():
    # Constant: rate=0, accel=0, lambda=lambda0, not abandoning
    r = access_accel([10, 10, 10, 10])
    assert r['rate'] == 0 and r['accel'] == 0
    assert abs(r['lambda'] - LAMBDA0) < 1e-9
    assert not r['abandoning']

    # Accelerating forget: [10,8,5,1] rates=[-2,-3,-4] accels=[-1,-1]
    r2 = access_accel([10, 8, 5, 1])
    assert r2['rate'] < 0 and r2['accel'] < 0
    assert r2['abandoning']
    assert r2['lambda'] > LAMBDA0

    # Growing: [1,3,6,10] -> not abandoning, lambda=lambda0
    r3 = access_accel([1, 3, 6, 10])
    assert not r3['abandoning']
    assert abs(r3['lambda'] - LAMBDA0) < 1e-9

    # Edge: len=3 gives 2 rates, 1 accel
    r4 = access_accel([5, 5, 5])
    assert not r4['insufficient']
    assert r4['rate'] == 0 and r4['accel'] == 0

    # Insufficient: len < 3
    r5 = access_accel([1, 2])
    assert r5['insufficient']

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    if args.self_test: self_test(); return
    print(json.dumps(run(args.dry_run), indent=2))

if __name__ == '__main__': main()
