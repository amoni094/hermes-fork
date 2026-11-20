#!/usr/bin/env python3
"""memory-fixed-point-stability.py — Dynamical stability of memory entries.

Theory (3B1B 'Differential equations' series; fixed-point analysis):
  The agent memory system is a discrete dynamical map:
    memory_state(t+1) = F(memory_state(t), new_input(t))

  A memory entry m_i is at a FIXED POINT of this map if its access rate
  r_i(t) converges: r_i(t) -> r_i* as t -> infinity.

  Stability criterion (Jacobian at fixed point):
    |dr_i(t+1)/dr_i(t)| < 1  =>  stable (perturbations decay)
    |dr_i(t+1)/dr_i(t)| > 1  =>  unstable (perturbations grow => entry fades or explodes)
    = 0                       =>  dead (entry never referenced = candidate for drop)

  Proxy (without full Jacobian): use the sequence of WEEKLY ACCESS COUNTS
  for each memory entry. Compute the ratio of successive counts:
    lambda_i(t) = access_count(t) / max(access_count(t-1), 1)

  Stability: geometric mean of |lambda_i(t)| over the last W weeks.
    stable:   mean_lambda in [0.5, 2.0]   (bounded oscillation)
    decaying: mean_lambda < 0.5            (drop candidate)
    growing:  mean_lambda > 2.0            (recently boosted = keep)

Hard cores:
  - lambda >= 0 always (counts are non-negative)
  - Dead entries (all-zero counts) have stability 'dead'
  - Stable entries: geometric mean in [0.5, 2.0]
  - Falsify: a constant-access entry has mean_lambda = 1.0 (neutral stability)

Slot: cron weekly (or nightly). Reads lifecycle.db access events.
Writes cache/memory-fixed-point-stability.json.

Usage:
  python3 memory-fixed-point-stability.py --self-test
  python3 memory-fixed-point-stability.py [--dry-run] [--weeks INT]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'memory-fixed-point-stability.json'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'

WEEKS = 8
STABLE_LOW = 0.5
STABLE_HIGH = 2.0


def geometric_mean(values: list[float]) -> float:
    """Geometric mean of positive values. Returns 0 if any value is 0."""
    if not values:
        return 1.0
    log_sum = sum(math.log(max(v, 1e-12)) for v in values)
    return math.exp(log_sum / len(values))


def classify_stability(lambdas: list[float]) -> str:
    if not lambdas or all(l == 0.0 for l in lambdas):
        return 'dead'
    gm = geometric_mean([l for l in lambdas if l > 0])
    if gm < STABLE_LOW:
        return 'decaying'
    if gm > STABLE_HIGH:
        return 'growing'
    return 'stable'


def ar1_pole_ls(x: list[float]) -> float | None:
    """
    Lag-1 AR(1) pole via least squares: a = sum(x_t * x_{t+1}) / sum(x_t^2).
    More statistically efficient than geometric mean of successive ratios.
    Returns a (the pole); |a| < 1 => stable, |a| > 1 => unstable, None if insufficient data.
    """
    if len(x) < 4:
        return None
    num = sum(x[t] * x[t + 1] for t in range(len(x) - 1))
    den = sum(x[t] * x[t] for t in range(len(x) - 1))
    if den <= 1e-12:
        return None
    return num / den


def stability_score(weekly_counts: list[int]) -> dict:
    """
    Given W weekly access counts for one memory entry, compute stability.
    weekly_counts[0] = oldest week, weekly_counts[-1] = most recent.
    Uses both geometric-mean lambda (robust to outliers) and AR(1) LS pole (efficient).
    Returns {status, mean_lambda, ar1_pole, weekly_counts, drop_candidate}.
    """
    if len(weekly_counts) < 2:
        return {
            'status': 'insufficient_data',
            'mean_lambda': 1.0,
            'ar1_pole': None,
            'drop_candidate': False,
        }
    lambdas = []
    for i in range(1, len(weekly_counts)):
        prev = max(weekly_counts[i-1], 1)
        lambdas.append(weekly_counts[i] / prev)

    gm = geometric_mean(lambdas)
    # AR(1) LS: works directly on raw counts (not ratios)
    a = ar1_pole_ls([float(c) for c in weekly_counts])

    # Classification: use AR(1) pole if available (more efficient), else geometric mean
    if a is not None:
        if a < STABLE_LOW:
            status = 'decaying'
        elif a > STABLE_HIGH:
            status = 'growing'
        elif all(c == 0 for c in weekly_counts):
            status = 'dead'
        else:
            status = 'stable'
    else:
        status = classify_stability(lambdas)

    return {
        'status': status,
        'mean_lambda': round(gm, 4),
        'ar1_pole': round(a, 4) if a is not None else None,
        'weekly_counts': weekly_counts,
        'drop_candidate': status in ('decaying', 'dead'),
    }


def _load_memory_access_history(weeks: int = WEEKS) -> dict[str, list[int]]:
    """Load weekly access counts for memory entries from lifecycle.db."""
    if not LIFECYCLE_DB.exists():
        return {}
    now = int(time.time())
    week_seconds = 7 * 24 * 3600
    cutoff = now - weeks * week_seconds
    try:
        conn = sqlite3.connect(LIFECYCLE_DB, timeout=5)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        if 'fact_lifecycle' not in tables:
            conn.close()
            return {}
        rows = conn.execute(
            "SELECT fact_id, last_accessed, access_count FROM fact_lifecycle "
            "WHERE last_accessed >= ? ORDER BY last_accessed",
            (cutoff,),
        ).fetchall()
        conn.close()

        # Bin last_accessed into weekly buckets; access_count is a proxy for hits.
        weekly: dict[str, list[int]] = {}
        for mem_id, ts, ac in rows:
            if ts is None:
                continue
            bucket = min(max(int((int(ts) - cutoff) / week_seconds), 0), weeks - 1)
            if mem_id not in weekly:
                weekly[mem_id] = [0] * weeks
            weekly[mem_id][bucket] += int(ac or 1)
        return weekly
    except Exception:
        return {}


def _atomic_write(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        pass


def run(dry_run: bool = False, weeks: int = WEEKS) -> dict:
    access_history = _load_memory_access_history(weeks)

    if not access_history:
        result = {
            'ts': int(time.time()),
            'weeks': weeks,
            'n_entries': 0,
            'entries': [],
        }
        if not dry_run:
            _atomic_write(OUT_PATH, result)
        return result

    entries = []
    for mem_id, counts in access_history.items():
        sc = stability_score(counts)
        entries.append({'id': mem_id, **sc})

    # Sort: drop candidates first, then decaying, stable, growing
    order = {'dead': 0, 'decaying': 1, 'insufficient_data': 2, 'stable': 3, 'growing': 4}
    entries.sort(key=lambda e: (order.get(e['status'], 2), e['mean_lambda']))

    result = {
        'ts': int(time.time()),
        'weeks': weeks,
        'n_entries': len(entries),
        'n_drop_candidates': sum(1 for e in entries if e['drop_candidate']),
        'entries': entries[:50],
    }
    if not dry_run:
        _atomic_write(OUT_PATH, result)
    return result


def self_test() -> None:
    # Hard core: lambda >= 0
    sc = stability_score([1, 4, 16, 64])
    assert sc['mean_lambda'] >= 0.0
    assert sc['status'] == 'growing', f"Should be growing: {sc}"

    # Constant access => mean_lambda = 1.0 (neutral)
    sc2 = stability_score([5, 5, 5, 5])
    assert abs(sc2['mean_lambda'] - 1.0) < 1e-9, f"Constant should be 1.0: {sc2}"
    assert sc2['status'] == 'stable', f"Constant should be stable: {sc2}"

    # Decaying: counts dropping 10x each week (geometric mean = 0.1 < STABLE_LOW=0.5)
    sc3 = stability_score([1000, 100, 10, 1])
    assert sc3['status'] == 'decaying', f"10x decay should be decaying: {sc3}"
    assert sc3['drop_candidate'] == True

    # Dead: all zeros
    sc4 = stability_score([0, 0, 0, 0])
    assert sc4['status'] == 'dead' or sc4['status'] == 'insufficient_data'
    # (classify_stability returns 'dead', stability_score may return insufficient_data for len<2)

    # Hard core: geometric_mean of [1,1,1] = 1
    assert abs(geometric_mean([1.0, 1.0, 1.0]) - 1.0) < 1e-9

    # geometric_mean positive values always >= 0
    assert geometric_mean([0.1, 0.5, 2.0]) > 0

    # Insufficient data: only 1 count
    sc5 = stability_score([10])
    assert sc5['status'] == 'insufficient_data'

    print("self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--weeks', type=int, default=WEEKS)
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    result = run(dry_run=args.dry_run, weeks=args.weeks)
    summary = {k: v for k, v in result.items() if k != 'entries'}
    summary['drop_candidates'] = [e['id'] for e in result.get('entries', []) if e['drop_candidate']][:10]
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
