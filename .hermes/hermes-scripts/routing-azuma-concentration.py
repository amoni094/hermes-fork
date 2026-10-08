#!/usr/bin/env python3
"""routing-azuma-concentration.py — Azuma-Hoeffding tail on routing regret.

For a martingale-difference sequence |X_t|<=c, P(S_T >= eps) <= exp(-eps^2 / (2 T c^2)).
Alarm if observed cumulative regret exceeds the (1-delta) Azuma radius.

Source: Azuma (1967); Lugosi concentration; Borodin-El-Yaniv regret sequences.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

import os
from pathlib import Path
_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
_hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile and 'profiles' not in str(_hermes_base) else _hermes_base

DELTA = 0.05
C_BOUND = 1.0  # per-round regret in [0,1] after clipping


def _cache_dir() -> Path:
    override = os.environ.get('HERMES_CACHE_DIR', '').strip()
    p = Path(override) if override else (_hermes_root / 'cache')
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write_json(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n')
        os.replace(str(tmp), str(path))
    except Exception:
        try:
            tmp = path.with_suffix(path.suffix + '.tmp')
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def _load_jsonl(path: Path) -> list:
    rows = []
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except (OSError, FileNotFoundError):
        pass
    return rows


def azuma_radius(t: int, c: float = C_BOUND, delta: float = DELTA) -> float:
    """eps s.t. P(S_T >= eps) <= delta  =>  eps = c * sqrt(2 T log(1/delta))."""
    t = max(t, 1)
    return c * math.sqrt(2.0 * t * math.log(1.0 / max(delta, 1e-15)))


def azuma_tail(s: float, t: int, c: float = C_BOUND) -> float:
    if t <= 0:
        return 1.0
    return math.exp(- (s * s) / (2.0 * t * c * c))


def compute(rows: list, delta: float = DELTA, n_skills: int = 1) -> dict:
    """ADV21-005: apply Azuma to centered martingale differences, not raw cumulative regret."""
    regrets = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        v = r.get('regret')
        if isinstance(v, (int, float)) and math.isfinite(v):
            regrets.append(float(v))
    t = len(regrets)
    # Convert to incremental differences (martingale differences)
    diffs = [regrets[i] - regrets[i-1] for i in range(1, t)] if t > 1 else regrets
    # Center by EXP3 expected per-round regret: E[r_t] = sqrt(2 n log(n) / T)
    n = max(n_skills, 2)
    exp3_per_round = math.sqrt(2.0 * n * math.log(n) / max(t, 1))
    # Centered sum of differences
    centered = [d - exp3_per_round for d in diffs]
    s_centered = sum(centered)
    t_eff = max(len(centered), 1)
    radius = azuma_radius(t_eff, C_BOUND, delta)
    tail = azuma_tail(abs(s_centered), t_eff)
    alarm = abs(s_centered) > radius
    return {
        'ts': time.time(),
        'T': t,
        'S_T_raw': round(regrets[-1] if regrets else 0.0, 6),
        'S_T_centered': round(s_centered, 6),
        'azuma_radius': round(radius, 6),
        'azuma_tail_p': round(min(1.0, tail), 8),
        'delta': delta,
        'alarm': alarm,
        'reason': 'centered_regret_exceeds_radius' if alarm else 'ok',
    }


def run(cache: Path | None = None) -> dict:
    cache = cache or _cache_dir()
    rows = _load_jsonl(cache / 'routing-regret-log.jsonl')
    result = compute(rows)
    try:
        _atomic_write_json(cache / 'routing-azuma-concentration.json', result)
    except Exception:
        pass
    return result


def self_test() -> dict:
    failures = []
    try:
        r = azuma_radius(100, 1.0, 0.05)
        assert r > 0
        assert azuma_tail(0, 10) == 1.0 or azuma_tail(0, 10) >= 0.99
        assert azuma_tail(50, 100) < 0.5
    except Exception as e:
        failures.append(f'formula: {e}')
    try:
        rows = [{'regret': 0.01 * i} for i in range(20)]
        r = compute(rows)
        assert r['alarm'] is False, f"stable regret should not alarm: {r}"
        # Large jumps: centered diffs >> radius
        r2 = compute([{'regret': 100.0 * i} for i in range(20)], n_skills=2)
        assert r2['alarm'] is True, f"large regret jumps should alarm: {r2}"
    except Exception as e:
        failures.append(f'alarm: {e}')
    try:
        with tempfile.TemporaryDirectory() as td:
            r = run(cache=Path(td))
            assert r['T'] == 0
            json.dumps(r)
    except Exception as e:
        failures.append(f'missing: {e}')
    return {'self_test': 'PASS' if not failures else 'FAIL', 'n_failures': len(failures), 'failures': failures}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        r = self_test()
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['self_test'] == 'PASS' else 1)
    try:
        print(json.dumps(run(), indent=2))
    except Exception:
        print(json.dumps({'error': 'shadow_path_failed'}))
        sys.exit(0)


if __name__ == '__main__':
    main()
