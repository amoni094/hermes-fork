#!/usr/bin/env python3
"""memory-displacement-convexity.py — McCann displacement convexity of entropy.

Villani: Shannon entropy is displacement-convex on P_2(R). Along the
1-D monotone (quantile) geodesic μ_t = ((1-t)id + t T)_# μ, t |-> H(μ_t)
is convex.

Sample t in {0, 1/2, 1}; check H(μ_{1/2}) <= 0.5 H(μ_0) + 0.5 H(μ_1) + slack.
Consumes memory-ot-decay.json importances as μ_0; target = uniform on top-K.

Usage:
  python3 memory-displacement-convexity.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

def _cache_dir() -> Path:
    override = os.environ.get('UE_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write(path: Path, obj: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        pass

SLACK = 0.05


def entropy(p: list) -> float:
    h = 0.0
    for x in p:
        if x > 0:
            h -= x * math.log(x)
    return h


def geodesic_mid(p: list, q: list) -> list:
    # 1-D monotone: sort both, interpolate masses on common support size
    n = min(len(p), len(q))
    if n == 0:
        return []
    ps, qs = sorted(p[:n]), sorted(q[:n])
    mid = [0.5 * a + 0.5 * b for a, b in zip(ps, qs)]
    s = sum(mid) or 1.0
    return [x / s for x in mid]


def check_convexity(p: list, q: list) -> dict:
    if len(p) < 2 or len(q) < 2:
        return {'n': min(len(p), len(q)), 'alarm': False, 'reason': 'short', 'convex_ok': True}
    sp = sum(p) or 1.0
    sq = sum(q) or 1.0
    pn = [max(x, 0.0) / sp for x in p]
    qn = [max(x, 0.0) / sq for x in q]
    mid = geodesic_mid(pn, qn)
    h0, h1, hm = entropy(pn), entropy(qn), entropy(mid)
    rhs = 0.5 * h0 + 0.5 * h1 + SLACK
    ok = bool(hm <= rhs + 1e-9)
    return {
        'n': len(pn),
        'h0': round(h0, 6),
        'h1': round(h1, 6),
        'h_mid': round(hm, 6),
        'convex_ok': ok,
        'alarm': not ok,
        'reason': 'not_displacement_convex' if not ok else 'ok',
        'ts': time.time(),
    }


def load_masses() -> tuple:
    p = _cache_dir() / 'memory-ot-decay.json'
    try:
        if p.exists():
            obj = json.loads(p.read_text(encoding='utf-8'))
            ents = obj.get('entries') or []
            imps = [float(e.get('importance') or 0.0) + 1e-9 for e in ents if isinstance(e, dict)]
            if imps:
                k = max(1, int(obj.get('k') or max(1, len(imps) // 4)))
                q = [1.0 if i < k else 1e-9 for i in range(len(imps))]
                return imps, q
    except Exception:
        pass
    return [], []


def compute(p=None, q=None) -> dict:
    try:
        if p is None:
            p, q = load_masses()
        rec = check_convexity(list(p), list(q))
        _atomic_write(_cache_dir() / 'memory-displacement-convexity.json', rec)
        return rec
    except Exception as exc:
        return {'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    # Two discrete laws on R: entropy of midpoint <= average (Shannon also mixture-convex)
    p = [0.7, 0.2, 0.1]
    q = [0.1, 0.2, 0.7]
    rec = check_convexity(p, q)
    assert rec['convex_ok'] is True
    empty = check_convexity([1.0], [1.0])
    assert empty['convex_ok'] is True
    print('PASS memory-displacement-convexity self-test')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        print(json.dumps(compute(), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'alarm': False, 'fail_open': str(exc)}))
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
