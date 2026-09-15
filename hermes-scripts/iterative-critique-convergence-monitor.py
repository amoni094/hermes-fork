#!/usr/bin/python3
"""
iterative-critique-convergence-monitor.py

Detects when iterative refinement loops (adversarial review → fix → review)
are converging vs. stuck oscillating or diverging.

Math basis: Fixed-point convergence in Banach spaces.
  For a sequence of critique outputs x_0, x_1, ... x_n,
  convergence implies ||x_{n+1} - x_n|| → 0 (contraction mapping).
  Proxy: count of issues raised in consecutive adversarial subagent calls.
  If issue counts oscillate or increase, the loop is not contracting.

Operationally: reads adversarial review logs / session critique counts
from ~/.hermes/cache/monitors/ and tracks issue-count trajectory.
"""
from __future__ import annotations

import json, math, sys
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "iterative-critique-convergence.json"
LOG_FILE  = CACHE_DIR / "critique-history.json"   # appended by adversarial runs

CONVERGENCE_RATIO = 0.60   # issue count must drop to < 60% of previous to be "contracting"
MIN_ROUNDS        = 3


def _load_history() -> list[dict]:
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text())
        except Exception:
            pass
    return []


def _infer_from_suite_cache() -> list[dict]:
    """
    Fall back: infer critique rounds from adversarial-monitor cache files.
    Each time an adversarial subagent writes a result, it increments issue count.
    """
    history = []
    # Look for any cache files with "issues" or "alarm" counts
    for f in sorted(CACHE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime):
        if f.name in ("iterative-critique-convergence.json", "critique-history.json"):
            continue
        try:
            d = json.loads(f.read_text())
            if isinstance(d, dict) and "ts" in d:
                # Count alarms/issues as a proxy for critique severity
                issues = d.get("issue_count", d.get("alarm_count",
                          d.get("low_productivity_count", d.get("leaking_count", 0))))
                if isinstance(issues, (int, float)):
                    history.append({"ts": d["ts"], "issues": int(issues), "source": f.name})
        except Exception:
            continue
    return sorted(history, key=lambda x: x["ts"])


def run() -> int:
    now = datetime.now(timezone.utc).isoformat()
    print(f"\n=== Iterative Critique Convergence Monitor — {now[:10]} ===\n")

    history = _load_history() or _infer_from_suite_cache()

    if len(history) < MIN_ROUNDS:
        print(f"Critique rounds found: {len(history)} (need {MIN_ROUNDS})")
        print("ALARM: no — insufficient rounds to assess convergence")
        return 0

    counts = [h["issues"] for h in history[-8:]]
    print(f"  {'Round':<5} {'Issues':>7}  {'Ratio':>7}  Status")
    print("  " + "-"*35)
    ratios = []
    for i, c in enumerate(counts):
        if i == 0:
            print(f"  {i:<5} {c:>7}")
            continue
        ratio = c / max(counts[i-1], 1)
        ratios.append(ratio)
        contracting = ratio < CONVERGENCE_RATIO
        print(f"  {i:<5} {c:>7}  {ratio:>7.3f}  {'↓ contracting' if contracting else '↑ not contracting'}")

    mean_ratio = sum(ratios) / len(ratios) if ratios else 1.0
    last_ratio = ratios[-1] if ratios else 1.0
    converging = last_ratio < CONVERGENCE_RATIO and mean_ratio < 0.85

    print(f"\nRounds: {len(counts)}, Mean ratio: {mean_ratio:.3f}, Last ratio: {last_ratio:.3f}")
    if not converging:
        print(f"\nALARM: yes — critique loop not converging: last ratio={last_ratio:.3f} "
              f"(need <{CONVERGENCE_RATIO}); consider stopping refinement")
    else:
        print(f"\nALARM: no — critique loop converging normally")

    OUT_FILE.write_text(json.dumps({
        "ts": now, "rounds": len(counts), "mean_ratio": round(mean_ratio, 4),
        "last_ratio": round(last_ratio, 4), "converging": converging,
        "counts": counts, "convergence_threshold": CONVERGENCE_RATIO,
    }, indent=2))
    return 0 if converging else 1


if __name__ == "__main__":
    sys.exit(run())
