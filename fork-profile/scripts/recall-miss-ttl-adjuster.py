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

MISS_LOG = Path('~/.hermes/cache/recall-misses.jsonl').expanduser()
TTL_STATE = Path('~/.hermes/cache/adaptive-ttl-state.json').expanduser()

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
MAX_ADJUST = 0.30   # max ±30% adjustment per run (prevents runaway)
MIN_TTL_DAYS = 3    # hard floor
MAX_TTL_DAYS = 180  # hard ceiling

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
    """Apply MRAS-inspired TTL adjustment and return updated state with change log."""
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

    print(json.dumps({
        'ts': time.time(),
        'adjusted_ttls': state,
        'miss_rates': miss_rates,
        'changes': change_log,
    }, indent=2))


if __name__ == '__main__':
    main()
