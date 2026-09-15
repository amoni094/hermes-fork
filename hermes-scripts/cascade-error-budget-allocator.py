#!/usr/bin/env python3
"""
cascade-error-budget-allocator.py

Concentrates verification effort on high-cascade-risk delegation chains using
a branching-process intensity bound.

Math basis (random_graphs / cascade_error wave-3 ideas queue):
  For a Galton-Watson branching process with offspring mean μ and depth d,
  the expected total cascade count is bounded by:
    E[total_errors] <= error_rate * (μ^(d+1) - 1) / (μ - 1)  if μ != 1
    E[total_errors] <= error_rate * (d + 1)                    if μ == 1

  Where:
    - error_rate = empirical per-call error rate for this tool
    - μ = mean number of downstream tool calls per call (branching factor)
    - d = delegation depth

  A chain with high cascade bound gets a larger share of the verification budget.
  Chains below a minimum bound are passed without verification.

Usage:
    python3 cascade-error-budget-allocator.py [--budget N] [--dry-run] [--report]

    --budget N    Total verification calls to allocate (default 10)
    --report      Print cascade risk table only, no allocation
    --dry-run     Skip writes

Output:
    ~/.hermes/cache/cascade-allocation.json   — per-chain verification budget
    ~/.hermes/cache/cascade-risk.json         — risk scores for all chains
"""

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME = Path.home()
SESSIONS_DIR = HOME / ".hermes/sessions"
OUTPUT_ALLOC = HOME / ".hermes/cache/cascade-allocation.json"
OUTPUT_RISK = HOME / ".hermes/cache/cascade-risk.json"

# ── Session log parsing ────────────────────────────────────────────────────────

def load_tool_sequences() -> list[list[dict]]:
    """Load per-session tool-call sequences with error flags."""
    sessions = []
    for f in sorted(SESSIONS_DIR.glob("*.jsonl"))[-100:]:
        records = []
        try:
            lines = [l.strip() for l in f.read_text().splitlines() if l.strip()]
        except Exception:
            continue
        parsed = []
        for line in lines:
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        for i, rec in enumerate(parsed):
            if rec.get("role") != "assistant":
                continue
            tool_calls = rec.get("tool_calls") or []
            for tc in tool_calls:
                if not isinstance(tc, dict):
                    continue
                fn = tc.get("function", {})
                name = fn.get("name", "")
                if not name:
                    continue
                # Is next record an error response?
                is_error = False
                if i + 1 < len(parsed):
                    nxt = parsed[i + 1]
                    content = str(nxt.get("content", ""))
                    if "error" in content.lower() or "Error" in content or "traceback" in content.lower():
                        is_error = True
                # Depth: count delegate_task calls before this one in the session
                depth = sum(
                    1 for prev in records
                    if prev.get("tool") in ("delegate_task", "spawn")
                )
                records.append({
                    "tool": name.lower(),
                    "is_error": is_error,
                    "depth": depth,
                    "session": f.stem,
                })
        if records:
            sessions.append(records)
    return sessions


# ── Branching process metrics ──────────────────────────────────────────────────

def compute_chain_metrics(sessions: list[list[dict]]) -> dict[str, dict]:
    """Compute per-tool error_rate, branching_factor, and typical depth."""
    tool_calls: dict[str, int] = Counter()
    tool_errors: dict[str, int] = Counter()
    tool_children: dict[str, list[int]] = defaultdict(list)  # downstream call counts
    tool_depths: dict[str, list[int]] = defaultdict(list)

    for session in sessions:
        for i, rec in enumerate(session):
            tool = rec["tool"]
            tool_calls[tool] += 1
            if rec["is_error"]:
                tool_errors[tool] += 1
            tool_depths[tool].append(rec["depth"])

            # Count children: subsequent tool calls before next delegation boundary
            children = 0
            for j in range(i + 1, min(i + 10, len(session))):
                if session[j]["depth"] > rec["depth"]:
                    children += 1
                else:
                    break
            tool_children[tool].append(children)

    metrics = {}
    for tool in tool_calls:
        n = tool_calls[tool]
        error_rate = tool_errors[tool] / n
        branching = sum(tool_children[tool]) / len(tool_children[tool]) if tool_children[tool] else 0.0
        avg_depth = sum(tool_depths[tool]) / len(tool_depths[tool]) if tool_depths[tool] else 0.0
        metrics[tool] = {
            "n": n,
            "error_rate": round(error_rate, 4),
            "branching_factor": round(branching, 4),
            "avg_depth": round(avg_depth, 2),
        }
    return metrics


def cascade_bound(error_rate: float, mu: float, depth: float) -> float:
    """Galton-Watson expected total cascade error count at given depth."""
    d = max(0, round(depth))
    if error_rate == 0:
        return 0.0
    if abs(mu - 1.0) < 1e-6:
        return error_rate * (d + 1)
    return error_rate * (mu ** (d + 1) - 1) / (mu - 1)


def compute_risk_scores(metrics: dict[str, dict]) -> list[dict]:
    """Compute cascade risk score for each tool chain."""
    risks = []
    for tool, m in metrics.items():
        bound = cascade_bound(m["error_rate"], m["branching_factor"], m["avg_depth"])
        risks.append({
            "tool": tool,
            "cascade_bound": round(bound, 4),
            "error_rate": m["error_rate"],
            "branching_factor": m["branching_factor"],
            "avg_depth": m["avg_depth"],
            "n_calls": m["n"],
        })
    risks.sort(key=lambda x: x["cascade_bound"], reverse=True)
    return risks


# ── Budget allocation ──────────────────────────────────────────────────────────

def allocate_budget(risks: list[dict], total_budget: int) -> list[dict]:
    """Allocate verification calls proportional to cascade_bound."""
    total_risk = sum(r["cascade_bound"] for r in risks)
    allocations = []
    remaining = total_budget
    for i, r in enumerate(risks):
        if total_risk == 0 or r["cascade_bound"] == 0:
            alloc = 0
        elif i == len(risks) - 1:
            alloc = remaining  # give remainder to last
        else:
            alloc = round(r["cascade_bound"] / total_risk * total_budget)
        remaining -= alloc
        allocations.append({
            **r,
            "verification_budget": alloc,
            "verification_priority": "HIGH" if alloc >= 3 else ("MEDIUM" if alloc >= 1 else "SKIP"),
        })
    return allocations


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cascade error budget allocator")
    parser.add_argument("--budget", type=int, default=10, help="Total verification calls to allocate")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", action="store_true", help="Print risk table only")
    args = parser.parse_args()

    print(f"[cascade] Loading session tool sequences...", file=sys.stderr)
    sessions = load_tool_sequences()
    print(f"[cascade] {len(sessions)} sessions loaded", file=sys.stderr)

    if not sessions:
        print("[cascade] No session data found.")
        return

    metrics = compute_chain_metrics(sessions)
    risks = compute_risk_scores(metrics)
    allocations = allocate_budget(risks, args.budget)

    now = datetime.now(timezone.utc).isoformat()

    if not args.dry_run and not args.report:
        OUTPUT_RISK.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_RISK.write_text(json.dumps({
            "scored_at": now,
            "tools_scored": len(risks),
            "risks": risks[:30],
        }, indent=2))
        OUTPUT_ALLOC.write_text(json.dumps({
            "allocated_at": now,
            "total_budget": args.budget,
            "allocations": allocations[:20],
        }, indent=2))
        print(f"[cascade] Written: {OUTPUT_RISK}, {OUTPUT_ALLOC}", file=sys.stderr)

    print(f"\n=== Cascade Error Budget Allocator — {now[:10]} ===")
    print(f"Sessions: {len(sessions)}, Tools tracked: {len(risks)}")
    print(f"Total verification budget: {args.budget} calls")
    print()
    print(f"{'Tool':<35} {'Cascade':>8} {'ErrRate':>8} {'BrFact':>7} {'Budget':>7} {'Priority'}")
    print("-" * 80)
    for a in allocations[:20]:
        if a["cascade_bound"] == 0 and a["verification_budget"] == 0:
            continue
        print(
            f"{a['tool']:<35} {a['cascade_bound']:>8.3f} {a['error_rate']:>8.3f} "
            f"{a['branching_factor']:>7.2f} {a['verification_budget']:>7} {a['verification_priority']}"
        )

    if not args.dry_run and not args.report:
        print(f"\nAllocation: {OUTPUT_ALLOC}")
        print(f"Risk scores: {OUTPUT_RISK}")


if __name__ == "__main__":
    main()
