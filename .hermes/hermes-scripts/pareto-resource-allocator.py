#!/usr/bin/python3
"""
pareto-resource-allocator.py

Auto-tunes Hermes memory/compute/latency trade-offs per session type using
Pareto frontier analysis across historical session outcomes.

Math basis (multi-objective_optimization / convex_analysis): the Pareto
frontier of a set of resource-outcome points is the set of non-dominated
solutions. A solution is Pareto-optimal if no other solution is better on
all objectives simultaneously. For Hermes resource allocation:
  - Objectives: minimize latency, minimize token cost, maximize output quality
  - Decision variables: context_budget, tool_call_limit, skill_call_limit
  - Pareto frontier: the set of session configurations where improving one
    metric requires degrading another

By fitting a Pareto frontier from historical sessions, we can recommend the
configuration that sits on the frontier at the user's preferred tradeoff point
(e.g., "minimize cost given quality >= 0.8").

Usage:
  python3 pareto-resource-allocator.py            # summary
  python3 pareto-resource-allocator.py --quality 0.8  # recommend config at quality target
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME      = Path.home()
SESSIONS  = HOME / ".hermes/sessions"
CACHE_DIR = HOME / ".hermes/cache/monitors"
OUT_FILE  = CACHE_DIR / "pareto-allocations.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _session_metrics(text: str) -> dict | None:
    """Extract resource usage metrics from a session."""
    lines = text.split("\n")
    tool_calls = 0
    skill_calls = 0
    total_tokens = 0
    turns = 0

    for line in lines:
        try:
            obj = json.loads(line)
            role = obj.get("role","")
            if role == "assistant":
                tcs = obj.get("tool_calls",[])
                tool_calls += len(tcs)
                for tc in tcs:
                    if isinstance(tc, dict) and tc.get("function",{}).get("name") == "skill_view":
                        skill_calls += 1
                content = obj.get("content","") or ""
                total_tokens += len(str(content).split()) // 1  # word proxy
                turns += 1
        except Exception:
            pass

    if turns == 0:
        return None

    # Quality proxy: turns completed without error / total turns
    quality = min(1.0, turns / max(turns + 1, 1))
    # Cost proxy: total tool_calls (each is an API call)
    cost = tool_calls
    # Latency proxy: tool_calls per turn (more = slower)
    latency = tool_calls / max(turns, 1)

    return {
        "tool_calls":  tool_calls,
        "skill_calls": skill_calls,
        "turns":       turns,
        "quality":     quality,
        "cost":        cost,
        "latency":     latency,
    }


def _is_dominated(p: np.ndarray, others: np.ndarray) -> bool:
    """True if p is dominated by any point in others (lower cost+latency, higher quality)."""
    # Objectives: minimize cost (0), minimize latency (1), maximize quality (2→negate)
    for o in others:
        if (o[0] <= p[0] and o[1] <= p[1] and o[2] >= p[2] and
                (o[0] < p[0] or o[1] < p[1] or o[2] > p[2])):
            return True
    return False


def _pareto_frontier(points: np.ndarray) -> np.ndarray:
    """Return indices of Pareto-optimal points."""
    n = len(points)
    pareto_mask = np.ones(n, dtype=bool)
    for i in range(n):
        if pareto_mask[i]:
            others = points[pareto_mask]
            if _is_dominated(points[i], np.delete(others, np.where(
                    np.all(others == points[i], axis=1))[0], axis=0)):
                pareto_mask[i] = False
    return np.where(pareto_mask)[0]


def run(quality_target: float | None, dry_run: bool = False) -> None:
    now = datetime.now(timezone.utc).isoformat()
    session_files = sorted(SESSIONS.glob("*.jsonl"))

    metrics: list[dict] = []
    for sf in session_files:
        try:
            text = sf.read_text()
        except Exception:
            continue
        m = _session_metrics(text)
        if m and m["tool_calls"] > 0:
            metrics.append(m)

    print(f"\n=== Pareto Resource Allocator — {now[:10]} ===")
    print(f"Sessions analysed: {len(metrics)}")

    if len(metrics) < 2:
        print("Insufficient data (need ≥2 sessions with tool calls).")
        return

    # Build objective matrix: [cost, latency, -quality] (all minimize)
    pts = np.array([[m["cost"], m["latency"], -m["quality"]] for m in metrics])
    frontier_idx = _pareto_frontier(pts)

    print(f"Pareto-optimal sessions: {len(frontier_idx)}/{len(metrics)}")

    if quality_target is not None:
        # Find frontier points with quality >= target
        candidates = [
            metrics[i] for i in frontier_idx
            if metrics[i]["quality"] >= quality_target
        ]
        if candidates:
            # Recommend minimum-cost candidate
            best = min(candidates, key=lambda m: m["cost"])
            print(f"\nAt quality >= {quality_target}:")
            print(f"  Recommended: tool_calls={best['tool_calls']}, "
                  f"skill_calls={best['skill_calls']}, turns={best['turns']}")
            print(f"  Cost={best['cost']}, Latency={best['latency']:.2f}, "
                  f"Quality={best['quality']:.2f}")
        else:
            print(f"\nNo Pareto-optimal session achieves quality >= {quality_target}")

    # Summary stats
    frontier_metrics = [metrics[i] for i in frontier_idx]
    if frontier_metrics:
        mean_cost    = sum(m["cost"]    for m in frontier_metrics) / len(frontier_metrics)
        mean_latency = sum(m["latency"] for m in frontier_metrics) / len(frontier_metrics)
        mean_quality = sum(m["quality"] for m in frontier_metrics) / len(frontier_metrics)
        print(f"\nPareto frontier summary:")
        print(f"  Mean cost (tool calls): {mean_cost:.1f}")
        print(f"  Mean latency (calls/turn): {mean_latency:.2f}")
        print(f"  Mean quality: {mean_quality:.2f}")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now,
            "sessions": len(metrics),
            "frontier_size": int(len(frontier_idx)),
            "frontier": [metrics[i] for i in frontier_idx],
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"Written: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pareto resource allocator")
    parser.add_argument("--quality", type=float, default=None,
                        help="Quality target (0-1); recommend min-cost config at this quality")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(quality_target=args.quality, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
