#!/usr/bin/env python3
"""skill-fourier-schedule.py — Fourier analysis of cron execution history.

Theory (3B1B 'But what is a Fourier transform?'; DFT):
  A sequence of event counts x[0..N-1] sampled hourly over the last N hours
  has discrete Fourier transform X[k] = sum_{n=0}^{N-1} x[n] e^{-2pi i k n / N}.
  The magnitude |X[k]| is the AMPLITUDE at frequency k cycles / N hours.
  Peaks in |X[k]| reveal dominant periodicities (daily = k=N/24, weekly = k=N/168).

  Hermes application:
    Tool-call and skill-use events are sampled into hourly bins.
    Peaks in the DFT reveal when certain skill clusters recur.
    A skill cluster with a strong 24h periodicity should be PRE-LOADED
    at the peak hour minus a warm-up margin.

Hard cores:
  - |X[k]| >= 0 always (magnitude of complex number)
  - Parseval: sum |X[k]|^2 = N * sum |x[n]|^2 (energy conservation)
  - If x[n] is constant (no periodicity), all |X[k>0]| are 0 (flat spectrum)
  - Dominant frequency k_max -> period P = N / k_max hours

Slot: cron daily. Reads lifecycle.db for skill-use timestamps.
Writes cache/skill-fourier-schedule.json with dominant period + next peak hour.

Usage:
  python3 skill-fourier-schedule.py --self-test
  python3 skill-fourier-schedule.py [--dry-run] [--window-hours INT]
"""
from __future__ import annotations

import argparse
import cmath
import json
import math
import os
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)

CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'skill-fourier-schedule.json'
# lifecycle.db lives in the memory-facts subdirectory
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'

WINDOW_HOURS = 7 * 24   # 1 week of history


def dft(x: list[float]) -> list[complex]:
    """Naive O(N^2) DFT — fine for N <= 168 (1 week of hourly bins)."""
    N = len(x)
    return [
        sum(x[n] * cmath.exp(-2j * math.pi * k * n / N) for n in range(N))
        for k in range(N)
    ]


def find_dominant_periods(x: list[float], top_k: int = 3) -> list[dict]:
    """
    Compute DFT magnitudes, return top_k dominant non-DC frequencies.
    Returns list of {period_hours, amplitude, next_peak_hour}.
    """
    N = len(x)
    if N < 4:
        return []
    X = dft(x)
    # skip k=0 (DC component = mean); only first N//2 (positive freqs)
    magnitudes = [(abs(X[k]), k) for k in range(1, N // 2 + 1)]
    magnitudes.sort(reverse=True)

    now_hour = int(time.time() // 3600)
    results = []
    for amp, k in magnitudes[:top_k]:
        period_hours = N / k
        # phase of this frequency (in hours)
        phase_rad = cmath.phase(X[k])
        phase_hours = -phase_rad * N / (2 * math.pi)
        # next occurrence of the peak
        hours_since_peak = (now_hour - phase_hours) % period_hours
        next_peak_in = period_hours - hours_since_peak
        results.append({
            'frequency_k': k,
            'period_hours': round(period_hours, 2),
            'amplitude': round(amp, 4),
            'next_peak_in_hours': round(next_peak_in % period_hours, 2),
        })
    return results


def _load_skill_events(window_hours: int = WINDOW_HOURS) -> dict[str, list[float]]:
    """
    Load skill-use timestamps from lifecycle.db.
    Returns {skill_name: hourly_bin_counts [len=window_hours]}.
    """
    if not LIFECYCLE_DB.exists():
        return {}
    cutoff = int(time.time()) - window_hours * 3600
    bins: dict[str, list[float]] = {}
    try:
        conn = sqlite3.connect(LIFECYCLE_DB, timeout=5)
        # Try different possible schema shapes
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if 'skill_events' in tables:
            rows = conn.execute(
                "SELECT skill_name, timestamp FROM skill_events WHERE timestamp >= ? ORDER BY timestamp",
                (cutoff,)
            ).fetchall()
        elif 'events' in tables:
            rows = conn.execute(
                "SELECT source, ts FROM events WHERE ts >= ? AND event_type='skill_use' ORDER BY ts",
                (cutoff,)
            ).fetchall()
        else:
            conn.close()
            return {}
        conn.close()

        # Bin into hourly buckets
        start = int(time.time()) - window_hours * 3600
        for skill, ts in rows:
            bucket = min(int((ts - start) / 3600), window_hours - 1)
            if skill not in bins:
                bins[skill] = [0.0] * window_hours
            bins[skill][bucket] += 1.0
    except Exception:
        pass
    return bins


def _atomic_write(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    except Exception:
        pass


def run(dry_run: bool = False, window_hours: int = WINDOW_HOURS) -> dict:
    skill_bins = _load_skill_events(window_hours)

    if not skill_bins:
        # No events yet — write empty result
        result = {
            'ts': int(time.time()),
            'window_hours': window_hours,
            'n_skills': 0,
            'skills': [],
        }
        if not dry_run:
            _atomic_write(OUT_PATH, result)
        return result

    skills_out = []
    for skill, counts in skill_bins.items():
        periods = find_dominant_periods(counts, top_k=2)
        if periods:
            skills_out.append({
                'skill': skill,
                'total_events': int(sum(counts)),
                'dominant_periods': periods,
            })

    # Sort by amplitude of dominant period
    skills_out.sort(key=lambda s: -(s['dominant_periods'][0]['amplitude'] if s['dominant_periods'] else 0))

    result = {
        'ts': int(time.time()),
        'window_hours': window_hours,
        'n_skills': len(skills_out),
        'skills': skills_out[:20],  # top 20 by periodicity strength
    }
    if not dry_run:
        _atomic_write(OUT_PATH, result)
    return result


def self_test() -> None:
    # Hard core: magnitude >= 0
    x = [1.0, 0.0, -1.0, 0.0]  # 2-cycle sine
    X = dft(x)
    for c in X:
        assert abs(c) >= -1e-10, f"Magnitude negative: {c}"

    # Parseval: sum |X[k]|^2 = N * sum |x[n]|^2
    N = len(x)
    lhs = sum(abs(c)**2 for c in X)
    rhs = N * sum(v**2 for v in x)
    assert abs(lhs - rhs) < 1e-6, f"Parseval violated: {lhs} != {rhs}"

    # Constant signal: all X[k>0] = 0
    x_const = [3.0] * 8
    X_const = dft(x_const)
    for k in range(1, len(X_const)):
        assert abs(X_const[k]) < 1e-9, f"Non-zero X[{k}] for constant: {X_const[k]}"

    # 24h periodicity: signal with period 24 in 168 bins
    x_daily = [math.sin(2 * math.pi * i / 24) for i in range(168)]
    periods = find_dominant_periods(x_daily, top_k=1)
    assert len(periods) == 1
    assert abs(periods[0]['period_hours'] - 24.0) < 1.0, f"Expected 24h period: {periods}"
    assert periods[0]['amplitude'] > 0

    # find_dominant_periods: len <= top_k
    ps = find_dominant_periods([1.0, 2.0, 1.0, 2.0], top_k=2)
    assert len(ps) <= 2

    print("self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--window-hours', type=int, default=WINDOW_HOURS)
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    result = run(dry_run=args.dry_run, window_hours=args.window_hours)
    out = {k: v for k, v in result.items() if k != 'skills'}
    out['top_skills'] = result.get('skills', [])[:5]
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
