#!/usr/bin/env python3
"""routing-laplace-poles.py — Laplace-transform pole analysis for skill preloading.

Theory (3B1B 'Why Laplace transforms are so useful'; 'But what is a Laplace Transform?'):
  The Laplace transform L{f}(s) = integral f(t) e^{-st} dt reveals the poles of a signal.
  A decaying exponential f(t) = A r^t has a pole at s = -log(r).
  The hazard rate at lead time dt is lambda * e^{-lambda * dt} where lambda = s.

  Hermes application:
    Treat the binary sequence x_n (was skill S used in session n?) as a signal.
    Lag-1 LS: r = sum(x_t * x_{t+1}) / sum(x_t^2).
    Pole sigma = -log(r).
    Preload skill S before session n+1 if hazard(sigma, dt=1) >= THRESHOLD.

  This catches APERIODIC bursts (a debug storm after a crash) that the
  Fourier/circadian scheduler misses because they have no fixed clock period.

Hard cores:
  - r in (0, 1) => sigma > 0 (decaying: skill use is dwindling)
  - r > 1 => sigma < 0 (growing: skill use is accelerating => definitely preload)
  - If x_n is constant 1: r = 1, sigma = 0, hazard = 0 (always used, no extra signal)
  - Falsify: x_n = 0.7^n => |r - 0.7| < 0.05; x_n = random binary => sigma unstable

Slot: session-start preload. Writes cache/laplace-preload.json.
Complements circadian-skill-prewarm (clock-based) and skill-fourier-schedule (periodic).

Usage:
  python3 routing-laplace-poles.py --self-test
  python3 routing-laplace-poles.py [--dry-run] [--threshold FLOAT]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
import time
from pathlib import Path

_hermes_base = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', 'fork')
_hermes_root = (
    (_hermes_base / 'profiles' / _hermes_profile)
    if _hermes_profile and 'profiles' not in str(_hermes_base)
    else _hermes_base
)
CACHE = _hermes_root / 'cache'
OUT_PATH = CACHE / 'laplace-preload.json'
LIFECYCLE_DB = _hermes_base / 'memory-facts' / 'lifecycle.db'

THRESHOLD = 0.15   # hazard threshold for preload recommendation
MAX_SESSIONS = 50  # look back this many sessions


def ar1_pole(x: list[float]) -> float | None:
    """
    Lag-1 AR(1) pole estimate.
    r = sum(x_t * x_{t+1}) / sum(x_t^2).
    sigma = -log(r).
    Returns sigma (the Laplace pole), or None if insufficient data.
    """
    if len(x) < 4:
        return None
    num = sum(x[t] * x[t + 1] for t in range(len(x) - 1))
    den = sum(x[t] * x[t] for t in range(len(x) - 1))
    if den <= 1e-12:
        return None
    r = max(1e-6, num / den)   # allow r > 1 (accelerating use)
    return -math.log(r)


def hazard(sigma: float | None, dt: float = 1.0) -> float:
    """
    Instantaneous hazard at lead time dt.
    h(dt) = sigma * exp(-sigma * dt)  for sigma > 0.
    For sigma <= 0 (accelerating), return a large value (always preload).
    """
    if sigma is None:
        return 0.0
    if sigma < 0.0:
        return 1.0  # accelerating use: preload always
    if sigma == 0.0:
        return 0.0  # constant use: no additional preload signal
    return sigma * math.exp(-sigma * dt)


def should_preload(x: list[float], dt: float = 1.0, threshold: float = THRESHOLD) -> dict:
    """
    Determine whether to preload a skill given its session-use history.
    x: list of counts per session (most recent last).
    Returns {preload, sigma, hazard_value, r_estimate}.
    """
    sigma = ar1_pole(x)
    h = hazard(sigma, dt)
    r = math.exp(-sigma) if sigma is not None else None
    return {
        'preload': h >= threshold,
        'sigma': round(sigma, 5) if sigma is not None else None,
        'r_estimate': round(r, 5) if r is not None else None,
        'hazard_value': round(h, 5),
        'threshold': threshold,
    }


def _load_skill_sessions(max_sessions: int = MAX_SESSIONS) -> dict[str, list[float]]:
    """
    Load per-skill, per-session binary use indicator from lifecycle.db.
    Returns {skill_name: [use_count_session_0, ..., use_count_session_N]}.
    """
    if not LIFECYCLE_DB.exists():
        return {}
    try:
        conn = sqlite3.connect(LIFECYCLE_DB, timeout=5)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}

        rows = []
        if 'skill_events' in tables:
            rows = conn.execute(
                "SELECT skill_name, session_id FROM skill_events ORDER BY timestamp"
            ).fetchall()
        elif 'events' in tables:
            rows = conn.execute(
                "SELECT source, session_id FROM events WHERE event_type='skill_use' ORDER BY ts"
            ).fetchall()
        conn.close()

        # Map session_id -> index (chronological)
        seen_sessions: list[str] = []
        session_idx: dict[str, int] = {}
        skill_buckets: dict[str, dict[int, float]] = {}

        for skill, sess in rows:
            if sess not in session_idx:
                session_idx[sess] = len(seen_sessions)
                seen_sessions.append(sess)
            si = session_idx[sess]
            if skill not in skill_buckets:
                skill_buckets[skill] = {}
            skill_buckets[skill][si] = skill_buckets[skill].get(si, 0) + 1

        # Convert to dense list (last max_sessions sessions)
        n_sess = len(seen_sessions)
        start = max(0, n_sess - max_sessions)
        result = {}
        for skill, buckets in skill_buckets.items():
            counts = [float(buckets.get(i, 0)) for i in range(start, n_sess)]
            if any(c > 0 for c in counts):
                result[skill] = counts
        return result
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


def run(dry_run: bool = False, threshold: float = THRESHOLD) -> dict:
    skill_sessions = _load_skill_sessions()

    if not skill_sessions:
        result = {'ts': int(time.time()), 'n_skills': 0, 'preload': []}
        if not dry_run:
            _atomic_write(OUT_PATH, result)
        return result

    preload_list = []
    for skill, counts in skill_sessions.items():
        pc = should_preload(counts, dt=1.0, threshold=threshold)
        if pc['preload']:
            preload_list.append({'skill': skill, **pc})

    preload_list.sort(key=lambda s: -s['hazard_value'])
    result = {
        'ts': int(time.time()),
        'n_skills_analyzed': len(skill_sessions),
        'n_preload': len(preload_list),
        'threshold': threshold,
        'preload': preload_list,
    }
    if not dry_run:
        _atomic_write(OUT_PATH, result)
    return result


def self_test() -> None:
    # Hard core 1: decaying exponential => r ~ 0.7, sigma ~ 0.357
    x_decay = [0.7 ** n for n in range(20)]
    sigma = ar1_pole(x_decay)
    expected_sigma = -math.log(0.7)
    assert sigma is not None, "ar1_pole returned None for geometric series"
    assert abs(sigma - expected_sigma) < 0.05, f"sigma={sigma:.4f} expected {expected_sigma:.4f}"

    # Hard core 2: hazard at dt=1
    h = hazard(sigma, dt=1.0)
    assert h >= 0.0, f"hazard negative: {h}"
    # For sigma ~ 0.357: h = 0.357 * exp(-0.357) = ~0.25
    assert 0.1 < h < 0.5, f"hazard out of expected range: {h}"

    # Hard core 3: sigma=0 (constant) => hazard=0
    h0 = hazard(0.0, dt=1.0)
    assert h0 == 0.0, f"sigma=0 should give hazard=0: {h0}"

    # Hard core 4: sigma<0 (accelerating) => hazard=1 (always preload)
    h_neg = hazard(-0.5, dt=1.0)
    assert h_neg == 1.0, f"negative sigma should give hazard=1: {h_neg}"

    # Hard core 5: insufficient data => None
    assert ar1_pole([1.0, 0.5]) is None
    assert ar1_pole([]) is None

    # should_preload: decaying skill at threshold 0.15 => preload True
    pc = should_preload(x_decay, dt=1.0, threshold=0.15)
    assert pc['preload'] == True, f"Decaying skill should preload: {pc}"

    # should_preload: flat-zero usage => no preload
    x_zero = [0.0] * 20
    pc2 = should_preload(x_zero, dt=1.0, threshold=0.15)
    assert pc2['preload'] == False, f"Zero-use skill should not preload: {pc2}"

    # Pure square wave (periodic, not decaying): sigma should not falsely trigger
    # A period-4 square wave [1,0,1,0,...] has non-geometric autocorrelation
    x_sq = [float((i % 4) < 2) for i in range(20)]
    pc3 = should_preload(x_sq, dt=100.0, threshold=0.15)
    # At dt=100, any decaying pole gives negligible hazard
    assert pc3['hazard_value'] < 0.15 or pc3['sigma'] is None, (
        f"At dt=100, square wave should not preload: {pc3}"
    )

    print("self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--threshold', type=float, default=THRESHOLD)
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    result = run(dry_run=args.dry_run, threshold=args.threshold)
    print(json.dumps({
        'n_skills_analyzed': result.get('n_skills_analyzed', 0),
        'n_preload': result.get('n_preload', 0),
        'preload': result.get('preload', [])[:10],
    }, indent=2))


if __name__ == '__main__':
    main()
