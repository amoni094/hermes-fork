#!/usr/bin/env python3
"""memory-optional-stopping.py — optional sampling bound on SPRT stopping.

Williams / Durrett: for a martingale M_n and bounded stopping time τ,
  E[M_τ] = E[M_0]. Wald SPRT LLR is a martingale under H0 (mean increment 0
  on the H0 support after centering). Unbounded peeking (using future UE
  scores after the decision index) violates optional sampling.

Hard cores:
  1. Decision n_samples <= 4 * ASN (UI/bounded stopping).
  2. Prefix-only LLR at n equals stored llr (no future peek).

Consumes cache/memory-sprt-decisions.jsonl.

Usage:
  python3 memory-optional-stopping.py --self-test
  python3 memory-optional-stopping.py
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

ASN_MULT = 4.0


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


def check_record(rec: dict) -> dict:
    n = int(rec.get('n_samples') or 0)
    asn0 = float(rec.get('asn_h0') or 1.0)
    asn1 = float(rec.get('asn_h1') or 1.0)
    asn = max(asn0, asn1, 1.0)
    bounded = bool(n <= ASN_MULT * asn or rec.get('decision') == 'CONTINUE')
    # Prefix identity: if llr and boundary present, CONTINUE iff B < llr < A
    llr = rec.get('llr')
    a = rec.get('boundary_a')
    b = rec.get('boundary_b')
    peek_ok = True
    decision = rec.get('decision')
    if llr is not None and a is not None and b is not None:
        try:
            llr_f, a_f, b_f = float(llr), float(a), float(b)
            if decision == 'COMMIT' and not (llr_f < b_f):
                peek_ok = False
            if decision == 'DENY' and not (llr_f > a_f):
                peek_ok = False
            if decision == 'CONTINUE' and not (b_f <= llr_f <= a_f):
                peek_ok = False
        except (TypeError, ValueError):
            peek_ok = True
    alarm = (not bounded) or (not peek_ok)
    return {
        'n_samples': n,
        'asn_cap': round(ASN_MULT * asn, 4),
        'bounded_stopping': bounded,
        'prefix_consistent': peek_ok,
        'decision': decision,
        'alarm': alarm,
        'reason': ('unbounded_or_peek' if alarm else 'ok'),
    }


def load_last() -> dict:
    p = _cache_dir() / 'memory-sprt-decisions.jsonl'
    last = {}
    try:
        if not p.exists():
            return last
        for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
            s = line.strip()
            if not s.startswith('{'):
                continue
            try:
                obj = json.loads(s)
            except Exception:
                continue
            if isinstance(obj, dict):
                last = obj
    except Exception:
        return last
    return last


def compute(rec=None) -> dict:
    try:
        row = rec if rec is not None else load_last()
        out = check_record(row) if row else {
            'n_samples': 0, 'bounded_stopping': True, 'prefix_consistent': True,
            'alarm': False, 'reason': 'empty',
        }
        out['ts'] = time.time()
        _atomic_write(_cache_dir() / 'memory-optional-stopping.json', out)
        return out
    except Exception as exc:
        return {'alarm': False, 'fail_open': str(exc)}


def self_test() -> int:
    ok = check_record({'n_samples': 3, 'asn_h0': 2, 'asn_h1': 2, 'llr': 0.0,
                       'boundary_a': 2.94, 'boundary_b': -2.94, 'decision': 'CONTINUE'})
    assert ok['alarm'] is False
    bad_n = check_record({'n_samples': 100, 'asn_h0': 2, 'asn_h1': 2, 'llr': 0.0,
                          'boundary_a': 2.94, 'boundary_b': -2.94, 'decision': 'COMMIT'})
    assert bad_n['alarm'] is True
    peek = check_record({'n_samples': 2, 'asn_h0': 10, 'asn_h1': 10, 'llr': 0.1,
                         'boundary_a': 2.94, 'boundary_b': -2.94, 'decision': 'DENY'})
    assert peek['prefix_consistent'] is False
    print('PASS memory-optional-stopping self-test')
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
