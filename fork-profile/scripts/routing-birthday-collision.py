#!/usr/bin/env python3
"""routing-birthday-collision.py — birthday collision bound on routing buckets.

P(n,d) = 1 - exp(-n*(n-1)/(2*d))
d_min(p) = n*(n-1) / (2 * log(1/(1-p)))
Alarm if P(n, current_d) > 0.01.
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

home = os.environ.get('HERMES_HOME', '')
home = home.removesuffix('/profiles/fork')
if not home:
    home = os.path.expanduser('~/.hermes')
profile_dir = home + '/profiles/fork'
CACHE = Path(profile_dir) / 'cache'
OUT_PATH = CACHE / 'routing-birthday-state.json'
P_THRESHOLD = 0.01


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def birthday_p(n: int, d: float) -> float:
    """Approximate collision probability P(n, d)."""
    n = int(n)
    d = float(d)
    if n <= 1:
        return 0.0
    if d <= 0:
        return 1.0
    x = n * (n - 1) / (2.0 * d)
    # 1 - exp(-x); clamp for overflow
    if x >= 700:
        return 1.0
    return 1.0 - math.exp(-x)


def d_min_for(n: int, p_threshold: float) -> float:
    """Minimum buckets so collision probability < p_threshold."""
    n = int(n)
    p = float(p_threshold)
    if n <= 1:
        return 1.0
    if p <= 0:
        return float('inf')
    if p >= 1:
        return 1.0
    denom = 2.0 * math.log(1.0 / (1.0 - p))
    return n * (n - 1) / denom


def _load_json(path: Path):
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    return obj


def _count_skills_from_weights(obj) -> int | None:
    if obj is None:
        return None
    if isinstance(obj, list):
        return len(obj)
    if not isinstance(obj, dict):
        return None
    for key in ('skills', 'weights', 'skill_weights', 'n_skills'):
        if key == 'n_skills':
            v = obj.get(key)
            if isinstance(v, (int, float)) and v >= 0:
                return int(v)
            continue
        inner = obj.get(key)
        if isinstance(inner, dict):
            return len(inner)
        if isinstance(inner, list):
            return len(inner)
    return len(obj)


def _count_skill_dirs() -> int:
    n = 0
    for root in (Path(profile_dir) / 'skills', Path(home) / 'skills'):
        if not root.is_dir():
            continue
        try:
            for child in root.iterdir():
                if child.is_dir() and (child / 'SKILL.md').is_file():
                    n += 1
            if n:
                return n
        except Exception:
            continue
    return n


def load_n_skills() -> int:
    for path in (
        CACHE / 'routing-exp3-skill-weights.json',
        CACHE / 'routing-weights.json',
        Path(home) / 'cache' / 'routing-exp3-skill-weights.json',
        Path(home) / 'cache' / 'routing-weights.json',
    ):
        if path.is_file():
            n = _count_skills_from_weights(_load_json(path))
            if n is not None and n > 10:   # skip 4-channel routing-weights
                return n
    return _count_skill_dirs()


def load_d(n: int) -> int:
    path = CACHE / 'skill-attention-router-state.json'
    obj = _load_json(path) if path.is_file() else None
    if isinstance(obj, dict):
        for key in ('num_categories', 'num_buckets'):
            v = obj.get(key)
            if isinstance(v, (int, float)) and v > 0:
                return int(v)
    # Default: assume bucket granularity ~ n (conservative; real d from router state is better)
    return max(100, int(n))


def compute_state(n: int, d: int, p_threshold: float = P_THRESHOLD) -> dict:
    p = birthday_p(n, d)
    dmin = d_min_for(n, p_threshold)
    return {
        'n_skills': int(n),
        'd_current': int(d),
        'p_collision': p,
        'd_min_for_1pct': dmin,
        'alarm': bool(p > p_threshold),
        'timestamp': _now(),
    }


def run() -> dict:
    try:
        n = load_n_skills()
        d = load_d(n)
        result = compute_state(n, d)
        try:
            _atomic_write(OUT_PATH, result)
        except Exception:
            pass
        return result
    except Exception:
        result = {
            'n_skills': 0,
            'd_current': 10,
            'p_collision': 0.0,
            'd_min_for_1pct': 1.0,
            'alarm': False,
            'timestamp': _now(),
        }
        try:
            _atomic_write(OUT_PATH, result)
        except Exception:
            pass
        return result


def self_test() -> int:
    p23 = birthday_p(23, 365)
    assert 0.49 <= p23 <= 0.52, p23
    dmin = d_min_for(23, 0.5)
    assert 340 <= dmin <= 390, dmin
    assert birthday_p(10, 1000) < 0.05, birthday_p(10, 1000)
    assert birthday_p(100, 10) > 0.99, birthday_p(100, 10)
    st = compute_state(100, 10, p_threshold=0.01)
    assert st['alarm'] is True, st
    assert st['p_collision'] > 0.01
    for k in ('n_skills', 'd_current', 'p_collision', 'd_min_for_1pct', 'alarm', 'timestamp'):
        assert k in st, k
    quiet = compute_state(2, 10000, p_threshold=0.01)
    assert quiet['alarm'] is False
    print('self-test ok', {
        'P(23,365)': p23,
        'd_min(23,0.5)': dmin,
        'P(10,1000)': birthday_p(10, 1000),
        'P(100,10)': birthday_p(100, 10),
        'alarm_high': st['alarm'],
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
