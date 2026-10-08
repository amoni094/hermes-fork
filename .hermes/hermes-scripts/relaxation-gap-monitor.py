#!/usr/bin/python3
"""
relaxation-gap-monitor.py

Self-assesses Hermes routing solution quality by measuring the gap between
the achieved routing objective (primal) and a tractable upper bound (dual
relaxation). Extends duality-gap-monitor.py with time-series tracking and
a tighter LP relaxation via fractional assignment.

Math basis (convex_analysis / LP duality): for any combinatorial optimization
problem, the LP relaxation dual provides an upper bound on the primal optimal.
The relaxation gap (primal* / dual*) ∈ [0,1] measures how close the current
integer solution is to the continuous optimum. A falling gap over time means
the routing is becoming more efficient. A rising gap means degeneracy.

For Hermes skill routing:
  Primal: total value of actual skill selections (discrete, observed)
  Dual:   LP relaxation (fractional assignment of sessions to skills)
  Gap:    1 - primal/dual  ∈ [0,1]  (0=optimal, 1=completely suboptimal)

Unlike duality-gap-monitor.py (which looks at circuit-scorer output),
this script operates directly on raw session→skill assignment data and
tracks the gap trajectory over time.
"""

from __future__ import annotations
import os

import argparse
import json
import math
import re
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME      = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS  = HOME / ".hermes/sessions"
FORK_SESSIONS = _RT / "sessions"  # fork-profile sessions

CACHE_DIR = HOME / ".hermes/cache/monitors"
STATE_DB  = HOME / ".hermes/memory-facts/stability.db"
OUT_FILE  = CACHE_DIR / "relaxation-gap.json"
ALARM_FILE = CACHE_DIR / "relaxation-gap-alarm.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

GAP_ALARM_THRESHOLD = 0.60   # alarm if gap > 60%
WINDOW = 10                   # sessions per window


def _extract_skill_calls(text: str) -> list[str]:
    skills: list[str] = []
    for line in text.split("\n"):
        try:
            obj = json.loads(line)
            if obj.get("role") == "assistant":
                for tc in obj.get("tool_calls", []):
                    if isinstance(tc, dict) and tc.get("function", {}).get("name") == "skill_view":
                        args = tc["function"].get("arguments", "{}")
                        if isinstance(args, str):
                            args = json.loads(args)
                        s = args.get("name", "")
                        if s:
                            skills.append(s)
        except Exception:
            pass
    return skills


def _session_value(skills: list[str], skill_value: dict[str, float]) -> float:
    """Primal: total value of actual skill selections in this session."""
    return sum(skill_value.get(s, 0.5) for s in skills)


def _fractional_ub(session_skills: list[str], skill_value: dict[str, float]) -> float:
    """
    Dual (LP relaxation) upper bound for this session's selections.
    For each skill actually selected, the fractional UB assumes we could have
    chosen the globally best skill instead. So dual = budget × max_skill_value
    where budget = len(session_skills). This is always >= primal by construction.
    """
    if not session_skills or not skill_value:
        return 0.0
    budget    = len(session_skills)
    max_value = max(skill_value.values())
    return budget * max_value


def run(dry_run: bool = False) -> None:
    now = datetime.now(timezone.utc).isoformat()
    session_files = sorted([f for d in [SESSIONS, FORK_SESSIONS] if d.exists() for f in d.glob("*.jsonl")])

    # Build skill value map: use frequency as proxy for value
    skill_freq: dict[str, int] = defaultdict(int)
    session_skills: list[tuple[str, list[str]]] = []

    for sf in session_files:
        try:
            text = sf.read_text()
        except Exception:
            continue
        skills = _extract_skill_calls(text)
        session_skills.append((sf.stem[:20], skills))
        for s in skills:
            skill_freq[s] += 1

    if not skill_freq:
        print(f"\n=== Relaxation Gap Monitor — {now[:10]} ===")
        print("No skill calls found in session history.")
        return

    # Normalize freq to [0,1] value
    max_freq = max(skill_freq.values())
    skill_value = {s: f / max_freq for s, f in skill_freq.items()}
    all_skills  = list(skill_freq.keys())

    # Compute per-session and windowed gap
    primals: list[float] = []
    duals:   list[float] = []
    for _, skills in session_skills:
        if not skills:
            continue
        p = _session_value(skills, skill_value)
        d = _fractional_ub(skills, skill_value)
        primals.append(p)
        duals.append(d)

    if not primals:
        print("No sessions with skill calls.")
        return

    arr_p = np.array(primals)
    arr_d = np.array(duals)
    arr_d = np.where(arr_d == 0, 1e-6, arr_d)  # guard div/0

    gaps = 1.0 - arr_p / arr_d
    mean_gap   = float(np.mean(gaps))
    trend_gap  = float(np.mean(gaps[-WINDOW:])) if len(gaps) >= WINDOW else mean_gap

    print(f"\n=== Relaxation Gap Monitor — {now[:10]} ===")
    print(f"Sessions with skill calls: {len(primals)}")
    print(f"Skills in vocabulary:      {len(all_skills)}")
    print(f"Mean relaxation gap:       {mean_gap:.3f}  (0=optimal, 1=suboptimal)")
    print(f"Recent window gap (n={WINDOW}): {trend_gap:.3f}")

    alarm = trend_gap > GAP_ALARM_THRESHOLD
    if alarm:
        print(f"ALARM: yes — recent gap {trend_gap:.3f} > threshold {GAP_ALARM_THRESHOLD}")
        if not dry_run:
            _alarm_payload = json.dumps({"ts": now, "mean_gap": round(mean_gap, 4), "trend_gap": round(trend_gap, 4), "threshold": GAP_ALARM_THRESHOLD}, indent=2)
            _tmp = ALARM_FILE.with_suffix('.tmp'); _tmp.write_text(_alarm_payload); _tmp.replace(ALARM_FILE)
    else:
        print("ALARM: no — relaxation gap within bounds")

    if not dry_run:
        out = {
            "ts": now,
            "sessions": len(primals),
            "skills": len(all_skills),
            "mean_gap": round(mean_gap, 4),
            "trend_gap": round(trend_gap, 4),
            "gap_series": [round(g, 4) for g in gaps.tolist()],
            "alarm": alarm,
        }
        _tmp = OUT_FILE.with_suffix('.tmp'); _tmp.write_text(json.dumps(out, indent=2)); _tmp.replace(OUT_FILE)
        print(f"Written: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Relaxation gap monitor for skill routing")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
