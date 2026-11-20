#!/usr/bin/env python3
"""routing-backprop-sensitivity.py — Softmax Jacobian for routing sensitivity.

Theory (3B1B backpropagation): diagonal Jacobian g_i = alpha_i*(1-alpha_i).
Max g at tie (0.25). Near 0 for confident routing. Clip weight updates if near-tie.
"""
from __future__ import annotations
import argparse, json, math, os, time
from pathlib import Path

_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_prof = os.environ.get('HERMES_PROFILE', 'fork')
_root = _base / 'profiles' / _prof if 'profiles' not in str(_base) else _base
CACHE = _root / 'cache'
OUT = CACHE / 'routing-sensitivity.json'

def softmax(s):
    m = max(s) if s else 0.0
    e = [math.exp(x - m) for x in s]
    z = sum(e) or 1.0
    return [v / z for v in e]

def routing_grad(alpha):
    """Diagonal Jacobian: g_i = alpha_i * (1 - alpha_i). Max = 0.25 at tie."""
    return [a * (1.0 - a) for a in alpha]

def clip_update(delta, g, clip=0.05, tau=0.2):
    """Clip weight updates if routing is near-tie (max g > tau)."""
    if g and max(g) > tau:
        return [max(-clip, min(clip, d)) for d in delta]
    return list(delta)

def sensitivity_report(scores, names=None):
    alpha = softmax(scores)
    g = routing_grad(alpha)
    max_g = max(g) if g else 0.0
    winner = alpha.index(max(alpha))
    return {
        'alpha': [round(a, 6) for a in alpha],
        'grad': [round(gi, 6) for gi in g],
        'max_grad': round(max_g, 6),
        'winner': names[winner] if names else winner,
        'unstable': max_g > 0.2,
        'confident': alpha[winner] > 0.9,
    }

def _atomic_write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    os.replace(tmp, path)

def run(dry_run=False):
    src = CACHE / 'routing-naive-bayes-map.json'
    scores = []
    if src.exists():
        try:
            data = json.loads(src.read_text())
            scores = [item['log_score'] for item in data.get('top5', [])]
        except Exception: pass
    if not scores: scores = [0.0, 0.0]
    result = {'ts': int(time.time()), **sensitivity_report(scores)}
    if not dry_run: _atomic_write(OUT, result)
    return result

def self_test():
    # Tie: s=[0,0] -> alpha=[0.5,0.5], g=[0.25,0.25], max_g=0.25
    r = sensitivity_report([0.0, 0.0])
    assert abs(r['alpha'][0] - 0.5) < 1e-9
    assert abs(r['grad'][0] - 0.25) < 1e-9
    assert abs(r['max_grad'] - 0.25) < 1e-9
    assert r['unstable']

    # Confident: s=[10,0] -> g_winner near 0
    r2 = sensitivity_report([10.0, 0.0])
    assert r2['grad'][0] < 0.001, f"Winner grad not near 0: {r2['grad'][0]}"
    assert not r2['unstable']

    # g_i in [0, 0.25] always
    for s in [[0,0], [10,0], [1,2,3], [0.5,0.5,0.5]]:
        r = sensitivity_report(s)
        for gi in r['grad']:
            assert 0.0 <= gi <= 0.25 + 1e-9, f"g_i out of [0,0.25]: {gi}"

    # clip_update: max(g) > tau -> clips to [-clip, clip]
    delta = [1.0, -1.0, 0.5]
    g_high = [0.25, 0.25, 0.25]
    clipped = clip_update(delta, g_high, clip=0.05, tau=0.2)
    assert all(abs(d) <= 0.05 + 1e-9 for d in clipped), f"Not clipped: {clipped}"

    # clip_update: max(g) < tau -> unchanged
    g_low = [0.05, 0.05, 0.05]
    unclipped = clip_update(delta, g_low, clip=0.05, tau=0.2)
    assert unclipped == delta, f"Should not clip: {unclipped}"

    # Jacobian rows sum to ~0 (probability simplex constraint)
    # For 2-way: g = alpha*(1-alpha); sum of full row = alpha_i*(1 - alpha_i) + alpha_i*(-alpha_j)
    # = alpha_i - alpha_i^2 - alpha_i*alpha_j = alpha_i*(1 - sum(alpha)) = 0
    # Diagonal alone g_i = alpha_i*(1-alpha_i) is positive; check it's bounded by 0.25
    alpha2 = softmax([0.0, 0.0])
    g2 = routing_grad(alpha2)
    assert abs(sum(g2) - 0.5) < 1e-9  # each is 0.25, sum=0.5 for 2 skills

    print("self-test: PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    if args.self_test: self_test(); return
    print(json.dumps(run(args.dry_run), indent=2))

if __name__ == '__main__': main()
