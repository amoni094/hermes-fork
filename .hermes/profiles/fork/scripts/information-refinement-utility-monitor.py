#!/usr/bin/python3
"""
information-refinement-utility-monitor.py

Detects when Hermes' improved internal observability (finer skill logs,
richer memory tagging, more detailed tracing) produces diminishing marginal
utility — i.e., the information cost of refinement exceeds its benefit.

Math basis (monotone operator on information partition refinement):
  Let Π₀ ⊆ Π₁ be two information partitions (coarse → fine).
  The marginal utility of refinement is:
    ΔU = U(Π₁) - U(Π₀) = E[V(action | Π₁)] - E[V(action | Π₀)]
  
  When ΔU < refinement_cost, further logging/tracing is wasteful.
  We approximate this from session data:
    - U(Π) ≈ mean skill-routing precision at partition resolution Π
    - refinement_cost ≈ extra tokens / latency per turn at finer resolution

  Alarm: if successive refinement passes produce ΔU < ε (near-zero gain)
  with non-negligible cost → recommend coarsening observability.

Usage:
  python3 information-refinement-utility-monitor.py [--dry-run]
"""

from __future__ import annotations
import os

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
STABILITY_DB = HOME / ".hermes/cache/monitors/stability.db"
SESSIONS_DIR = _RT / "sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MARGINAL_UTILITY_THRESHOLD = 0.02   # ΔU < 2% → refinement no longer worth it
REFINEMENT_COST_PER_LEVEL  = 0.05   # assumed 5% overhead per partition level
MIN_SESSIONS_PER_LEVEL     = 2


def _load_session_stats() -> list[dict]:
    """Load per-session tool count and latency from JSONL files."""
    stats = []
    try:
        for p in sorted(SESSIONS_DIR.glob("*.jsonl"))[-40:]:
            lines = p.read_text().splitlines()
            tool_count = 0
            content_len = 0
            for line in lines:
                try:
                    ev = json.loads(line)
                    if ev.get("role") == "assistant":
                        c = ev.get("content", ev.get("api_content", ""))
                        if isinstance(c, str):
                            content_len += len(c)
                            if "tool_use" in c:
                                tool_count += c.count('"type": "tool_use"') or c.count('"tool_use"')
                        elif isinstance(c, list):
                            for b in c:
                                if isinstance(b, dict) and b.get("type") == "tool_use":
                                    tool_count += 1
                except Exception:
                    pass
            stats.append({
                "session_id": p.stem,
                "n_turns": len(lines),
                "tool_calls": tool_count,
                "content_tokens_est": content_len // 4,
            })
    except Exception:
        pass
    return stats


def _partition_level(stat: dict) -> int:
    """Assign a partition refinement level from tool density."""
    density = stat["tool_calls"] / max(stat["n_turns"], 1)
    if density < 0.3:
        return 0   # Coarse: few tools
    elif density < 1.0:
        return 1   # Medium
    else:
        return 2   # Fine: tool-heavy


def _utility_at_level(stats: list[dict], level: int) -> float:
    """Approximate utility = mean tool density (proxy for routing precision)."""
    subset = [s for s in stats if _partition_level(s) == level]
    if not subset:
        return 0.0
    densities = [s["tool_calls"] / max(s["n_turns"], 1) for s in subset]
    return float(np.mean(densities))


def run_monitor(dry_run: bool = False) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    alarms: list[str] = []
    stats = _load_session_stats()

    print(f"[info-refinement] Loaded {len(stats)} sessions")

    if len(stats) < MIN_SESSIONS_PER_LEVEL:
        # Synthesize reference data
        stats = [
            {"session_id": "ref_coarse",  "n_turns": 10, "tool_calls": 2,  "content_tokens_est": 500},
            {"session_id": "ref_medium1", "n_turns": 10, "tool_calls": 8,  "content_tokens_est": 1200},
            {"session_id": "ref_medium2", "n_turns": 12, "tool_calls": 9,  "content_tokens_est": 1400},
            {"session_id": "ref_fine1",   "n_turns": 8,  "tool_calls": 14, "content_tokens_est": 2000},
            {"session_id": "ref_fine2",   "n_turns": 7,  "tool_calls": 13, "content_tokens_est": 1900},
        ]
        print("[info-refinement] Using reference sessions")

    levels = [0, 1, 2]
    utilities = {lv: _utility_at_level(stats, lv) for lv in levels}
    counts    = {lv: sum(1 for s in stats if _partition_level(s) == lv) for lv in levels}

    print(f"\n=== Information Refinement Utility Monitor — {now[:10]} ===")
    print(f"  {'Level':<8} {'n_sessions':<12} {'utility':<12} {'ΔU':<12} {'cost':<10} {'net_gain'}")
    print("  " + "-" * 65)

    results = []
    for i in range(1, len(levels)):
        lv_prev, lv_curr = levels[i - 1], levels[i]
        delta_u = utilities[lv_curr] - utilities[lv_prev]
        net_gain = delta_u - REFINEMENT_COST_PER_LEVEL
        alarm = delta_u < MARGINAL_UTILITY_THRESHOLD and counts[lv_curr] >= MIN_SESSIONS_PER_LEVEL

        flag = "  ALARM" if alarm else "OK"
        print(f"  [{flag}] L{lv_prev}→L{lv_curr}:  "
              f"n={counts[lv_curr]:<6} U={utilities[lv_curr]:.3f}  "
              f"ΔU={delta_u:+.3f}  cost={REFINEMENT_COST_PER_LEVEL:.3f}  net={net_gain:+.3f}")

        if alarm:
            alarms.append(
                f"REFINEMENT_SATURATION L{lv_prev}→L{lv_curr}: "
                f"ΔU={delta_u:.4f} < {MARGINAL_UTILITY_THRESHOLD} — observability overhead exceeds gain"
            )
        results.append({
            "transition": f"L{lv_prev}->L{lv_curr}",
            "delta_u": round(delta_u, 5),
            "net_gain": round(net_gain, 5),
            "alarm": alarm,
            "sessions_at_level": counts[lv_curr],
        })

    if alarms:
        print(f"\nALARM: yes — {len(alarms)} refinement saturation alarm(s):")
        for a in alarms:
            print(f"  {a}")
        alarm_exit = 1
    else:
        print("\nALARM: no — information refinement is still producing positive net gain")
        alarm_exit = 0

    if not dry_run:
        out = CACHE_DIR / "information-refinement-report.json"
        _tmp_out = out.with_suffix(".tmp")
        _tmp_out.write_text(json.dumps({
            "ts": now, "utilities": utilities, "counts": counts,
            "results": results, "alarms": alarms,
        }, indent=2))
        _tmp_out.replace(out)
        print(f"\nWritten: {out}")

    return alarm_exit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import sys
    sys.exit(run_monitor(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
