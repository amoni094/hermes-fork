#!/usr/bin/env python3
"""Skill spacing scheduler — ACT-R distributed-practice review.

Implements Anderson (1994) ACT-R activation decay with spaced-repetition
scheduling (Leitner 1972) to surface skills due for review.

Theory:
  ACT-R (Anderson & Lebiere 1998, 'The Atomic Components of Thought'):
    Activation A_i = ln(sum_j t_j^{-d}) where t_j = time since j-th practice,
    d = 0.5 (decay exponent). Skills with low activation are poorly retained.

  Simplified spacing interval (Wozniak & Gorzelany 1994, SuperMemo SM-2):
    next_review_gap = base_gap * (n_reviews + 1)^{1/d}
    At d=0.5: gap grows quadratically with review count.

  Distributed practice (Cepeda et al. 2006, Psych Bull 132(3)):
    Optimal inter-study interval for 30-day retention ≈ 10-20% of retention
    interval. We target 7-day retention -> review gap starts at 1 day, doubles
    each successful recall.

Usage:
  python3 skill-spacing-scheduler.py               # list overdue skills
  python3 skill-spacing-scheduler.py --all          # all skills with next-due
  python3 skill-spacing-scheduler.py --update NAME  # mark NAME as reviewed now
  python3 skill-spacing-scheduler.py --json         # JSON output
  python3 skill-spacing-scheduler.py --self-test    # unit tests

The scheduler reads skill_invocations from state.db (shared with
skill-yield-tracker.py) and writes review state to skill-spacing-state.json.
"""

import argparse
import json
import math
import os
import sqlite3
import sys
import time
from pathlib import Path

# ── Profile-aware paths ───────────────────────────────────────────────────────
_hermes_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_hermes_profile = os.environ.get("HERMES_PROFILE", "")
_hermes_root = (
    (_hermes_base / "profiles" / _hermes_profile)
    if _hermes_profile and "profiles" not in str(_hermes_base)
    else _hermes_base
)
DB_PATH = _hermes_root / "state.db"  # same DB as skill-yield-tracker.py
STATE_PATH = _hermes_root / "cache" / "skill-spacing-state.json"

# ── ACT-R parameters ──────────────────────────────────────────────────────────
_DECAY_D = 0.5          # Anderson (1994) decay exponent; d=0.5 is empirically validated
_BASE_GAP_DAYS = 1.0    # Initial review interval (days); Cepeda et al. 2006: ~10% of target
_MAX_GAP_DAYS = 90.0    # Cap: after 90 days without use, treat as cold
_MIN_INVOCATIONS = 3    # Only schedule skills with at least this many invocations

# ── ACT-R activation ──────────────────────────────────────────────────────────

def actr_activation(practice_times_ago_days: list[float], d: float = _DECAY_D) -> float:
    """Anderson (1994) ACT-R base-level activation.

    A = ln(sum_j t_j^{-d})

    where t_j is time since j-th practice in days. Returns -inf if no
    practices. Higher activation = better retained.

    Anderson, J.R. & Lebiere, C. (1998). 'The Atomic Components of Thought.'
    Lawrence Erlbaum. Chapter 4.
    """
    if not practice_times_ago_days:
        return float("-inf")
    total = sum(max(t, 0.001) ** (-d) for t in practice_times_ago_days)
    return math.log(total)


def next_review_gap_days(n_reviews: int, base: float = _BASE_GAP_DAYS, d: float = _DECAY_D) -> float:
    """Spacing interval from ACT-R decay exponent.

    From the SM-2 / ACT-R synthesis (Pavlik & Anderson 2005):
      gap = base * (n_reviews + 1)^{1/d}
    At d=0.5: gap = base * (n+1)^2.

    Pavlik, P.I. & Anderson, J.R. (2005). 'Practice and Forgetting Effects
    on Vocabulary Memory.' Cognitive Science 29(4): 559-586.
    Cepeda, N.J. et al. (2006). 'Distributed practice in verbal recall tasks.'
    Psychological Bulletin 132(3): 354-380.
    """
    gap = base * ((n_reviews + 1) ** (1.0 / d))
    return min(gap, _MAX_GAP_DAYS)


# ── State I/O ─────────────────────────────────────────────────────────────────

def load_state() -> dict:
    """Load review state: {skill_name: {n_reviews, last_reviewed_ts, next_due_ts}}."""
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_PATH)


# ── DB queries ────────────────────────────────────────────────────────────────

def load_skill_invocations() -> dict[str, list[float]]:
    """Return {skill_name: [days_ago, ...]} from skill_invocations table."""
    if not DB_PATH.exists():
        return {}
    now_ts = time.time()
    try:
        con = sqlite3.connect(DB_PATH)
        rows = con.execute(
            "SELECT skill_name, timestamp FROM skill_invocations ORDER BY timestamp DESC"
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return {}

    result: dict[str, list[float]] = {}
    for skill_name, ts_str in rows:
        try:
            # timestamp stored as ISO string or unix float
            try:
                ts = float(ts_str)
            except (ValueError, TypeError):
                import datetime
                ts = datetime.datetime.fromisoformat(str(ts_str)).timestamp()
            days_ago = max(0.001, (now_ts - ts) / 86400.0)
        except Exception:
            days_ago = 30.0  # conservative fallback
        result.setdefault(skill_name, []).append(days_ago)
    return result


def load_skill_counts() -> dict[str, int]:
    """Return {skill_name: invocation_count} from skill_yield_metrics."""
    if not DB_PATH.exists():
        return {}
    try:
        con = sqlite3.connect(DB_PATH)
        rows = con.execute(
            "SELECT skill_name, invocation_count FROM skill_yield_metrics"
        ).fetchall()
        con.close()
        return {r[0]: (r[1] or 0) for r in rows}
    except sqlite3.Error:
        return {}


# ── Scheduling logic ──────────────────────────────────────────────────────────

def compute_schedule(
    invocations: dict[str, list[float]],
    counts: dict[str, int],
    state: dict,
) -> list[dict]:
    """Return list of skill schedule entries sorted by urgency (overdue first)."""
    now_ts = time.time()
    entries = []

    all_skills = set(invocations.keys()) | set(counts.keys())
    for skill_name in all_skills:
        n_inv = counts.get(skill_name, len(invocations.get(skill_name, [])))
        if n_inv < _MIN_INVOCATIONS:
            continue

        times_ago = invocations.get(skill_name, [])
        activation = actr_activation(times_ago)

        s = state.get(skill_name, {})
        n_reviews = s.get("n_reviews", 0)
        last_reviewed = s.get("last_reviewed_ts", now_ts - 30 * 86400)  # default 30 days ago
        next_due = s.get("next_due_ts", now_ts)  # default: due now

        gap_days = next_review_gap_days(n_reviews)
        overdue_days = max(0.0, (now_ts - next_due) / 86400.0)
        is_overdue = now_ts >= next_due

        entries.append({
            "skill_name": skill_name,
            "n_invocations": n_inv,
            "n_reviews": n_reviews,
            "activation": round(activation, 3),
            "gap_days": round(gap_days, 1),
            "overdue_days": round(overdue_days, 2),
            "next_due_iso": _ts_to_iso(next_due),
            "is_overdue": is_overdue,
            "last_reviewed_iso": _ts_to_iso(last_reviewed),
        })

    # Sort: overdue first (most overdue at top), then by activation ascending (weakest first)
    entries.sort(key=lambda e: (-e["overdue_days"], e["activation"]))
    return entries


def _ts_to_iso(ts: float) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def mark_reviewed(skill_name: str, state: dict) -> dict:
    """Update state for a skill that was just reviewed."""
    now_ts = time.time()
    s = state.get(skill_name, {})
    n_reviews = s.get("n_reviews", 0) + 1
    # Use n_reviews-1 so first review schedules next_review_gap_days(0)=1 day out
    gap_days = next_review_gap_days(max(0, n_reviews - 1))
    next_due = now_ts + gap_days * 86400.0
    state[skill_name] = {
        "n_reviews": n_reviews,
        "last_reviewed_ts": now_ts,
        "next_due_ts": next_due,
        "gap_days": round(gap_days, 1),
    }
    return state


# ── CLI ───────────────────────────────────────────────────────────────────────

def cmd_list(all_skills: bool = False, as_json: bool = False) -> None:
    invocations = load_skill_invocations()
    counts = load_skill_counts()
    state = load_state()

    if not DB_PATH.exists() and not state:
        print("No skill yield DB found")
        return

    schedule = compute_schedule(invocations, counts, state)
    if not all_skills:
        schedule = [e for e in schedule if e["is_overdue"]]

    if as_json:
        print(json.dumps(schedule, indent=2))
        return

    if not schedule:
        print("No skills due for review." + (" Pass --all to see full schedule." if not all_skills else ""))
        return

    header = f"{'SKILL':<45} {'INV':>5} {'REV':>5} {'ACT':>7} {'OVERDUE':>8} {'NEXT_DUE'}"
    print(header)
    print("-" * len(header))
    for e in schedule:
        flag = " *** OVERDUE" if e["is_overdue"] else ""
        print(
            f"{e['skill_name']:<45} {e['n_invocations']:>5} {e['n_reviews']:>5} "
            f"{e['activation']:>7.2f} {e['overdue_days']:>7.1f}d {e['next_due_iso']}{flag}"
        )


def cmd_update(skill_name: str) -> None:
    state = load_state()
    state = mark_reviewed(skill_name, state)
    save_state(state)
    s = state[skill_name]
    print(
        f"Marked '{skill_name}' reviewed. n_reviews={s['n_reviews']}, "
        f"next due in {s['gap_days']:.1f} days ({_ts_to_iso(s['next_due_ts'])})"
    )


def cmd_self_test() -> None:
    """Unit tests for ACT-R activation and spacing formulas."""
    failures = []

    # 1. Single practice 1 day ago: A = ln(1^{-0.5}) = ln(1) = 0.0
    a = actr_activation([1.0])
    if not abs(a - 0.0) < 1e-9:
        failures.append(f"Test 1 failed: expected 0.0 got {a}")

    # 2. Two practices 1 day ago each: A = ln(2 * 1^{-0.5}) = ln(2)
    a2 = actr_activation([1.0, 1.0])
    if not abs(a2 - math.log(2)) < 1e-9:
        failures.append(f"Test 2 failed: expected {math.log(2):.4f} got {a2:.4f}")

    # 3. More recent = higher activation: 1-day-ago > 10-day-ago
    a_recent = actr_activation([1.0])
    a_old = actr_activation([10.0])
    if not a_recent > a_old:
        failures.append(f"Test 3 failed: recent {a_recent:.3f} should > old {a_old:.3f}")

    # 4. Spacing grows with n_reviews (d=0.5 -> quadratic)
    g0 = next_review_gap_days(0)  # base * 1^2 = base
    g1 = next_review_gap_days(1)  # base * 2^2 = 4*base
    g2 = next_review_gap_days(2)  # base * 3^2 = 9*base
    if not (g0 < g1 < g2):
        failures.append(f"Test 4 failed: gaps not monotone {g0:.1f} {g1:.1f} {g2:.1f}")

    # 5. Gap capped at _MAX_GAP_DAYS
    g_large = next_review_gap_days(1000)
    if not abs(g_large - _MAX_GAP_DAYS) < 1e-9:
        failures.append(f"Test 5 failed: cap not applied {g_large}")

    # 6. mark_reviewed increments n_reviews and advances next_due
    state = {}
    state = mark_reviewed("test_skill", state)
    assert state["test_skill"]["n_reviews"] == 1
    state = mark_reviewed("test_skill", state)
    assert state["test_skill"]["n_reviews"] == 2
    g_after_2 = state["test_skill"]["gap_days"]
    if not g_after_2 > _BASE_GAP_DAYS:
        failures.append(f"Test 6 failed: gap after 2 reviews = {g_after_2}")

    # 7. Empty practices -> -inf activation
    a_empty = actr_activation([])
    if not (a_empty == float("-inf")):
        failures.append(f"Test 7 failed: empty activation should be -inf, got {a_empty}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        sys.exit(1)
    else:
        print("SELF-TEST PASS")
        print(f"  ACT-R activation formula correct")
        print(f"  Spacing: n=0 gap={g0:.1f}d, n=1 gap={g1:.1f}d, n=2 gap={g2:.1f}d")
        print(f"  Cap at {_MAX_GAP_DAYS}d verified")
        print(f"  mark_reviewed state transitions correct")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="Show all skills, not just overdue")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--update", metavar="SKILL", help="Mark SKILL as reviewed now")
    parser.add_argument("--self-test", action="store_true", help="Run unit tests")
    args = parser.parse_args()

    if args.self_test:
        cmd_self_test()
    elif args.update:
        cmd_update(args.update)
    else:
        cmd_list(all_skills=args.all, as_json=args.json)


if __name__ == "__main__":
    main()
