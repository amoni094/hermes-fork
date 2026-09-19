#!/usr/bin/python3
"""
feedback-budget-optimizer.py

Dynamically allocates tool-call budgets and context-compression ratios
per session phase using feedback channel capacity theory.

Math basis (information_theory / feedback_capacity): the feedback capacity
of a channel C_fb = max_{p(x|y^{t-1})} I(X;Y) is always >= C (no feedback).
For Hermes, each tool call is a channel use: the "feedback" is the tool result,
which can be used to adapt the next call. Optimal feedback strategy concentrates
budget on tool sequences with highest mutual information (most novel results).

Concretely:
  - Phase 1 (exploration): allocate budget freely, measure per-tool info gain
    (proxy: result length × novelty vs prior calls in session)
  - Phase 2 (exploitation): allocate remaining budget to highest-gain tools,
    cut tools that return redundant results
  - Emit per-session budget recommendation: {tool: suggested_calls}

Usage as cron/monitor: scans recent sessions, computes per-tool info gain
distribution, outputs recommended budget allocation for next session.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
SESSIONS  = HOME / ".hermes/sessions"
CACHE_DIR = HOME / ".hermes/cache/monitors"
OUT_FILE  = CACHE_DIR / "feedback-budget.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BUDGET_TOTAL = 50     # default total tool calls per session
MIN_CALLS    = 1      # minimum guaranteed calls per tool
TOP_K        = 10     # number of top tools to allocate budget to


def _extract_tool_results(text: str) -> list[dict]:
    """Extract (tool_name, result_length) pairs from a session."""
    calls: list[dict] = []
    lines = text.split("\n")
    for line in lines:
        try:
            obj = json.loads(line)
            role = obj.get("role", "")

            if role == "assistant":
                # Collect tool calls and their result lengths from api_content
                api = obj.get("api_content", [])
                if isinstance(api, list):
                    for block in api:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            name = block.get("name", "")
                            if name:
                                calls.append({"tool": name, "result_len": 0, "_id": block.get("id","")})
                # fallback: tool_calls list
                if not calls or calls[-1]["result_len"] == 0:
                    for tc in obj.get("tool_calls", []):
                        if isinstance(tc, dict):
                            name = tc.get("function", {}).get("name", "")
                            if name:
                                calls.append({"tool": name, "result_len": 0, "_id": tc.get("id","")})

            elif role == "user":
                # Tool results are in user message content blocks
                content = obj.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            tool_use_id = block.get("tool_use_id", "")
                            result_content = block.get("content", "")
                            if isinstance(result_content, list):
                                result_content = " ".join(
                                    str(c.get("text","")) for c in result_content
                                    if isinstance(c, dict)
                                )
                            result_len = len(str(result_content))
                            # Match back to most recent call with same id
                            for c in reversed(calls):
                                if c.get("_id") == tool_use_id or c["result_len"] == 0:
                                    c["result_len"] = result_len
                                    break
        except Exception:
            pass
    return [c for c in calls if c["result_len"] > 0]


def _info_gain(calls: list[dict]) -> dict[str, float]:
    """
    Estimate per-tool information gain using result length as proxy.
    Novelty: result_len / mean_result_len_for_tool_in_session.
    Returns {tool: mean_info_gain}.
    """
    tool_results: dict[str, list[int]] = defaultdict(list)
    for c in calls:
        tool_results[c["tool"]].append(c["result_len"])

    gain: dict[str, float] = {}
    for tool, lengths in tool_results.items():
        if not lengths:
            continue
        mean_len = sum(lengths) / len(lengths)
        # Diminishing returns: info gain = mean_len × log(1 + 1/count)
        # High count tools with same length = redundant
        count = len(lengths)
        gain[tool] = mean_len * math.log(1 + 1 / count)
    return gain


def _allocate_budget(gain: dict[str, float], total: int) -> dict[str, int]:
    """
    Allocate total budget across tools proportional to info gain.
    Each tool gets at least MIN_CALLS.
    """
    if not gain:
        return {}
    top = sorted(gain.items(), key=lambda x: -x[1])[:TOP_K]
    total_gain = sum(g for _, g in top)
    if total_gain == 0:
        # Uniform allocation
        per = max(MIN_CALLS, total // len(top))
        return {t: per for t, _ in top}

    allocation: dict[str, int] = {}
    remaining = total
    for tool, g in top:
        share = max(MIN_CALLS, round(g / total_gain * total))
        allocation[tool] = share
        remaining -= share

    # Give any remainder to the top tool
    if remaining > 0 and top:
        allocation[top[0][0]] = allocation.get(top[0][0], 0) + remaining

    return allocation


def run(dry_run: bool = False, budget: int = BUDGET_TOTAL) -> None:
    now = datetime.now(timezone.utc).isoformat()
    session_files = sorted(SESSIONS.glob("*.jsonl"))

    # Aggregate gain across sessions
    all_gain: dict[str, list[float]] = defaultdict(list)
    sessions_processed = 0

    for sf in session_files:
        try:
            text = sf.read_text()
        except Exception:
            continue
        calls = _extract_tool_results(text)
        if not calls:
            continue
        gain = _info_gain(calls)
        for tool, g in gain.items():
            all_gain[tool].append(g)
        sessions_processed += 1

    if not all_gain:
        print(f"\n=== Feedback Budget Optimizer — {now[:10]} ===")
        print("No tool results found in session history.")
        return

    # Mean gain per tool across sessions
    mean_gain = {t: sum(gs) / len(gs) for t, gs in all_gain.items()}
    allocation = _allocate_budget(mean_gain, budget)

    print(f"\n=== Feedback Budget Optimizer — {now[:10]} ===")
    print(f"Sessions analysed: {sessions_processed}")
    print(f"Tools observed:    {len(mean_gain)}")
    print(f"Total budget:      {budget} calls")
    print(f"\nRecommended allocation (top {TOP_K}):")
    print(f"  {'Tool':<40} {'Gain':>8} {'Budget':>8}")
    print("  " + "-" * 58)
    for tool, calls_alloc in sorted(allocation.items(), key=lambda x: -x[1]):
        g = mean_gain.get(tool, 0)
        print(f"  {tool:<40} {g:>8.1f} {calls_alloc:>8}")

    # Efficiency: what fraction of budget goes to top-3 tools
    total_alloc = sum(allocation.values())
    top3_alloc  = sum(v for _, v in sorted(allocation.items(), key=lambda x: -x[1])[:3])
    efficiency  = top3_alloc / max(total_alloc, 1)
    print(f"\nConcentration (top-3 share): {efficiency:.2%}")
    if efficiency > 0.7:
        print("NOTE: budget heavily concentrated — consider diversifying tool usage")

    if not dry_run:
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({
            "ts": now,
            "sessions": sessions_processed,
            "budget": budget,
            "allocation": allocation,
            "mean_gain": {t: round(g, 2) for t, g in mean_gain.items()},
        }, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"Written: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Feedback budget optimizer")
    parser.add_argument("--budget",  type=int, default=BUDGET_TOTAL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run, budget=args.budget)


if __name__ == "__main__":
    main()
