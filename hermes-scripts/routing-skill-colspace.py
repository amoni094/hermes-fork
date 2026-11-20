#!/usr/bin/env python3
"""routing-skill-colspace.py — Column space rank check on skill description matrix.

Theory (3B1B linear algebra): rank(A) = independently discriminable skills.
rho = ||proj_colspace(q)|| / ||q||. Low rho = query outside skill span = unroutable.
"""
from __future__ import annotations
import argparse, json, math, os, random, re, zlib, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'routing-skill-colspace.json'
SKILLS_DIR = _root / 'skills'
DIM = 64

def hashed_tf(text, dim=DIM):
    v = [0.0] * dim
    for w in re.findall(r'[a-z0-9]+', (text or '').lower()):
        if len(w) > 1: v[zlib.crc32(w.encode()) % dim] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]

def dot(a, b): return sum(x * y for x, y in zip(a, b))

def power_iter_top(rows, r=8, iters=25, seed=42):
    if not rows: return []
    d = len(rows[0])
    rng = random.Random(seed)
    vecs = []
    residual = [list(row) for row in rows]
    for _ in range(min(r, len(rows))):
        v = [rng.gauss(0, 1) for _ in range(d)]
        for __ in range(iters):
            Av = [sum(row[j] * v[j] for j in range(d)) for row in residual]
            AtAv = [sum(residual[i][j] * Av[i] for i in range(len(residual))) for j in range(d)]
            norm = math.sqrt(sum(x * x for x in AtAv)) or 1.0
            v = [x / norm for x in AtAv]
        sigma = math.sqrt(sum(sum(row[j] * v[j] for j in range(d)) ** 2 for row in residual))
        if sigma < 1e-8: break
        vecs.append((sigma, v))
        for row in residual:
            c = sum(row[j] * v[j] for j in range(d))
            for j in range(d): row[j] -= c * v[j]
    return vecs

def colspace_score(skill_texts, query, energy=0.90, tau=0.15):
    rows = [hashed_tf(t) for t in skill_texts]
    if not rows: return {'rank': 0, 'rank_frac': 0.0, 'rho': 0.0, 'unroutable': True, 'collapsed': True}
    d = len(rows[0])
    vecs = power_iter_top(rows, r=min(12, len(rows)))
    total = sum(s * s for s, _ in vecs) or 1.0
    acc = 0.0; r_eff = 0
    for s, _ in vecs:
        acc += s * s; r_eff += 1
        if acc / total >= energy: break
    q = hashed_tf(query)
    nq = math.sqrt(sum(x * x for x in q)) or 1.0
    proj = [0.0] * d
    for _, v in vecs[:r_eff]:
        c = dot(q, v)
        for j in range(d): proj[j] += c * v[j]
    rho = math.sqrt(sum(x * x for x in proj)) / nq
    return {'rank': r_eff, 'rank_frac': round(r_eff / max(len(rows), 1), 3),
            'rho': round(rho, 4), 'unroutable': rho < tau,
            'collapsed': r_eff <= 1 and len(rows) >= 2}

def _load_skills():
    result = {}
    for d in SKILLS_DIR.iterdir():
        md = d / 'SKILL.md'
        if md.exists():
            result[d.name] = md.read_text('utf-8', errors='replace')[:500]
    return result

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def run(query='debug python code', dry_run=False):
    skills = _load_skills()
    if not skills:
        result = {'ts': int(time.time()), 'error': 'no skills'}
        if not dry_run: _atomic_write(OUT, result)
        return result
    names = list(skills.keys())
    result = {'ts': int(time.time()), 'K': len(names), 'query': query,
              **colspace_score(list(skills.values()), query)}
    if not dry_run: _atomic_write(OUT, result)
    return result

def self_test():
    # 3 identical descriptions: collapsed
    same = ['python debug error traceback fix code'] * 3
    r = colspace_score(same, 'python debug')
    assert r['collapsed'], f"Identical rows should collapse: {r}"
    assert r['rank_frac'] < 0.6, f"rank_frac too high for identical: {r}"

    # rank_frac in [0, 1]
    for texts in [same, ['alpha beta gamma', 'delta epsilon zeta', 'eta theta iota']]:
        r2 = colspace_score(texts, 'alpha')
        assert 0.0 <= r2['rank_frac'] <= 1.0, f"rank_frac OOR: {r2}"

    # Query outside span: tokens not in any description
    diverse = ['python debug error', 'sailing nautical chart', 'machine learning gradient']
    r3 = colspace_score(diverse, 'xyzzyuniquenonce blargfrob quux')
    assert 0.0 <= r3['rho'] <= 1.0, f"rho OOR: {r3}"
    assert r3['rho'] < 0.8, f"Unknown query should have low rho: {r3}"

    # 3 diverse descriptions: not collapsed
    r4 = colspace_score(diverse, 'python debug')
    assert not r4['collapsed'], f"Diverse rows should not collapse: {r4}"

    # Result has all required keys
    for key in ('rank', 'rank_frac', 'rho', 'unroutable', 'collapsed'):
        assert key in r4, f"Missing key: {key}"

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--query', type=str, default='debug python code')
    args = p.parse_args()
    if args.self_test: self_test(); return
    print(json.dumps(run(args.query, args.dry_run), indent=2))

if __name__ == '__main__': main()
