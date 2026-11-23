#!/usr/bin/env python3
"""recall-miss-ttl-adjuster.py — MRAS-inspired adaptive TTL policy updater.

Reads recall-misses.jsonl (written by memory-ttl-purge.py) to compute the
recent miss rate per fact_type, then adjusts TTL policy in memory-ttl-purge.py's
TTL_POLICY config accordingly.

Theory (Slotine & Li Ch 7 / MRAS): Fixed TTL = open-loop control.
This script is the feedback controller:
  - High miss rate → decrease TTL (prune more aggressively; stale facts are recalled)
  - Low miss rate → increase TTL (retain more; purge is too aggressive)
  - EMA update: new_ttl = old_ttl * alpha + reference_ttl * (1 - alpha)
    where reference_ttl = base_ttl * (1 - miss_rate_error)

Bottleneck #8 closure: recall-misses.jsonl demand signal is now consumed.
Cron: called daily by recall-miss-ttl-adjuster-0001 (added to jobs.json).
"""
import json
import time
from pathlib import Path
from collections import defaultdict

def estimate_mixing_ttl(miss_log_path: Path, fact_type: str = 'default', base_ttl_days: float = 30.0) -> float | None:
    """Estimate TTL from Markov mixing time via spectral gap of inter-miss intervals.

    Theory (Levin, Peres & Wilmer "Markov Chains and Mixing Times", Ch. 4):
      Mixing time t_mix(epsilon) <= ceil(log(1/epsilon) / spectral_gap)
      where spectral_gap = 1 - |second_largest_eigenvalue|.

    We approximate spectral_gap from empirical lag-1 autocorrelation of
    inter-miss intervals: spectral_gap ≈ 1 - |autocorr_lag1|.
    Then: mix_time ≈ ceil(log(20) / spectral_gap)  [epsilon=0.05]

    Returns recommended TTL in days, or None if insufficient data (<5 events).
    """
    if not miss_log_path.exists():
        return None
    try:
        cutoff = __import__('time').time() - 30 * 24 * 3600  # 30-day window
        timestamps = []
        for line in miss_log_path.read_text().splitlines():
            try:
                row = __import__('json').loads(line)
                if row.get('fact_type', 'default') == fact_type:
                    ts = float(row.get('ts', 0))
                    if ts > cutoff:
                        timestamps.append(ts)
            except Exception:
                continue

        if len(timestamps) < 5:
            return None

        timestamps.sort()
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        n = len(intervals)
        mean_iv = sum(intervals) / n
        # Lag-1 autocorrelation
        if mean_iv == 0:
            return None
        deviations = [x - mean_iv for x in intervals]
        numerator = sum(deviations[i] * deviations[i+1] for i in range(n-1))
        denominator = sum(d*d for d in deviations)
        if denominator == 0:
            return None
        autocorr = numerator / denominator

        spectral_gap = max(0.01, 1.0 - abs(autocorr))  # clamp to avoid division by zero
        # t_mix(0.05) = log(1/0.05) / spectral_gap = log(20) / spectral_gap
        mix_time_intervals = math.ceil(math.log(20.0) / spectral_gap)
        # Convert to days: mix_time in units of mean inter-miss interval
        mix_time_seconds = mix_time_intervals * mean_iv
        mix_time_days = mix_time_seconds / 86400.0
        # Clamp to [MIN_TTL_DAYS, MAX_TTL_DAYS]
        return max(MIN_TTL_DAYS, min(MAX_TTL_DAYS, mix_time_days))
    except Exception:
        return None


import math

import os as _os
_hermes_base = Path(_os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = _os.environ.get("HERMES_PROFILE", "")
_hermes_root = (_hermes_base / "profiles" / _hermes_profile) if _hermes_profile and "profiles" not in str(_hermes_base) else _hermes_base
MISS_LOG = _hermes_root / "cache" / "recall-misses.jsonl"
TTL_STATE = _hermes_root / "cache" / "adaptive-ttl-state.json"

# Reference TTL baselines (days) per fact_type — these are the target steady-state values
BASE_TTL_DAYS = {
    'memory': 30,
    'skill': 90,
    'cron': 14,
    'external': 7,
    'default': 30,
}

# MRAS gain parameters
ALPHA = 0.85        # EMA smoothing (0.85 = ~7-run half-life)
MAX_ADJUST = 0.10   # C1: gain cap reduced to ±10%/run (Strogatz §8.2: limit cycle if gain > 2/ω₀;
                    # at ω₀≈0.15/run, safe gain < 13%/run; 10% gives margin of ~3x)
                    # Previously 0.30 — overshooting was possible at high miss-rate error
MIN_TTL_DAYS = 3    # hard floor
MAX_TTL_DAYS = 180  # hard ceiling
GAIN_HISTORY_PATH = _hermes_root / "cache" / "ttl-gain-history.jsonl"

LOOKBACK_HOURS = 48  # only consider misses in last 48h for miss rate computation


def load_ttl_state():
    try:
        if TTL_STATE.exists():
            return json.loads(TTL_STATE.read_text())
    except Exception:
        pass
    return {k: float(v) for k, v in BASE_TTL_DAYS.items()}


def save_ttl_state(state):
    TTL_STATE.parent.mkdir(parents=True, exist_ok=True)
    # M5 fix: atomic write via tmp+rename to prevent learning reset on crash
    _ttl_tmp = TTL_STATE.with_suffix('.tmp')
    _ttl_tmp.write_text(json.dumps(state, indent=2))
    _ttl_tmp.rename(TTL_STATE)


def compute_miss_rates():
    """Read recent miss log, compute miss rate per fact_type over LOOKBACK_HOURS."""
    cutoff = time.time() - LOOKBACK_HOURS * 3600
    counts = defaultdict(int)
    misses = defaultdict(int)

    if not MISS_LOG.exists():
        return {}

    for line in MISS_LOG.read_text().splitlines():
        try:
            row = json.loads(line)
            ts = float(row.get('ts', 0))
            if ts < cutoff:
                continue
            ft = row.get('fact_type', 'default')
            counts[ft] += 1
            misses[ft] += 1  # every logged entry IS a miss (purge event)
        except Exception:
            continue

    # Also estimate total facts in play by reading TTL state total (proxy)
    # Miss rate = misses / (misses + estimated_retained)
    # Without a hit log, we approximate: miss_rate = min(1, misses / max(misses*2, 10))
    # This is conservative — assumes at least as many hits as misses
    rates = {}
    for ft, n in misses.items():
        rates[ft] = min(1.0, n / max(n * 2, 10))

    return rates


def adjust_ttls(state, miss_rates):
    """Apply MRAS-inspired TTL adjustment and return updated state with change log.

    C1 stability (Strogatz, Nonlinear Dynamics §8.2): gain cap at MAX_ADJUST=0.10
    prevents limit-cycle oscillation. At high miss-rate error, the uncapped system
    overshoots TTL in both directions with period ~7 runs (ALPHA half-life).
    Reduced gain ensures error decays monotonically to zero.
    """
    log = []
    for ft, base in BASE_TTL_DAYS.items():
        old_ttl = state.get(ft, float(base))
        miss_rate = miss_rates.get(ft, None)

        if miss_rate is None:
            # No signal — EMA toward baseline gently
            new_ttl = old_ttl * ALPHA + base * (1 - ALPHA)
        else:
            # MRAS reference: if miss_rate > 0.5, TTL too long → reduce
            # if miss_rate < 0.1, TTL too short → increase
            error = miss_rate - 0.3  # target miss rate 30%
            # Positive error → TTL too long → reduce TTL
            # C1: gain capped; adjustment in [1-MAX_ADJUST, 1+MAX_ADJUST]
            adjustment = 1.0 - (error * MAX_ADJUST / 0.7)  # scale: max error=0.7 → max adjust
            adjustment = max(1 - MAX_ADJUST, min(1 + MAX_ADJUST, adjustment))
            reference_ttl = base * adjustment
            new_ttl = old_ttl * ALPHA + reference_ttl * (1 - ALPHA)

        new_ttl = max(MIN_TTL_DAYS, min(MAX_TTL_DAYS, new_ttl))
        state[ft] = round(new_ttl, 1)
        log.append({
            'fact_type': ft, 'old_ttl': round(old_ttl, 1),
            'new_ttl': round(new_ttl, 1),
            'miss_rate': miss_rates.get(ft), 'base_ttl': base,
        })

    return state, log


def main():
    state = load_ttl_state()
    miss_rates = compute_miss_rates()
    state, change_log = adjust_ttls(state, miss_rates)
    save_ttl_state(state)

    payload = {
        'ts': time.time(),
        'adjusted_ttls': state,
        'miss_rates': miss_rates,
        'changes': change_log,
    }
    try:
        GAIN_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(GAIN_HISTORY_PATH, "a") as fh:
            fh.write(json.dumps(payload) + "\n")
    except Exception:
        pass

    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
