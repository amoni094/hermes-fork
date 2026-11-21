#!/usr/bin/env python3
"""shadow-gate-permutation.py — Fisher exact permutation test for shadow vs live.

One-tailed test of shadow > live.
p_value = fraction of shuffles with shuffled_stat >= observed_stat.
M=10000 Monte Carlo for N > 8 (task: M=10000 when N > 20); exact enum for N <= 8.

Signals:
  p < 0.05 and observed > 0 -> PROMOTE
  p < 0.05 and observed < 0 -> REJECT
  else -> NO_SIGNAL
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from datetime import datetime, timezone, UTC
from itertools import combinations
from pathlib import Path
from statistics import mean

home = os.environ.get('HERMES_HOME', '')
home = home.removesuffix('/profiles/fork')
if not home:
    home = os.path.expanduser('~/.hermes')
profile_dir = home + '/profiles/fork'
CACHE = Path(profile_dir) / 'cache'
OUT_PATH = CACHE / 'shadow-gate-permutation-result.json'

M_MONTE_CARLO = 10000
ALPHA = 0.05
REQUIRED_FIELDS = ('signal', 'p_value', 'n_shadow', 'n_live', 'observed_diff', 'timestamp')


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _to_float(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return float(v)
    if isinstance(v, str):
        try:
            x = float(v.strip())
        except Exception:
            return None
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    return None


def _variant_group(v) -> str | None:
    if not isinstance(v, str):
        return None
    s = v.strip().lower()
    if s in ('shadow', 'treatment'):
        return 'shadow'
    if s in ('live', 'control'):
        return 'live'
    return None


def _load_jsonl(path: Path) -> list[dict]:
    recs = []
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return recs
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            recs.append(obj)
    return recs


def _shadow_jsonl_files() -> list[Path]:
    if not CACHE.is_dir():
        return []
    files = []
    preferred = CACHE / 'shadow-results.jsonl'
    if preferred.is_file():
        files.append(preferred)
    try:
        for p in sorted(CACHE.glob('shadow-*.jsonl')):
            if p not in files and p.is_file():
                files.append(p)
    except Exception:
        pass
    return files


def _split_shadow_live(records: list[dict]) -> tuple[list[float], list[float]]:
    shadow, live = [], []
    for rec in records:
        score = _to_float(rec.get('score'))
        if score is None:
            continue
        g = _variant_group(rec.get('variant'))
        if g == 'shadow':
            shadow.append(score)
        elif g == 'live':
            live.append(score)
    return shadow, live


def _split_by_model(records: list[dict]) -> tuple[list[float], list[float]]:
    """Temporal split of calibration-log: older half=live, newer half=shadow.
    Uses predicted_confidence as score proxy."""
    vals = []
    for rec in records:
        score = _to_float(rec.get('score'))
        if score is None:
            score = _to_float(rec.get('predicted_confidence'))
        if score is None:
            continue
        vals.append(score)
    if len(vals) < 20:
        return [], []
    mid = len(vals) // 2
    live = vals[:mid]
    shadow = vals[mid:]
    return shadow, live


def permutation_p_both(shadow: list[float], live: list[float],
                       rng: random.Random | None = None) -> tuple[float, float]:
    """Return (p_upper, p_lower) in one pass.

    p_upper = P(stat >= observed)   -- use for PROMOTE test
    p_lower = P(stat <= observed)   -- use for REJECT test
    """
    n_s, n_l = len(shadow), len(live)
    n = n_s + n_l
    if n_s == 0 or n_l == 0:
        return 1.0, 1.0
    observed = mean(shadow) - mean(live)
    combined = list(shadow) + list(live)
    if rng is None:
        rng = random.Random()

    if n <= 8:
        ge = le = total = 0
        for idx in combinations(range(n), n_s):
            sset = set(idx)
            s = [combined[i] for i in idx]
            l = [combined[i] for i in range(n) if i not in sset]
            stat = mean(s) - mean(l)
            total += 1
            if stat >= observed:
                ge += 1
            if stat <= observed:
                le += 1
        denom = total if total else 1
        return ge / denom, le / denom

    m = M_MONTE_CARLO
    ge = le = 0
    buf = combined[:]
    for _ in range(m):
        rng.shuffle(buf)
        stat = mean(buf[:n_s]) - mean(buf[n_s:])
        if stat >= observed:
            ge += 1
        if stat <= observed:
            le += 1
    return ge / m, le / m


def permutation_p(shadow: list[float], live: list[float], rng: random.Random | None = None) -> float:
    """One-tailed upper p: P(shuffled_stat >= observed_stat). Legacy wrapper."""
    return permutation_p_both(shadow, live, rng=rng)[0]


def decide(shadow: list[float], live: list[float], rng: random.Random | None = None) -> dict:
    n_s, n_l = len(shadow), len(live)
    if n_s == 0 or n_l == 0:
        return {
            'signal': 'no_data',
            'p_value': None,
            'n_shadow': n_s,
            'n_live': n_l,
            'observed_diff': None,
            'timestamp': _now(),
        }
    observed = mean(shadow) - mean(live)
    p_upper, p_lower = permutation_p_both(shadow, live, rng=rng)
    if p_upper <= ALPHA and observed > 0:
        signal = 'PROMOTE'
    elif p_lower <= ALPHA and observed < 0:
        signal = 'REJECT'
    else:
        signal = 'NO_SIGNAL'
    p = p_upper  # canonical p_value = upper tail (PROMOTE direction)
    return {
        'signal': signal,
        'p_value': p,
        'n_shadow': n_s,
        'n_live': n_l,
        'observed_diff': observed,
        'timestamp': _now(),
    }


def load_groups() -> tuple[list[float], list[float]]:
    records: list[dict] = []
    for path in _shadow_jsonl_files():
        records.extend(_load_jsonl(path))
    shadow, live = _split_shadow_live(records)
    if shadow and live:
        return shadow, live
    cal = CACHE / 'calibration-log.jsonl'
    if cal.is_file():
        shadow, live = _split_by_model(_load_jsonl(cal))
    return shadow, live


def run() -> dict:
    try:
        shadow, live = load_groups()
        if not shadow or not live:
            result = {'signal': 'no_data', 'p_value': None, 'n_shadow': 0,
                   'n_live': 0, 'observed_diff': None, 'timestamp': _now()}
        else:
            result = decide(shadow, live)
        try:
            _atomic_write(OUT_PATH, result)
        except Exception:
            pass
        return result
    except Exception:
        result = {'signal': 'no_data', 'p_value': None, 'n_shadow': 0,
                   'n_live': 0, 'observed_diff': None, 'timestamp': _now()}
        try:
            _atomic_write(OUT_PATH, result)
        except Exception:
            pass
        return result


def self_test() -> int:
    rng_data = random.Random(42)
    group_a = [rng_data.gauss(1.0, 0.5) for _ in range(20)]
    group_b = [rng_data.gauss(0.0, 0.5) for _ in range(20)]
    # A clearly better than B (shadow vs live)
    better = decide(group_a, group_b, rng=random.Random(123))
    assert better['p_value'] is not None and better['p_value'] < 0.15, better
    assert better['observed_diff'] > 0, better
    for k in REQUIRED_FIELDS:
        assert k in better, k

    ident_rng = random.Random(42)
    ident_a = [ident_rng.gauss(0.0, 0.5) for _ in range(20)]
    ident_rng2 = random.Random(42)
    ident_b = [ident_rng2.gauss(0.0, 0.5) for _ in range(20)]
    same = decide(ident_a, ident_b, rng=random.Random(99))
    assert same['p_value'] is not None and same['p_value'] > 0.3, same
    for k in REQUIRED_FIELDS:
        assert k in same, k

    # exact path smoke: N <= 8
    tiny = decide([3.0, 4.0, 5.0], [0.0, 0.5, 1.0], rng=random.Random(1))
    assert tiny['n_shadow'] + tiny['n_live'] <= 8
    assert 0.0 <= tiny['p_value'] <= 1.0
    for k in REQUIRED_FIELDS:
        assert k in tiny, k

    # REJECT test: shadow clearly worse than live
    rng_rej = random.Random(42)
    group_worse = [rng_rej.gauss(0.0, 0.5) for _ in range(20)]   # shadow worse
    group_better = [rng_rej.gauss(1.0, 0.5) for _ in range(20)]  # live better
    worse = decide(group_worse, group_better, rng=random.Random(77))
    assert worse['observed_diff'] < 0, worse
    assert worse['p_value'] is not None and worse['p_value'] > 0.5, worse  # upper-tail p ~1
    # p_lower (REJECT direction) must be small for clearly worse shadow
    _, p_lower = permutation_p_both(group_worse, group_better, rng=random.Random(77))
    assert p_lower <= 0.15, f"REJECT tail too large: p_lower={p_lower}"
    assert worse['signal'] == 'REJECT', worse

    # no_data schema check
    empty = decide([], [1.0, 2.0])
    for k in REQUIRED_FIELDS:
        assert k in empty, f"no_data missing field: {k}"

    print('self-test ok', {
        'better_p': better['p_value'],
        'better_signal': better['signal'],
        'same_p': same['p_value'],
        'same_signal': same['signal'],
        'tiny_p': tiny['p_value'],
        'reject_signal': worse['signal'],
        'reject_p_lower': p_lower,
    })
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if '--self-test' in args:
        try:
            return self_test()
        except AssertionError as e:
            print('self-test FAILED:', e, file=sys.stderr)
            return 1
        except Exception as e:
            print('self-test ERROR:', type(e).__name__, e, file=sys.stderr)
            return 1
    result = run()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
