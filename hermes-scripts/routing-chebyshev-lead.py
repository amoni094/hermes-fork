#!/usr/bin/env python3
"""routing-chebyshev-lead.py — Chebyshev prime race bias detector for routing.

Theory (3B1B number theory / Chebyshev bias): two primes may have equal density
yet one leads almost all the time. Applied: two skills with tied scores but one
consistently wins more pulls signals unexplained routing bias -> boost exploration.

L_T = count(pulls_A > pulls_B when |score_A - score_B| < eps) / tied_count
Alarm if tied_frac > 0.5 AND (L_T > 1-delta OR L_T < delta).
"""
from __future__ import annotations
import argparse, json, math, os, sqlite3, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'routing-chebyshev-lead.json'
LIFECYCLE_DB = _base / 'memory-facts' / 'lifecycle.db'

EPS = 0.05    # score tie threshold
DELTA = 0.15  # lead-fraction alarm threshold (L > 1-delta or L < delta)
T_MIN = 20    # minimum observations

def chebyshev_lead(scores_a, scores_b, pulls_a, pulls_b, eps=EPS, delta=DELTA):
    T = min(len(pulls_a), len(pulls_b), len(scores_a), len(scores_b))
    if T < T_MIN:
        return {'insufficient': True, 'alarm': False, 'T': T}
    tied = lead = 0
    for t in range(T):
        if abs(scores_a[t] - scores_b[t]) < eps:
            tied += 1
            if pulls_a[t] > pulls_b[t]:
                lead += 1
    L = lead / tied if tied > 0 else 0.5
    tied_frac = tied / T
    alarm = tied_frac > 0.5 and (L > 1 - delta or L < delta)
    return {
        'L': round(L, 4), 'tied_frac': round(tied_frac, 4),
        'tied': tied, 'lead': lead, 'T': T,
        'alarm': alarm, 'boost_explore': alarm,
        'insufficient': False,
    }

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def _load_tool_pairs():
    """Load (pulls_a, pulls_b) for the two most common tools from tool_review_log."""
    if not LIFECYCLE_DB.exists():
        return None
    try:
        conn = sqlite3.connect(LIFECYCLE_DB, timeout=5)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if 'tool_review_log' not in tables:
            conn.close()
            return None
        rows = conn.execute(
            "SELECT tool_name, ts FROM tool_review_log ORDER BY ts"
        ).fetchall()
        conn.close()
    except Exception:
        return None
    if not rows:
        return None
    from collections import Counter
    counts = Counter(r[0] for r in rows if r[0])
    if len(counts) < 2:
        return None
    a, b = [t for t, _ in counts.most_common(2)]
    pulls_a, pulls_b, scores_a, scores_b = [], [], [], []
    ca = cb = 0
    for name, _ts in rows:
        if name == a:
            ca += 1
        elif name == b:
            cb += 1
        else:
            continue
        pulls_a.append(ca)
        pulls_b.append(cb)
        scores_a.append(0.5)
        scores_b.append(0.5)
    return a, b, scores_a, scores_b, pulls_a, pulls_b


def run(dry_run=False):
    loaded = _load_tool_pairs()
    if not loaded:
        return {'ts': int(time.time()), 'skipped': True}
    a, b, sa, sb, pa, pb = loaded
    T = min(len(pa), len(pb), len(sa), len(sb))
    if T < T_MIN:
        return {'ts': int(time.time()), 'skipped': True, 'T': T}
    r = chebyshev_lead(sa, sb, pa, pb)
    result = {'ts': int(time.time()), 'pair': [a, b], **r}
    if not dry_run:
        _atomic_write(OUT, result)
    return result

def self_test():
    T = 30
    scores = [0.5] * T

    # A always leads: L=1, tied_frac=1, alarm=True
    r = chebyshev_lead(scores, scores, [2]*T, [1]*T)
    assert not r['insufficient']
    assert r['tied_frac'] == 1.0
    assert abs(r['L'] - 1.0) < 1e-9
    assert r['alarm'], f"Should alarm when A always leads: {r}"

    # Alternating: L~0.5, no alarm
    pa = [2 if i % 2 == 0 else 1 for i in range(T)]
    pb = [1 if i % 2 == 0 else 2 for i in range(T)]
    r2 = chebyshev_lead(scores, scores, pa, pb)
    assert not r2['alarm'], f"Alternating should not alarm: {r2}"
    assert abs(r2['L'] - 0.5) < 0.1

    # Scores never tied: tied_frac=0, no alarm
    sa = [1.0] * T; sb = [0.0] * T
    r3 = chebyshev_lead(sa, sb, [2]*T, [1]*T)
    assert r3['tied_frac'] == 0.0
    assert not r3['alarm']

    # T < 20: insufficient
    r4 = chebyshev_lead([0.5]*10, [0.5]*10, [2]*10, [1]*10)
    assert r4['insufficient'] and not r4['alarm']

    # alarm implies tied_frac > 0.5
    for _ in range(5):
        r = chebyshev_lead(scores, scores, [2]*T, [1]*T)
        if r['alarm']:
            assert r['tied_frac'] > 0.5, f"alarm without tied_frac>0.5: {r}"

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    if args.self_test: self_test(); return
    result = run(args.dry_run)
    if result.get('skipped'):
        return
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
