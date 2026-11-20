#!/usr/bin/env python3
"""routing-naive-bayes-map.py — Naive Bayes MAP skill routing.

Theory (3B1B Bayes): P(skill|query) proportional to P(query|skill)*P(skill).
P(w|skill) = Laplace-smoothed token counts from SKILL.md.
Distinct from dot-product attention router (generative vs discriminative).
"""
from __future__ import annotations
import argparse, json, math, os, re, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'routing-naive-bayes-map.json'
SKILLS_DIR = _root / 'skills'

def tokenize(text):
    return re.findall(r'[a-z][a-z0-9]*', (text or '').lower())

def fit(skills):
    """skills: {name: skill_md_text}. Returns (vocab_idx, log_likelihoods, V)."""
    vocab = sorted({w for t in skills.values() for w in tokenize(t)})
    V = max(len(vocab), 1)
    idx = {w: i for i, w in enumerate(vocab)}
    ll = {}
    for name, text in skills.items():
        c = [0] * V
        toks = tokenize(text)
        for w in toks:
            if w in idx: c[idx[w]] += 1
        n = sum(c)
        ll[name] = [math.log((c[i] + 1) / (n + V)) for i in range(V)]
    return idx, ll, V

def map_route(query, idx, ll, prior=None):
    """Return (winner_name, {name: score}) using MAP estimate."""
    if prior is None:
        prior = {s: 1.0 / max(len(ll), 1) for s in ll}
    q = tokenize(query)
    scores = {}
    for s, logpw in ll.items():
        sc = math.log(max(prior.get(s, 1.0 / max(len(ll), 1)), 1e-15))
        for w in q:
            sc += logpw[idx[w]] if w in idx else math.log(1.0 / (1 + len(idx)))
        scores[s] = sc
    winner = max(scores, key=scores.get)
    return winner, scores

def _load_skills():
    result = {}
    for d in SKILLS_DIR.iterdir():
        md = d / 'SKILL.md'
        if md.exists():
            result[d.name] = md.read_text('utf-8', errors='replace')
    return result

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def run(query='', dry_run=False):
    skills = _load_skills()
    if not skills:
        result = {'ts': int(time.time()), 'error': 'no skills found'}
        if not dry_run: _atomic_write(OUT, result)
        return result
    idx, ll, V = fit(skills)
    if query == '':
        result = {'ts': int(time.time()), 'K': len(skills), 'V': V, 'status': 'indexed'}
        if not dry_run:
            _atomic_write(OUT, result)
        return result
    winner, scores = map_route(query, idx, ll)
    top5 = sorted(scores.items(), key=lambda x: -x[1])[:5]
    result = {'ts': int(time.time()), 'query': query, 'winner': winner,
              'V': V, 'K': len(skills),
              'top5': [{'skill': s, 'log_score': round(sc, 4)} for s, sc in top5]}
    if not dry_run: _atomic_write(OUT, result)
    return result

def self_test():
    # Synthetic skills
    skill_a = ('librarian tidy meek book shelf ' * 4).strip()
    skill_b = ('farmer field meek ' + 'farmer ' * 20).strip()
    skills = {'skill_a': skill_a, 'skill_b': skill_b}
    idx, ll, V = fit(skills)

    # Uniform prior: 'tidy librarian shelf' -> skill_a wins (likelihood)
    q = 'tidy librarian shelf'
    winner, scores = map_route(q, idx, ll)
    assert winner == 'skill_a', f"Expected skill_a, got {winner}: {scores}"

    # Strong prior CAN flip winner: use a query that is neutral (not in either skill's vocab)
    # and an extreme prior favoring skill_b
    q_neutral = 'unknown token that matches neither skill'
    strong_prior = {'skill_a': 1e-10, 'skill_b': 1.0 - 1e-10}
    winner_b, _scores_b = map_route(q_neutral, idx, ll, prior=strong_prior)
    assert winner_b == 'skill_b', f"Extreme prior should select skill_b for neutral query: {winner_b}"

    # Scores are ordered correctly: winner has highest score
    assert scores['skill_a'] > scores['skill_b'], "skill_a should score higher with uniform prior"

    # Scores are log-probabilities (should be negative or at least comparable)
    for s, sc in scores.items():
        assert isinstance(sc, float), f"score not float: {sc}"

    # V = vocab size, K = 2
    assert V > 0 and len(ll) == 2

    # Query with unknown tokens: should not crash
    winner_unk, _ = map_route('xyzzy quux blarg', idx, ll)
    assert winner_unk in ('skill_a', 'skill_b')

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--query', type=str, default='')
    args = p.parse_args()
    if args.self_test: self_test(); return
    print(json.dumps(run(args.query, args.dry_run), indent=2))

if __name__ == '__main__': main()
