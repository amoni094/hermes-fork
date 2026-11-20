#!/usr/bin/env python3
"""skill-attention-router.py — Soft attention routing for skill selection.

Theory (3B1B 'Attention in transformers, step-by-step | Deep Learning Ch 6'):
  Attention weight: alpha_j = softmax(Q dot K_j / sqrt(d))_j
  where Q = query vector, K_j = key vector for skill j, d = dimension.

  Hermes application:
    Replace TF-IDF cosine with an attention-like scoring of skills:
    - Query = bag-of-words (BOW) of the user message
    - Key_j = BOW of skill j's trigger description
    - Score_j = dot(Q, K_j) / sqrt(vocab_size)
    - alpha_j = softmax(Score_j)  [routing probability distribution]

  Unlike exact cosine similarity, attention normalizes by sqrt(d),
  which controls the 'peakedness' of the distribution: low d => sharp,
  high d => diffuse. This directly implements the scaled dot-product
  attention formula from Vaswani et al. 2017.

  Hard cores:
    - sum(alpha_j) = 1.0 (probability simplex)
    - alpha_j >= 0 always
    - If all K_j are equal, alpha_j = 1/K (uniform)
    - Argmax(alpha) = argmax(Score) [softmax is order-preserving]

  Slot: called by skill-trigger-ce-bound.py and information-rate-skill-sampler
  as an alternative score function. Also exposes --route MODE for direct use.

Usage:
  python3 skill-attention-router.py --self-test
  python3 skill-attention-router.py --query "how to debug Python" --top-k 5
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

SKILLS_DIR = _hermes_root / 'skills'
CACHE = _hermes_root / 'cache'


def _atomic_write(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        pass


def tokenize(text: str) -> list[str]:
    """Simple whitespace+punctuation tokenizer."""
    return re.findall(r"[a-z]+", text.lower())


def build_bow(tokens: list[str], vocab: dict[str, int]) -> list[float]:
    """Build a BOW vector in the given vocabulary."""
    vec = [0.0] * len(vocab)
    for tok in tokens:
        if tok in vocab:
            vec[vocab[tok]] += 1.0
    return vec


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def softmax(scores: list[float]) -> list[float]:
    """Numerically stable softmax."""
    m = max(scores) if scores else 0.0
    exps = [math.exp(s - m) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def attention_scores(query: str, skills: list[dict]) -> list[dict]:
    """
    Compute soft attention weights over skills given a query.
    skills: list of {name, description, ...}
    Returns list of {name, score, attention_weight} sorted descending.
    """
    # Build shared vocabulary from query + all descriptions
    all_texts = [query] + [s.get('description', '') for s in skills]
    all_tokens = [tokenize(t) for t in all_texts]
    vocab_set = set(tok for toks in all_tokens for tok in toks)
    vocab = {tok: i for i, tok in enumerate(sorted(vocab_set))}
    d = max(len(vocab), 1)

    q_bow = build_bow(all_tokens[0], vocab)
    raw_scores = []
    for i, skill in enumerate(skills):
        k_bow = build_bow(all_tokens[i + 1], vocab)
        raw = dot(q_bow, k_bow) / math.sqrt(d)
        raw_scores.append(raw)

    weights = softmax(raw_scores)
    result = [
        {
            'name': skills[i]['name'],
            'score': round(raw_scores[i], 6),
            'attention_weight': round(weights[i], 6),
        }
        for i in range(len(skills))
    ]
    result.sort(key=lambda r: -r['attention_weight'])
    return result


def _load_skills(skills_dir: Path) -> list[dict]:
    skills = []
    if not skills_dir.exists():
        return skills
    for skill_md in skills_dir.rglob('SKILL.md'):
        desc = ''
        try:
            for line in skill_md.read_text('utf-8', errors='replace').splitlines():
                if line.startswith('description:'):
                    desc = line.split(':', 1)[1].strip().strip('"').strip("'")
                    break
        except Exception:
            continue
        skills.append({'name': skill_md.parent.name, 'description': desc})
    return skills



def mass_select(
    skills: list[dict],
    weights: list[float],
    costs: list[int],
    budget: int,
    tau: float = 0.90,
) -> dict:
    """
    Select the smallest prefix of skills (sorted by attention weight desc)
    whose cumulative attention mass >= tau, subject to total cost <= budget.

    Hard cores:
    - sum(selected weights) in [0, 1]
    - sum(selected costs) <= budget
    - If budget < min(cost), return empty set (not an error)
    - argmax is always included first

    Returns {chosen_indices, mass, spent_budget, tau}.
    """
    order = sorted(range(len(weights)), key=lambda i: -weights[i])
    chosen, mass, spent = [], 0.0, 0
    for i in order:
        cost = costs[i] if i < len(costs) else 1
        if spent + cost > budget:
            continue
        chosen.append(i)
        mass += weights[i]
        spent += cost
        if mass >= tau:
            break
    return {
        'chosen_indices': chosen,
        'chosen_names': [skills[i]['name'] for i in chosen],
        'mass': round(mass, 6),
        'spent_budget': spent,
        'tau': tau,
    }

def self_test() -> None:
    skills = [
        {'name': 'python-debug', 'description': 'Use when debugging Python code tracebacks errors'},
        {'name': 'sailing-nav', 'description': 'Use when navigating sailboats and reading nautical charts'},
        {'name': 'ml-training', 'description': 'Use when training machine learning models gradient descent'},
    ]

    # Hard core: attention weights sum to 1
    results = attention_scores('debugging python errors', skills)
    total = sum(r['attention_weight'] for r in results)
    assert abs(total - 1.0) < 1e-6, f"Weights don't sum to 1: {total}"

    # Hard core: alpha_j >= 0
    for r in results:
        assert r['attention_weight'] >= 0.0

    # Routing: python-debug should rank #1 for python query
    assert results[0]['name'] == 'python-debug', f"Expected python-debug first: {results}"

    # Hard core: python-debug beats sailing for python query (sailing has zero overlap)
    # (ml-training and sailing may both be 0 and tie; just verify python-debug is first)
    python_rank = next(i for i, r in enumerate(results) if r['name'] == 'python-debug')
    sailing_rank = next(i for i, r in enumerate(results) if r['name'] == 'sailing-nav')
    assert python_rank < sailing_rank, f"python-debug should rank above sailing-nav: {results}"

    # Uniform case: all descriptions identical => uniform weights
    uniform_skills = [{'name': f'skill{i}', 'description': 'same description text'} for i in range(4)]
    ur = attention_scores('some query', uniform_skills)
    for r in ur:
        assert abs(r['attention_weight'] - 0.25) < 1e-6, f"Expected uniform: {r}"

    # Argmax preserves order: argmax(alpha) == argmax(score) [by softmax monotonicity]
    scores = [r['score'] for r in results]
    weights = [r['attention_weight'] for r in results]
    assert scores.index(max(scores)) == weights.index(max(weights))


    # mass_select: budget-constrained selection
    test_skills = [
        {'name': 'a', 'description': 'python debug errors'},
        {'name': 'b', 'description': 'sailing nautical'},
        {'name': 'c', 'description': 'machine learning training'},
    ]
    test_q = 'debug python error'
    test_results = attention_scores(test_q, test_skills)
    test_weights = [r['attention_weight'] for r in sorted(test_results, key=lambda r: test_skills.index(next(s for s in test_skills if s['name'] == r['name'])))]
    ms = mass_select(test_skills, test_weights, costs=[10, 5, 8], budget=20, tau=0.90)
    assert ms['spent_budget'] <= 20, f"Over budget: {ms}"
    assert 0.0 <= ms['mass'] <= 1.0, f"Mass out of [0,1]: {ms}"
    # Empty budget: budget < all costs => empty
    ms_empty = mass_select(test_skills, test_weights, costs=[100, 100, 100], budget=50, tau=0.90)
    assert ms_empty['chosen_indices'] == [], f"Should be empty: {ms_empty}"

    print("self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--query', type=str, default='')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--skills-dir', type=str, default=str(SKILLS_DIR))
    parser.add_argument('--mass-select', action='store_true')
    parser.add_argument('--budget', type=int, default=100)
    parser.add_argument('--tau', type=float, default=0.90)
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    if not args.query and not args.mass_select:
        skills = _load_skills(Path(args.skills_dir))
        print(json.dumps({'k': len(skills), 'status': 'ready'}))
        return

    skills = _load_skills(Path(args.skills_dir))
    if not skills:
        print(json.dumps({'error': 'no skills found', 'skills_dir': args.skills_dir}))
        return

    results = attention_scores(args.query, skills)
    if getattr(args, 'mass_select', False):
        weights = [r['attention_weight'] for r in results]
        costs = [1] * len(skills)  # unit cost without real token counts
        ms = mass_select(
            [{'name': r['name']} for r in results],
            weights, costs,
            budget=getattr(args, 'budget', len(skills)),
            tau=getattr(args, 'tau', 0.90),
        )
        print(json.dumps({'query': args.query, 'mass_select': ms}, indent=2))
    else:
        print(json.dumps({'query': args.query, 'top': results[:args.top_k]}, indent=2))


if __name__ == '__main__':
    main()
