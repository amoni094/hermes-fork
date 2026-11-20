#!/usr/bin/env python3
"""memory-beta-bernoulli-keep.py — Beta-Bernoulli conjugate memory retention.

Theory: Prior Beta(1,1). Access=success: alpha++. Idle=failure: beta++.
Keep probability pi = alpha/(alpha+beta). Keep if pi > tau.
"""
from __future__ import annotations
import argparse, json, math, os, sqlite3, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'memory-beta-bernoulli-keep.json'
LIFECYCLE_DB = _base / 'memory-facts' / 'lifecycle.db'
TAU = 0.5

def update(alpha, beta, accessed):
    return (alpha + 1.0, beta) if accessed else (alpha, beta + 1.0)

def keep_prob(alpha, beta):
    return alpha / max(alpha + beta, 1e-15)

def decide(entries, tau=TAU):
    """entries: list of {id, alpha?, beta?, access_seq: [0/1,...]}"""
    out = []
    for e in entries:
        a, b = float(e.get('alpha', 1.0)), float(e.get('beta', 1.0))
        for hit in e.get('access_seq', []):
            a, b = update(a, b, bool(hit))
        pi = keep_prob(a, b)
        out.append({'id': e['id'], 'alpha': round(a, 4), 'beta': round(b, 4),
                    'pi': pi, 'keep': pi > tau})
    return out

def _load_lifecycle():
    if not LIFECYCLE_DB.exists(): return []
    try:
        conn = sqlite3.connect(LIFECYCLE_DB, timeout=5)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if 'fact_lifecycle' not in tables:
            conn.close()
            return []
        rows = conn.execute(
            "SELECT fact_id, access_count, created_at FROM fact_lifecycle"
        ).fetchall()
        conn.close()
        now = int(time.time())
        out = []
        for fid, ac, created in rows:
            ac = int(ac or 0)
            age_days = max(1, int((now - int(created or now)) / 86400))
            # access_count = successes; age_days = total windows
            alpha = 1 + ac
            beta = 1 + max(0, age_days - ac)
            out.append({'id': fid, 'alpha': alpha, 'beta': beta, 'access_seq': []})
        return out
    except Exception:
        pass
    return []

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def run(dry_run=False):
    entries = _load_lifecycle()
    results = decide(entries)
    out = {'ts': int(time.time()), 'n': len(results), 'tau': TAU,
           'keep_count': sum(1 for r in results if r['keep']),
           'entries': results[:100]}
    if not dry_run: _atomic_write(OUT, out)
    return out

def self_test():
    # No observations: pi=0.5, keep=False (not strictly > 0.5)
    r = decide([{'id': 'e1', 'access_seq': []}])
    assert abs(r[0]['pi'] - 0.5) < 1e-9, f"pi!=0.5: {r[0]}"
    assert r[0]['keep'] == False, f"should not keep at pi=0.5: {r[0]}"

    # 10 hits: alpha=11, beta=1, pi=11/12
    r2 = decide([{'id': 'e2', 'access_seq': [1]*10}])
    assert abs(r2[0]['alpha'] - 11.0) < 1e-9
    assert abs(r2[0]['pi'] - 11/12) < 1e-6
    assert r2[0]['keep'] == True

    # 10 misses: alpha=1, beta=11, pi=1/12
    r3 = decide([{'id': 'e3', 'access_seq': [0]*10}])
    assert abs(r3[0]['alpha'] - 1.0) < 1e-9
    assert abs(r3[0]['pi'] - 1/12) < 1e-6
    assert r3[0]['keep'] == False

    # Swap: 10 misses then 10 hits vs 10 hits then 10 misses
    # (both sequences give same alpha/beta since they just count)
    r_hits_misses = decide([{'id': 'x', 'access_seq': [1]*10 + [0]*5}])
    r_misses_hits = decide([{'id': 'x', 'access_seq': [0]*5 + [1]*10}])
    assert abs(r_hits_misses[0]['pi'] - r_misses_hits[0]['pi']) < 1e-9

    # Initial alpha/beta from stored state
    r4 = decide([{'id': 'e4', 'alpha': 5.0, 'beta': 2.0, 'access_seq': [1]}])
    assert abs(r4[0]['alpha'] - 6.0) < 1e-9

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    if args.self_test: self_test(); return
    print(json.dumps(run(args.dry_run), indent=2))

if __name__ == '__main__': main()
