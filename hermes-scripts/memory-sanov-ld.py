#!/usr/bin/env python3
"""memory-sanov-ld.py — Sanov large-deviation test on UE histograms.

Cover–Thomas Thm 11.4.1 (Sanov): for i.i.d. X_i ~ Q,
  P(P_n in closed A) <= (n+1)^{|X|} exp(-n inf_{P in A} D(P||Q))

Take Q = Uniform on K bins of composite_ue. If n * KL(P_n || Q) exceeds
log(1/delta) + |X| log(n+1) at delta=0.05, the empirical memory-UE law has
left the typical set of Q → distribution-shift alarm.

Usage:
  python3 memory-sanov-ld.py --self-test
  python3 memory-sanov-ld.py
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

N_BINS = 5
DELTA = 0.05


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


def _clip01(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not math.isfinite(v):
        return 0.5
    return max(0.0, min(1.0, v))


def kl_discrete(p: list, q: list) -> float:
    s = 0.0
    for pi, qi in zip(p, q):
        if pi <= 0.0:
            continue
        s += pi * math.log(pi / max(qi, 1e-12))
    return s


def sanov_stat(samples: list, n_bins: int = N_BINS, delta: float = DELTA) -> dict:
    xs = [_clip01(x) for x in (samples or [])]
    n = len(xs)
    k = max(int(n_bins), 2)
    counts = [0] * k
    for x in xs:
        b = min(k - 1, int(x * k) if x < 1.0 else k - 1)
        counts[b] += 1
    if n == 0:
        return {'n': 0, 'kl_nats': 0.0, 'threshold': 0.0, 'alarm': False, 'reason': 'empty'}
    pn = [c / n for c in counts]
    q = [1.0 / k] * k
    kl = kl_discrete(pn, q)
    # Sanov exponent vs union bound (n+1)^k exp(-n KL)
    thresh = (math.log(1.0 / max(delta, 1e-12)) + k * math.log(n + 1)) / n
    alarm = bool(kl > thresh)
    return {
        'n': n,
        'n_bins': k,
        'kl_nats': round(kl, 6),
        'threshold': round(thresh, 6),
        'pn': [round(x, 6) for x in pn],
        'alarm': alarm,
        'reason': 'sanov_shift' if alarm else 'ok',
        'delta': delta,
        'ts': time.time(),
    }


def load_ue() -> list:
    out = []
    cache = _cache_dir()
    for name in ('ue-memory-gate-log.jsonl', 'ue-blackbox-scores.jsonl', 'ue-memory-gate-scores.jsonl'):
        p = cache / name
        try:
            if not p.exists():
                continue
            for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
                s = line.strip()
                if not s.startswith('{'):
                    continue
                try:
                    row = json.loads(s)
                except Exception:
                    continue
                if not isinstance(row, dict):
                    continue
                v = row.get('composite_ue')
                if v is None:
                    v = row.get('ue_score', row.get('ue'))
                if v is not None:
                    out.append(_clip01(v))
        except Exception:
            continue
        if out:
            break
    return out[-400:]


def compute(samples=None) -> dict:
    try:
        xs = list(samples) if samples is not None else load_ue()
        rec = sanov_stat(xs)
        _atomic_write(_cache_dir() / 'memory-sanov-ld.json', rec)
        return rec
    except Exception as exc:
        return {'n': 0, 'kl_nats': 0.0, 'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    uni = [i / 20.0 for i in range(21)] * 8
    r = sanov_stat(uni, n_bins=5)
    assert r['n'] > 0
    assert r['kl_nats'] >= 0
    # Dirac mass far from uniform → large KL
    spike = [0.01] * 80
    r2 = sanov_stat(spike, n_bins=5, delta=0.05)
    assert r2['kl_nats'] > r['kl_nats']
    empty = sanov_stat([])
    assert empty['n'] == 0 and empty['alarm'] is False
    print('PASS memory-sanov-ld self-test')
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
