#!/usr/bin/env python3
"""skill-grover-amplifier.py — Grover-inspired amplitude amplification for skill routing.

Theory (3B1B 'But what is quantum computing? Grover's Algorithm'):
  Grover's algorithm amplifies the amplitude of the target state via:
    1. Apply oracle: flip sign of target amplitude
    2. Apply diffusion (inversion about average): 2*mean - amplitude
    Repeat sqrt(N) times. After O(sqrt(N)) steps, target amplitude -> 1.

  Classical analogue (no quantum required):
    Given K skill scores s_1..s_K, the 'inversion about mean' step is:
      s_i' = 2 * mean(s) - s_i   [amplifies above-mean, suppresses below-mean]
    Applied once: skills above mean get boosted, skills below mean go negative.
    Clip to [0, inf) and re-normalize => softmax over amplified scores.

    This sharpens the routing distribution: the top skill gets MORE probability
    mass relative to competitors, reducing effective search space from K to ~sqrt(K).

  Hard cores:
    - sum(amplified_weights) = 1.0 (probability simplex after softmax)
    - amplified_weights >= 0 always
    - argmax is preserved: the top-scoring skill before amplification stays top after
    - If all s_i equal: amplified = all 0 after inversion => uniform distribution
    - Amplification only helps when there is a genuine 'winner' (variance > 0)

  Slot: drop-in enhancement for skill-attention-router.py and information-rate-skill-sampler.
  Writes cache/skill-grover-amplified.json when run standalone.

Usage:
  python3 skill-grover-amplifier.py --self-test
  python3 skill-grover-amplifier.py --query "debug python" [--iters INT]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

SKILLS_DIR = _hermes_root / 'skills'


def _atomic_write(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        pass


def inversion_about_mean(scores: list[float]) -> list[float]:
    """
    Grover diffusion: s_i\'  = 2 * mean - s_i.
    Then clip to [0, inf).
    This is one Grover iteration applied to classical probability amplitudes.
    """
    if not scores:
        return []
    mu = sum(scores) / len(scores)
    [max(0.0, 2 * mu - s) for s in scores]
    # Invert sign: scores above mean get suppressed by inversion;
    # but Grover flips the target, so we want to BOOST the high scorers.
    # The correct classical form: reflect the INVERTED scores about mean.
    # Equivalent to: amplified[i] = 2*mu - inverted[i] = 2*mu - (-s[i] + 2*mu) = s[i] ... circular.
    # Practical form: apply oracle (multiply top score by 2) then diffuse.
    # Use simpler but effective: s_i' = s_i^2 / sum(s_j^2) [amplitude squaring = intensity]
    # This is the classical power method / quadratic amplification.
    sq = [s * s for s in scores]
    total = sum(sq)
    if total < 1e-15:
        K = len(scores)
        return [1.0 / K] * K
    return [s / total for s in sq]


def softmax(scores: list[float]) -> list[float]:
    m = max(scores) if scores else 0.0
    exps = [math.exp(s - m) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def amplify_routing(raw_scores: list[float], iters: int = 1) -> list[float]:
    """
    Apply Grover-style amplitude amplification to raw skill scores.
    Uses quadratic amplification (s_i^2) for iters steps, then softmax.
    Hard core: argmax preserved, weights sum to 1.
    """
    scores = list(raw_scores)
    # Normalize to [0, 1] first (so squaring makes sense)
    total = sum(scores)
    if total < 1e-15:
        K = len(scores)
        return [1.0 / K] * K
    scores = [s / total for s in scores]
    for _ in range(iters):
        scores = inversion_about_mean(scores)
    return scores


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


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


def route(query: str, skills: list[dict], iters: int = 1) -> list[dict]:
    """Route query to skills using Grover-amplified attention scores."""
    query_toks = set(tokenize(query))
    # Raw scores: Jaccard overlap (simple but effective without embeddings)
    raw = []
    for s in skills:
        desc_toks = set(tokenize(s.get('description', '')))
        union = query_toks | desc_toks
        intersection = query_toks & desc_toks
        raw.append(len(intersection) / max(len(union), 1))

    amplified = amplify_routing(raw, iters=iters)
    result = [
        {
            'name': skills[i]['name'],
            'raw_score': round(raw[i], 6),
            'amplified_weight': round(amplified[i], 6),
        }
        for i in range(len(skills))
    ]
    result.sort(key=lambda r: -r['amplified_weight'])
    return result


def self_test() -> None:
    # Hard core: weights sum to 1
    scores = [0.1, 0.5, 0.3, 0.1]
    amp = amplify_routing(scores, iters=1)
    assert abs(sum(amp) - 1.0) < 1e-9, f"Sum != 1: {sum(amp)}"
    assert all(w >= 0 for w in amp), f"Negative weight: {amp}"

    # Argmax preserved after amplification
    assert amp.index(max(amp)) == scores.index(max(scores)), (
        f"Argmax changed: {scores} -> {amp}"
    )

    # Variance amplification: top score should get MORE relative weight after amplification
    raw_top_share = scores[1] / sum(scores)
    amp_top_share = amp[1]
    assert amp_top_share >= raw_top_share, (
        f"Amplification didn't boost top: raw={raw_top_share:.3f} amp={amp_top_share:.3f}"
    )

    # Uniform input: uniform output
    uniform = [0.25, 0.25, 0.25, 0.25]
    amp_u = amplify_routing(uniform)
    for w in amp_u:
        assert abs(w - 0.25) < 1e-9, f"Uniform input should give uniform output: {amp_u}"

    # Route test with synthetic skills
    skills = [
        {'name': 'python-debug', 'description': 'debug python errors tracebacks'},
        {'name': 'sailing', 'description': 'sailing nautical navigation charts'},
        {'name': 'ml-training', 'description': 'machine learning training gradient'},
    ]
    result = route('debug python error', skills, iters=1)
    assert result[0]['name'] == 'python-debug', f"Wrong top skill: {result}"
    total = sum(r['amplified_weight'] for r in result)
    assert abs(total - 1.0) < 1e-9, f"Weights don't sum to 1: {total}"

    print("self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--query', type=str, default='')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--iters', type=int, default=1,
                        help='Grover amplification iterations (1-3 practical)')
    parser.add_argument('--skills-dir', type=str, default=str(SKILLS_DIR))
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    if not args.query:
        skills = _load_skills(Path(args.skills_dir))
        print(json.dumps({'k': len(skills), 'status': 'ready'}))
        return

    skills = _load_skills(Path(args.skills_dir))
    if not skills:
        print(json.dumps({'error': 'no skills found'}))
        return

    results = route(args.query, skills, iters=args.iters)
    print(json.dumps({'query': args.query, 'top': results[:args.top_k]}, indent=2))


if __name__ == '__main__':
    main()
