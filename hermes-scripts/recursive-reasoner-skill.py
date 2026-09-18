#!/usr/bin/python3
"""
recursive-reasoner-skill.py

Enables multi-step agent reasoning with automatic loop termination and
convergence detection — implements S-AI-Recursive style convergent
recursive reasoning with a fixed-point stopping criterion.

Math basis: S-AI-Recursive (convergent recursive reasoning)
  At each step t, agent produces belief b_t from b_{t-1} via:
    b_t = f(b_{t-1}, context)
  Convergence: ||b_t - b_{t-1}||_1 < ε   (belief stabilised)
  Max iterations: T_max (prevents runaway loops)
  
  Operationally: track key conclusion tokens across reasoning steps;
  alarm/stop when the set of conclusions stops changing.

Usage:
  python3 recursive-reasoner-skill.py --steps STEP1 STEP2 ...
  python3 recursive-reasoner-skill.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "recursive-reasoning-trace.json"

MAX_ITERATIONS  = 10
CONVERGENCE_EPS = 0.05   # stop when belief change < 5%


def _extract_conclusions(text: str) -> set[str]:
    """Extract key conclusion tokens (4+ char words, excluding stop words)."""
    STOP = {"this", "that", "with", "from", "have", "will", "been",
            "they", "their", "when", "what", "which", "also", "than"}
    tokens = set(re.findall(r"[a-z]{4,}", text.lower()))
    return tokens - STOP


def _belief_distance(b1: set[str], b2: set[str]) -> float:
    """L1-proxy distance between two conclusion sets."""
    union = b1 | b2
    if not union:
        return 0.0
    sym_diff = b1.symmetric_difference(b2)
    return len(sym_diff) / len(union)


def reason(steps: list[str], eps: float = CONVERGENCE_EPS) -> dict:
    """Run convergent recursive reasoning over provided steps."""
    trace        = []
    prev_belief  = set()
    converged_at = -1
    final_belief = set()

    for i, step in enumerate(steps[:MAX_ITERATIONS]):
        curr_belief = _extract_conclusions(step)
        # Accumulate (belief grows, never shrinks — monotone operator)
        curr_belief = prev_belief | curr_belief
        dist = _belief_distance(prev_belief, curr_belief)

        trace.append({
            "step":     i + 1,
            "text":     step[:80],
            "new_tokens": len(curr_belief - prev_belief),
            "belief_size": len(curr_belief),
            "distance": round(dist, 4),
            "converged": dist < eps and i > 0,
        })

        if dist < eps and i > 0:
            converged_at = i + 1
            final_belief = curr_belief
            break

        prev_belief = curr_belief
        final_belief = curr_belief

    if converged_at == -1:
        converged_at = len(trace)

    return {
        "steps_run":     len(trace),
        "converged_at":  converged_at,
        "final_tokens":  len(final_belief),
        "top_conclusions": sorted(final_belief)[:10],
        "trace":         trace,
    }


def run(steps: list[str] | None, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()

    if not steps:
        # Demo: 5-step reasoning about memory compression
        steps = [
            "Memory compression reduces context size and improves throughput.",
            "Compression must preserve task-relevant tokens to avoid information loss.",
            "Rate-distortion theory provides optimal compression bounds.",
            "Applying rate-distortion: keep tokens with highest mutual information to task.",
            "Conclusion: use relevance-scored block selection with budget constraint.",
        ]

    result = reason(steps)

    print(f"\n=== Recursive Reasoner — {now[:10]} ===")
    print(f"Steps run: {result['steps_run']}  "
          f"Converged at: {result['converged_at']}  "
          f"Final belief size: {result['final_tokens']} tokens\n")

    for t in result["trace"]:
        icon = "✓ CONVERGED" if t["converged"] else f"+{t['new_tokens']} new"
        print(f"  Step {t['step']}: dist={t['distance']:.4f}  {icon}")
        print(f"    \"{t['text'][:70]}\"")

    print(f"\nTop conclusions: {', '.join(result['top_conclusions'][:8])}")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now, **{k: v for k, v in result.items() if k != "top_conclusions"},
            "top_conclusions": result["top_conclusions"],
        }, indent=2))

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--steps",   nargs="+", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.steps, args.dry_run))


if __name__ == "__main__":
    main()
