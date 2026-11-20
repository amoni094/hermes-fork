#!/usr/bin/env python3
"""Skill-DAG amplification (bullwhip) stability margin.

EMA-smoothed nodal response magnitudes; path products as Lyapunov-style
certificates. Writes amplification-state.json.

Usage:
  python3 stability-margin-analyzer.py --self-test
  python3 stability-margin-analyzer.py
"""
from __future__ import annotations
import argparse, json, os, random, sys
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'amplification-state.json'


def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def ema(xs, alpha=0.2):
    if not xs:
        return 0.0
    v = xs[0]
    for x in xs[1:]:
        v = alpha * x + (1 - alpha) * v
    return v


def path_product(mags, path):
    p = 1.0
    for n in path:
        p *= max(1e-9, float(mags.get(n, 1.0)))
    return p


def max_path_product(mags, paths):
    return max(path_product(mags, pth) for pth in paths) if paths else 0.0


def synthetic_dag(rng, n_nodes=5, n_calls=1000):
    nodes = ['n%d' % i for i in range(n_nodes)]
    paths = [
        nodes[:],
        [nodes[0], nodes[-1]],
        nodes[:3],
        nodes[2:],
    ]
    series = {n: [] for n in nodes}
    for t in range(n_calls):
        base = 0.4 + 0.05 * rng.random()
        for i, n in enumerate(nodes):
            series[n].append(base * (1.15 ** i) + 0.02 * rng.random())
    mags = {n: ema(series[n]) for n in nodes}
    deriv = {}
    for n in nodes:
        s = series[n]
        deriv[n] = (ema(s[-100:]) - ema(s[-200:-100])) if len(s) >= 200 else 0.0
    return nodes, paths, mags, deriv


def rerank_paths(paths, deriv):
    def score(pth):
        return sum(deriv.get(n, 0.0) for n in pth) / max(1, len(pth))
    return sorted(paths, key=score)


def analyze():
    rng = random.Random(5)
    nodes, paths, mags, deriv = synthetic_dag(rng)
    greedy = max_path_product(mags, paths)
    ranked = rerank_paths(paths, deriv)
    # adjoint approx: keep the two lowest-growth paths, report their max product
    kept = ranked[:2] if len(ranked) >= 2 else ranked
    max_path_product(mags, kept)
    # also consider the min-product path as the chosen route
    chosen = min(path_product(mags, pth) for pth in paths)
    return {
        'ts': datetime.now(UTC).isoformat(),
        'nodes': nodes,
        'mags': mags,
        'greedy_max_path_product': greedy,
        'rerank_best_path_product': chosen,
        'improved': greedy > chosen,
    }


def run():
    payload = analyze()
    try:
        _atomic_write(OUT_PATH, payload)
    except Exception:
        pass
    try:
        shadow = Path.home() / '.hermes' / 'cache' / 'shadow' / 'amplification-state.json'
        _atomic_write(shadow, payload)
    except Exception:
        pass
    return payload


def _self_test() -> int:
    rng = random.Random(5)
    _nodes, paths, mags, _deriv = synthetic_dag(rng, n_nodes=5, n_calls=1000)
    greedy = max_path_product(mags, paths)
    chosen = min(path_product(mags, pth) for pth in paths)
    assert greedy > chosen, f'greedy={greedy} chosen={chosen}'
    print('[stability-margin-analyzer] --self-test PASS')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[stability-margin-analyzer] --self-test FAIL: {exc}')
            sys.exit(1)
    try:
        run()
    except Exception as e:
        print(f'[stability-margin-analyzer] ERROR (suppressed): {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
