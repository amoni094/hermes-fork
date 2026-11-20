#!/usr/bin/env python3
"""Clopper-Pearson confidence region around a SAFE AI compliance score."""
from __future__ import annotations
import argparse, json, math, os, random, sqlite3, sys, time, uuid, zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone, UTC
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base
CACHE = _hermes_root / 'cache'

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _atomic_write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)

def _lifecycle_db() -> Path:
    return _hermes_root / 'memory-facts' / 'lifecycle.db'

def _connect(db: Path | None = None) -> sqlite3.Connection:
    path = db or _lifecycle_db()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn

OUT_PATH = CACHE / 'compliance-confidence.json'
ALPHA = 0.1


def _binom_sf_ge(k, n, p):
    """P(X >= k) for X~Bin(n,p)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    # recursive terms from P(X=0)
    q = 1.0 - p
    term = q ** n if q > 0 else (0.0 if n > 0 else 1.0)
    if p == 1.0:
        return 1.0 if k <= n else 0.0
    s = 0.0
    for x in range(n + 1):
        if x >= k:
            s += term
        if x < n and term > 0:
            term = term * (n - x) / (x + 1) * p / q if q > 0 else 0.0
    return min(1.0, max(0.0, s))


def _binom_cdf(k, n, p):
    return 1.0 - _binom_sf_ge(k + 1, n, p)


def clopper_pearson(k, n, alpha=ALPHA):
    """CP interval for binomial proportion k/n."""
    k = int(k)
    n = int(n)
    if n <= 0:
        return 0.0, 1.0
    _lo, _hi = 0.0, 1.0
    # lower: inf {p: P(X>=k | p) <= alpha/2} via binary search
    if k == 0:
        lower = 0.0
    else:
        a, b = 0.0, 1.0
        for _ in range(60):
            m = 0.5 * (a + b)
            if _binom_sf_ge(k, n, m) > alpha / 2.0:
                b = m
            else:
                a = m
        lower = a
    if k == n:
        upper = 1.0
    else:
        a, b = 0.0, 1.0
        for _ in range(60):
            m = 0.5 * (a + b)
            if _binom_cdf(k, n, m) > alpha / 2.0:
                a = m
            else:
                b = m
        upper = b
    return float(lower), float(upper)


def region(score, calibration, alpha=ALPHA):
    if score is None:
        return {
            'status': 'insufficient_data',
            'score': None,
            'lower': None,
            'upper': None,
            'alpha': alpha,
            'n_calibration': len(calibration or []),
            'empirical_mean': None,
            'n': 0,
            'ts': _now(),
        }
    score = max(0.0, min(1.0, float(score)))
    cal = []
    for x in calibration or []:
        try:
            cal.append(max(0.0, min(1.0, float(x))))
        except (TypeError, ValueError):
            continue
    n = len(cal)
    if n == 0:
        return {
            'status': 'insufficient_data',
            'score': None if score is None else float(score) if False else None,
            'lower': None,
            'upper': None,
            'alpha': alpha,
            'n_calibration': 0,
            'empirical_mean': None,
            'ts': _now(),
        }
    sum(1 for x in cal if x >= 0.5)
    mean = sum(cal) / n
    k_s = round(n * score)
    lo, hi = clopper_pearson(k_s, n, alpha)
    # shrink toward observed score
    lo = min(score, lo)
    hi = max(score, hi)
    return {
        'status': 'ok',
        'score': score,
        'lower': lo,
        'upper': hi,
        'alpha': alpha,
        'n_calibration': n,
        'empirical_mean': mean,
        'ts': _now(),
    }


def _self_test() -> int:
    cal = [0.8] * 20 + [0.9] * 20 + [0.7] * 10
    r = region(0.82, cal, alpha=0.1)
    assert r['lower'] <= r['score'] <= r['upper']
    assert r['n_calibration'] == 50
    lo0, hi0 = clopper_pearson(8, 10, 0.1)
    assert 0.0 <= lo0 <= 0.8 <= hi0 <= 1.0
    empty = region(0.5, [])
    assert empty.get('status') == 'insufficient_data'
    missing = region(None, [0.8]*10)
    assert missing.get('status') == 'insufficient_data'
    tmp = OUT_PATH.with_name(OUT_PATH.stem + '_test_' + uuid.uuid4().hex + OUT_PATH.suffix)
    _atomic_write(tmp, r)
    tmp.unlink(missing_ok=True)
    print('[safe-compliance-confidence] --self-test PASS [{:.3f}, {:.3f}]'.format(r['lower'], r['upper']))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--score', type=float, default=None)
    ap.add_argument('--calibration-file', default='')
    ap.add_argument('--alpha', type=float, default=ALPHA)
    args = ap.parse_args()
    if args.self_test:
        try:
            sys.exit(_self_test())
        except Exception as exc:
            print(f'[safe-compliance-confidence] --self-test FAIL: {exc}')
            sys.exit(1)
    cal = []
    if args.calibration_file:
        p = Path(args.calibration_file)
        try:
            cal = json.loads(p.read_text(encoding='utf-8'))
            if not isinstance(cal, list):
                cal = []
        except (OSError, json.JSONDecodeError):
            cal = []
    r = region(args.score, cal, alpha=args.alpha)
    if r.get('status') != 'insufficient_data':
        try:
            _atomic_write(OUT_PATH, r)
        except Exception:
            pass
    print(json.dumps(r))


if __name__ == '__main__':
    main()
