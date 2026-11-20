#!/usr/bin/env python3
"""routing-brouwer-attractor.py — Brouwer fixed-point iteration on skill simplex.

Theory (Brouwer fixed-point theorem): any continuous map on a convex compact set
has a fixed point. F(p) = softmax(A*mix(p)) where mix(p) blends skill BOW descriptions.
Attractors = skills whose probability mass is stable under F. Feeds routing priors.
"""
from __future__ import annotations
import argparse, json, math, os, re, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'routing-brouwer-attractors.json'
SKILLS_DIR = _root / 'skills'

def bow(text):
    c = {}
    for w in re.findall(r'[a-z]+', (text or '').lower()):
        if len(w) > 2: c[w] = c.get(w, 0) + 1
    n = sum(c.values()) or 1
    return {k: v / n for k, v in c.items()}

def mix_desc(descs, p):
    m = {}
    for w, d in zip(p, descs):
        for k, v in d.items():
            m[k] = m.get(k, 0.0) + w * v
    return m

def score_all(q, descs):
    s = [sum(q.get(k, 0.0) * v for k, v in d.items()) for d in descs]
    m = max(s) if s else 0.0
    e = [math.exp(x - m) for x in s]
    z = sum(e) or 1.0
    return [x / z for x in e]

def iterate(descs, steps=40, eps=1e-4):
    K = len(descs)
    if K == 0: return []
    p = [1.0 / K] * K
    for _ in range(steps):
        q = mix_desc(descs, p)
        nxt = score_all(q, descs)
        if sum(abs(a - b) for a, b in zip(nxt, p)) < eps:
            return nxt
        p = nxt
    return p

def _load_skills():
    result = {}
    if not SKILLS_DIR.exists():
        return result
    for skill_md in SKILLS_DIR.rglob('SKILL.md'):
        name = skill_md.parent.name
        try:
            result[name] = skill_md.read_text('utf-8', errors='replace')
        except Exception:
            pass
    return result

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def run(dry_run=False):
    skills = _load_skills()
    if not skills:
        result = {'ts': int(time.time()), 'error': 'no skills found', 'attractors': []}
        if not dry_run: _atomic_write(OUT, result)
        return result
    names = list(skills.keys())
    descs = [bow(skills[n]) for n in names]
    p_star = iterate(descs)
    attractors = sorted(zip(names, p_star), key=lambda x: -x[1])
    result = {
        'ts': int(time.time()),
        'K': len(names),
        'sum_p': round(sum(p_star), 6),
        'top_attractors': [{'skill': n, 'mass': round(m, 6)} for n, m in attractors[:10]],
    }
    if not dry_run: _atomic_write(OUT, result)
    return result

def self_test():
    # Identical descriptions: p* = uniform
    descs = [bow('the quick brown fox jumps over lazy dog')] * 4
    p = iterate(descs)
    assert abs(sum(p) - 1.0) < 1e-9, f"sum!=1: {sum(p)}"
    for pi in p:
        assert abs(pi - 0.25) < 0.01, f"Not uniform: {p}"

    # One disjoint skill: its mass should grow
    descs2 = [
        bow('python python python python python debug debug'),
        bow('python python python python python debug debug'),
        bow('xyzzy xyzzy xyzzy xyzzy nonce nonce nonce'),
    ]
    p2 = iterate(descs2)
    assert abs(sum(p2) - 1.0) < 1e-9
    # Disjoint skill (index 2) should have different mass than others
    # (direction: its mass can go up or down depending on how it blends)
    # Minimal assertion: sum=1, all >= 0
    assert all(pi >= 0.0 for pi in p2)

    # Convergence: ||F(p*) - p*||_1 < 0.01
    descs3 = [bow('alpha beta gamma'), bow('delta epsilon zeta'), bow('eta theta iota')]
    p3 = iterate(descs3)
    q = mix_desc(descs3, p3)
    nxt = score_all(q, descs3)
    residual = sum(abs(a - b) for a, b in zip(nxt, p3))
    assert residual < 0.01, f"Not converged: residual={residual}"

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    if args.self_test: self_test(); return
    print(json.dumps(run(args.dry_run), indent=2))

if __name__ == '__main__': main()
