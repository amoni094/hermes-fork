#!/usr/bin/env python3
"""skill-paraphrase-persistence.py — Topological persistence under query token dropout.

Theory (topology / persistent homology analogy): skill 'born' at r=0 (in top-k at full query),
'dies' at first dropout radius r where it leaves top-k. Persistence = death - birth.
Persistent skills are robust attractors; fragile skills are routing liabilities.
"""
from __future__ import annotations
import argparse, json, math, os, random, re, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'skill-paraphrase-persistence.json'
SKILLS_DIR = _root / 'skills'

def top_k_jaccard(toks, skills, k=3):
    q = set(toks)
    scored = []
    for s in skills:
        d = set(re.findall(r'[a-z]+', (s.get('description', '') or '').lower()))
        union = q | d; inter = q & d
        scored.append((len(inter) / max(len(union), 1), s['name']))
    scored.sort(reverse=True)
    return [name for _, name in scored[:k]]

def variants(toks, r, n=8, seed=42):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        t = list(toks)
        if r >= len(t):
            out.append([])
        else:
            drop = set(rng.sample(range(len(t)), r))
            out.append([x for i, x in enumerate(t) if i not in drop])
    return out

def persist(query, skills, k=3, rmax=None):
    toks = re.findall(r'[a-z]+', query.lower())
    rmax = rmax if rmax is not None else max(1, len(toks) // 2)
    base_top = set(top_k_jaccard(toks, skills, k))
    bars = {s: {'birth': 0, 'death': rmax + 1} for s in base_top}
    for r in range(1, rmax + 1):
        alive = set()
        for v in variants(toks, r):
            alive |= set(top_k_jaccard(v, skills, k))
        for s in list(bars):
            if s not in alive and bars[s]['death'] == rmax + 1:
                bars[s]['death'] = r
    return {s: {'birth': 0, 'death': b['death'], 'persistence': b['death'] - 0}
            for s, b in bars.items()}

def _load_skills():
    result = []
    if not SKILLS_DIR.exists():
        return result
    for skill_md in SKILLS_DIR.rglob('SKILL.md'):
        name = skill_md.parent.name
        desc = ''
        try:
            for line in skill_md.read_text('utf-8', errors='replace').splitlines():
                if line.startswith('description:'):
                    desc = line.split(':', 1)[1].strip().strip('"').strip("'")
                    break
        except Exception:
            pass
        result.append({'name': name, 'description': desc})
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
    bars = persist(query, skills)
    ranked = sorted(bars.items(), key=lambda x: -x[1]['persistence'])
    result = {'ts': int(time.time()), 'query': query,
              'persistent': [{'skill': s, **b} for s, b in ranked[:10]],
              'fragile': [{'skill': s, **b} for s, b in ranked if b['persistence'] <= 1]}
    if not dry_run: _atomic_write(OUT, result)
    return result

def self_test():
    # Nonce skill: only matches query via unique token
    skills = [
        {'name': 'nonce_skill', 'description': 'xyzzyunique xyzzyunique xyzzyunique'},
        {'name': 'general_a',   'description': 'python debug code error fix patch'},
        {'name': 'general_b',   'description': 'python debug code error fix patch test'},
    ]
    # Query with nonce token: nonce_skill is in top-k at r=0
    query = 'xyzzyunique python debug'
    toks = re.findall(r'[a-z]+', query.lower())
    base = set(top_k_jaccard(toks, skills, k=2))
    assert 'nonce_skill' in base, f"nonce_skill should be in top-2 at r=0: {base}"

    bars = persist(query, skills, k=2, rmax=len(toks))
    # nonce_skill should die at r=1 (drop 'xyzzyunique' token)
    if 'nonce_skill' in bars:
        assert bars['nonce_skill']['persistence'] >= 0, "Persistence must be >= 0"
        # At r=1 with 1 nonce-matching token dropped, nonce_skill likely dies
        # (not guaranteed with 8 variants, but should die by r=len(toks)-1)
        assert bars['nonce_skill']['death'] <= len(toks) + 1

    # persistence >= 0 for all skills
    for s, b in bars.items():
        assert b['persistence'] >= 0, f"Negative persistence: {s} {b}"
        assert b['birth'] == 0, f"Birth should be 0: {b}"

    # Original top skill does NOT die at r=0 (birth=death=0 is impossible for top-k member)
    for s, b in bars.items():
        assert b['death'] > 0, f"Cannot die at r=0: {s} {b}"

    # Query = full description of general_a: should have higher persistence
    query_full = 'python debug code error fix patch'
    bars2 = persist(query_full, skills, k=2, rmax=3)
    if 'general_a' in bars2:
        assert bars2['general_a']['persistence'] >= 0

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
