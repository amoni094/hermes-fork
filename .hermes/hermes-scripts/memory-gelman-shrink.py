#!/usr/bin/env python3
"""memory-gelman-shrink.py — hierarchical partial pooling of importance.

Gelman BDA: importance_i ~ N(μ, τ^2), μ ~ N(μ0, σ0^2). James–Stein /
empirical-Bayes shrinks toward the grand mean. Rank disagreement between
no-pooling and pooled scores flags unstable memory priority.

Alarm if >30% of entries swap top-K membership after shrinkage.

Usage:
  python3 memory-gelman-shrink.py --self-test
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

SWAP_FRAC = 0.30


def shrink(xs: list) -> dict:
    vals = []
    for v in (xs or []):
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            continue
    n = len(vals)
    if n < 3:
        return {'n': n, 'alarm': False, 'reason': 'short', 'swap_frac': 0.0}
    mu = sum(vals) / n
    var = sum((x - mu) ** 2 for x in vals) / n
    # EB: B = σ0^2 / (σ0^2 + τ^2); use σ0^2 = var/n, τ^2 = var
    tau2 = max(var, 1e-12)
    sig0 = max(var / n, 1e-12)
    b = sig0 / (sig0 + tau2)
    pooled = [b * mu + (1.0 - b) * x for x in vals]
    k = max(1, n // 4)
    top_raw = set(sorted(range(n), key=lambda i: -vals[i])[:k])
    top_pool = set(sorted(range(n), key=lambda i: -pooled[i])[:k])
    swap = 1.0 - (len(top_raw & top_pool) / k)
    alarm = bool(swap > SWAP_FRAC)
    return {
        'n': n,
        'k': k,
        'B': round(b, 6),
        'mu': round(mu, 6),
        'swap_frac': round(swap, 6),
        'alarm': alarm,
        'reason': 'rank_swap' if alarm else 'ok',
        'ts': time.time(),
    }


def load_imp() -> list:
    p = _cache_dir() / 'memory-ot-decay.json'
    try:
        if p.exists():
            obj = json.loads(p.read_text(encoding='utf-8'))
            ents = obj.get('entries') or []
            return [float(e.get('importance') or 0.0) for e in ents if isinstance(e, dict)]
    except Exception:
        pass
    out = []
    try:
        q = _cache_dir() / 'ue-memory-gate-log.jsonl'
        if q.exists():
            for line in q.read_text(encoding='utf-8', errors='replace').splitlines():
                s = line.strip()
                if not s.startswith('{'):
                    continue
                try:
                    row = json.loads(s)
                except Exception:
                    continue
                if isinstance(row, dict) and row.get('composite_ue') is not None:
                    out.append(float(row['composite_ue']))
    except Exception:
        pass
    return out[-80:]


def compute(xs=None) -> dict:
    try:
        rec = shrink(list(xs) if xs is not None else load_imp())
        _atomic_write(_cache_dir() / 'memory-gelman-shrink.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    # Mild spread: ranks stable
    xs = [0.4 + 0.01 * i for i in range(20)]
    r = shrink(xs)
    assert r['swap_frac'] <= 0.3
    # One huge outlier vs cluster
    ys = [0.1] * 16 + [10.0, 10.1, 10.2, 0.11]
    r2 = shrink(ys)
    assert r2['n'] == 20
    empty = shrink([1.0, 2.0])
    assert empty['n'] == 2
    print('PASS memory-gelman-shrink self-test')
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
