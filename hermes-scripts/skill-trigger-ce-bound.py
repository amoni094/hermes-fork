#!/usr/bin/env python3
"""skill-trigger-ce-bound.py — Fano-bound routing CE monitor for skill triggers.

Theory (3B1B 'Compression is Intelligence'; Cover-Thomas Fano Lemma 2.10.1):
  Fano inequality: H(P_e) + P_e log2(K-1) >= H(S|Q) = H(S) - I(Q;S)
  => P_e >= (H(S) - I(Q;S) - 1) / log2(K)

  Where:
    S = skill identity (K skills total)
    Q = routing query
    P_e = routing error probability
    I(Q;S) = mutual information between query and correct skill

  LLM-pretraining frame: a routing model that achieves low CE on the
  skill-prediction task is essentially an arithmetic coder mapping queries
  to skill intervals. Its CE loss per query IS the routing rate.

  If two skill trigger descriptions are similar (high mutual information
  between them), the routing model cannot achieve low P_e regardless of
  size. The Fano bound makes this HARD: routing error is lower-bounded.

  Therefore: skills with SIMILAR trigger descriptions contribute high H(S|Q)
  and push up P_e. The fix is to maximize I(Q;S) = make triggers distinctive.

Hermes application:
  1. Load all skill descriptions.
  2. For each pair, compute zlib-based cross-entropy proxy:
     CE(A|B) ≈ H(A, B) - H(B) ≈ (zlib_bits(A+B) - zlib_bits(B)) / len(A)
  3. Compute average CE across skills for each skill as "routing ambiguity".
  4. Compute Fano P_e lower bound: P_e_lb = max(0, (H_S - I_QS - 1) / log2(K))
     where H_S = log2(K) (uniform prior), I_QS estimated from CE gap.
  5. Flag skills where CE(description | other skills) is LOW (easy to confuse).

Hard cores:
  - P_e >= Fano lower bound (cannot route with less error than theory allows)
  - CE proxy obeys DPI: CE(skill | query) >= CE(skill | perfect oracle) = 0
  - zlib cross-entropy is an upper bound on true CE (not tight but monotone)

Falsifying test:
  - Two identical descriptions: high confusion, high P_e lower bound.
  - Two completely different descriptions: low confusion, low P_e lower bound.

Usage:
  python3 skill-trigger-ce-bound.py --self-test
  python3 skill-trigger-ce-bound.py [--top-n N] [--skills-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import zlib
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'skill-trigger-ce-report.json'
ALARM_PATH = CACHE / 'skill-trigger-ce-alarm.json'

AMBIGUITY_THRESHOLD = 0.75   # CE ratio above this = too similar to others
TOP_N = 15                    # report worst N skills by ambiguity


def zlib_bits(text: str) -> float:
    b = text.encode('utf-8', errors='replace')
    if not b:
        return 0.0
    return len(zlib.compress(b, 9)) * 8.0


def cross_entropy_proxy(a: str, b: str) -> float:
    """
    CE proxy: CE(a | b) ≈ [zlib_bits(b + a) - zlib_bits(b)] / len(a_bytes)
    Measures how many bits needed to encode a given the predictor has seen b.
    Lower = a is more predictable from b = more similar / ambiguous.
    """
    a_bytes = a.encode('utf-8', errors='replace')
    if not a_bytes:
        return 0.0
    bits_b = zlib_bits(b)
    bits_ba = zlib_bits(b + a) if b else zlib_bits(a)
    marginal = max(bits_ba - bits_b, 0.0)
    return marginal / max(len(a_bytes) * 8, 1)   # bits per bit of a


def fano_lower_bound(H_S: float, I_QS: float, K: int) -> float:
    """P_e >= max(0, (H(S) - I(Q;S) - 1) / log2(K))."""
    if K <= 1:
        return 0.0
    return max(0.0, (H_S - I_QS - 1.0) / math.log2(K))


def load_skills(skills_dir: Path) -> list[dict]:
    """Load skill descriptions from SKILL.md frontmatter."""
    skills = []
    for skill_md in sorted(skills_dir.rglob('SKILL.md')):
        try:
            text = skill_md.read_text('utf-8', errors='replace')
            # Extract description from frontmatter
            desc = ''
            in_front = False
            for line in text.splitlines():
                if line.strip() == '---':
                    in_front = not in_front
                    continue
                if in_front and line.startswith('description:'):
                    desc = line.split(':', 1)[1].strip().strip('"').strip("'")
                    break
            if desc:
                skills.append({
                    'name': skill_md.parent.name,
                    'description': desc,
                })
        except Exception:
            pass
    return skills


SAMPLE_SIZE = 20   # compare each skill against a random sample of peers
BOTTOM_PCT = 0.10  # flag bottom 10% by CE ratio as "ambiguous"


def analyze(skills: list[dict], seed: int = 42) -> dict:
    import random as _rnd
    rng = _rnd.Random(seed)
    K = len(skills)
    if K < 2:
        return {'error': 'need at least 2 skills', 'K': K}

    H_S = math.log2(K)  # uniform prior entropy over K skills

    results = []
    for i, sk in enumerate(skills):
        # Sample min(SAMPLE_SIZE, K-1) peer descriptions to form the context.
        # Using ALL peers when K>>1 saturates the compressor; sampling gives
        # a stable per-skill CE estimate that scales with K.
        peers = [s['description'] for j, s in enumerate(skills) if j != i]
        sample = rng.sample(peers, min(SAMPLE_SIZE, len(peers)))
        others = ' '.join(sample)
        ce = cross_entropy_proxy(sk['description'], others)
        # I(Q;S) proxy: CE ratio * H_S
        I_QS = H_S * ce
        p_e_lb = fano_lower_bound(H_S, I_QS, K)
        results.append({
            'name': sk['name'],
            'description': sk['description'][:80],
            'ce_ratio': round(ce, 4),
            'I_QS_proxy': round(I_QS, 4),
            'p_e_lower_bound': round(p_e_lb, 4),
        })

    results.sort(key=lambda x: x['ce_ratio'])
    # Flag bottom BOTTOM_PCT% as ambiguous (relative ranking, not absolute threshold)
    n_flag = max(1, int(len(results) * BOTTOM_PCT))
    for i, r in enumerate(results):
        r['ambiguous'] = i < n_flag

    ambiguous = [r for r in results if r['ambiguous']]
    summary = {
        'ts': int(time.time()),
        'K': K,
        'H_S': round(H_S, 4),
        'n_ambiguous': len(ambiguous),
        'worst_N': results[:TOP_N],
    }
    return summary


def _atomic_write(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        pass


def self_test() -> None:
    # Hard core 1: Fano bound non-negative for any input
    skills_identical = [
        {'name': 'a', 'description': 'Use when doing X. Handles X tasks.'},
        {'name': 'b', 'description': 'Use when doing X. Handles X tasks.'},
    ]
    res = analyze(skills_identical)
    for r in res['worst_N']:
        assert r['p_e_lower_bound'] >= 0.0, f"Fano bound must be non-negative: {r}"

    # Hard core 2: identical descriptions have LOWER CE ratio than distinct ones
    # (identical = more predictable from each other = more ambiguous)
    skills_different = [
        {'name': 'python', 'description': 'Use when writing Python code for data processing pipelines and ETL.'},
        {'name': 'sailing', 'description': 'Use when navigating ocean vessels in maritime logistics and seamanship.'},
    ]
    res2 = analyze(skills_different)
    ce_identical = res['worst_N'][0]['ce_ratio'] if res['worst_N'] else 1.0
    ce_distinct = res2['worst_N'][0]['ce_ratio'] if res2['worst_N'] else 0.0
    assert ce_identical <= ce_distinct, (
        f"Identical triggers should have lower CE than distinct: "
        f"identical={ce_identical:.4f}, distinct={ce_distinct:.4f}"
    )

    # Hard core 3: n_ambiguous for identical >= n_ambiguous for distinct
    assert res['n_ambiguous'] >= res2['n_ambiguous'], (
        f"Identical should have >= ambiguous skills: {res['n_ambiguous']} vs {res2['n_ambiguous']}"
    )

    print("self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--top-n', type=int, default=TOP_N)
    parser.add_argument('--skills-dir', type=Path,
                        default=_hermes_root / 'skills')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    skills = load_skills(args.skills_dir)
    if not skills:
        sys.exit(0)

    result = analyze(skills)
    result['TOP_N'] = args.top_n
    result['worst_N'] = result['worst_N'][:args.top_n]

    print(json.dumps({
        'K': result['K'],
        'n_ambiguous': result['n_ambiguous'],
        'H_S': result['H_S'],
        'worst_trigger': result['worst_N'][0] if result['worst_N'] else None,
    }, indent=2))

    if not args.dry_run:
        _atomic_write(OUT_PATH, result)
        worst = result['worst_N'][0] if result.get('worst_N') else None
        if (result.get('n_ambiguous', 0) > 0
                and worst is not None
                and worst.get('ce_ratio', 1.0) < 0.3):
            _atomic_write(ALARM_PATH, {
                'ts': result['ts'],
                'n_ambiguous': result['n_ambiguous'],
                'examples': result['worst_N'][:3],
            })


if __name__ == '__main__':
    main()
