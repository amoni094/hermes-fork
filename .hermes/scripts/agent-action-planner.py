#!/usr/bin/python3
"""
agent-action-planner.py

Replaces ad-hoc tool selection with a principled planning layer that models
multi-step tool sequences as a Markov Decision Process and selects actions
using a simple value function over expected state coverage.

Research basis (LLM agent planning survey, arXiv:2609.09219):
  Agent action planning: given a task description, generate a sequence of
  tool actions that maximises coverage of the task's information requirements,
  subject to a budget constraint on the number of tool calls.

Math basis:
  State s = (covered_intents, remaining_budget)
  Action a ∈ {tools}
  Value V(s) = sum of intent coverage weights for uncovered intents reachable in budget
  Policy π(s) = argmax_a Q(s, a) where Q(s,a) = intent_gain(a) + γ·V(next_state)

Features:
  - Zero LLM calls: uses keyword overlap for intent-coverage scoring
  - Reads available tools from Hermes tool manifest or uses builtin list
  - Produces an ordered action sequence with per-step expected coverage gain
  - Budget-aware: stops when marginal gain < threshold or budget exhausted

Usage:
  python3 agent-action-planner.py "debug failing tests and update documentation"
  python3 agent-action-planner.py --list-tools
  python3 agent-action-planner.py "research papers" --budget 5 --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE  = CACHE_DIR / "action-plan.json"

# Hermes tool manifest — canonical tool names with intent keywords
TOOL_MANIFEST: dict[str, list[str]] = {
    "web_search":        ["search", "find", "lookup", "research", "news", "query", "discover"],
    "web_extract":       ["extract", "read", "fetch", "page", "url", "content", "scrape", "download"],
    "terminal":          ["run", "execute", "command", "shell", "build", "compile", "test", "install",
                          "debug", "check", "verify", "deploy", "launch", "start", "git", "script"],
    "write_file":        ["write", "create", "save", "output", "generate", "file", "produce", "make"],
    "read_file":         ["read", "view", "open", "inspect", "check", "file", "examine", "load"],
    "patch":             ["edit", "modify", "update", "fix", "change", "refactor", "patch", "correct",
                          "revise", "adjust", "documentation", "docs", "comment"],
    "search_files":      ["find", "search", "grep", "locate", "files", "pattern", "scan"],
    "skill_view":        ["skill", "load", "capability", "procedure", "method", "workflow"],
    "skill_manage":      ["skill", "create", "update", "save", "procedure", "method", "document",
                          "documentation", "record", "capture"],
    "execute_code":      ["python", "script", "compute", "analyse", "calculate", "process", "analyse",
                          "evaluate", "run", "test", "verify"],
    "delegate_task":     ["delegate", "subagent", "parallel", "background", "spawn", "orchestrate"],
    "browser_exec":      ["browser", "webpage", "click", "navigate", "form", "login", "web", "ui"],
    "memory":            ["memory", "remember", "persist", "store", "fact", "note", "record"],
    "clarify":           ["ask", "clarify", "question", "confirm", "decision", "choose"],
    "vision_analyze":    ["image", "screenshot", "visual", "picture", "diagram", "photo"],
    "text_to_speech":    ["speak", "audio", "voice", "tts", "narrate"],
}

GAMMA = 0.85        # discount factor for future coverage
MIN_GAIN = 0.01     # stop adding actions if marginal gain < this (was 0.05)
DEFAULT_BUDGET = 6  # default max tool calls in plan


def _extract_intents(task: str) -> list[tuple[str, float]]:
    """Extract weighted intent keywords from task description."""
    # Simple: each clause gets equal weight
    clauses = re.split(r"\band\b|\bthen\b|\balso\b|,|;", task, flags=re.IGNORECASE)
    intents = []
    for clause in clauses:
        words = re.findall(r"[a-z]{3,}", clause.lower())
        if words:
            weight = 1.0 / len(clauses)
            intents.append((" ".join(words), weight))
    return intents if intents else [(task.lower(), 1.0)]


def _coverage_score(tool: str, intent_words: set[str]) -> float:
    """How well does this tool cover the given intent keywords?"""
    tool_kws = set(TOOL_MANIFEST.get(tool, []))
    if not tool_kws or not intent_words:
        return 0.0
    return len(tool_kws & intent_words) / len(intent_words | tool_kws)


def _plan(task: str, budget: int) -> list[dict]:
    """
    Greedy MDP-style action planning with discounted coverage.
    Returns ordered list of planned tool actions with coverage gain.
    """
    intents = _extract_intents(task)
    tools   = list(TOOL_MANIFEST.keys())

    covered: dict[str, float] = {}  # intent_phrase → covered fraction
    plan: list[dict] = []
    remaining_budget = budget
    step_discount = 1.0

    for _ in range(budget):
        if remaining_budget <= 0:
            break

        best_tool: str | None = None
        best_gain: float = 0.0
        best_intent: str = ""

        for tool in tools:
            if any(p["tool"] == tool for p in plan):
                continue  # don't repeat tools unless explicit
            tool_kws = set(TOOL_MANIFEST.get(tool, []))

            # Compute marginal coverage gain across all intents
            gain = 0.0
            primary_intent = ""
            for intent_phrase, weight in intents:
                intent_words = set(intent_phrase.split())
                already = covered.get(intent_phrase, 0.0)
                raw = _coverage_score(tool, intent_words)
                marginal = max(0.0, raw - already) * weight
                gain += marginal
                if marginal > 0 and not primary_intent:
                    primary_intent = intent_phrase

            discounted_gain = gain * step_discount
            if discounted_gain > best_gain:
                best_gain = discounted_gain
                best_tool = tool
                best_intent = primary_intent

        if best_tool is None or best_gain < MIN_GAIN * step_discount:
            break

        # Update coverage
        tool_kws = set(TOOL_MANIFEST.get(best_tool, []))
        for intent_phrase, _ in intents:
            intent_words = set(intent_phrase.split())
            raw = _coverage_score(best_tool, intent_words)
            covered[intent_phrase] = min(1.0, covered.get(intent_phrase, 0.0) + raw)

        plan.append({
            "step": len(plan) + 1,
            "tool": best_tool,
            "intent": best_intent,
            "coverage_gain": round(best_gain, 4),
            "cumulative_coverage": round(sum(covered.values()) / max(len(intents), 1), 4),
        })

        step_discount *= GAMMA
        remaining_budget -= 1

    return plan


def run(task: str, budget: int, dry_run: bool, list_tools: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()

    if list_tools:
        print("Available tools:")
        for t, kws in TOOL_MANIFEST.items():
            print(f"  {t:<20} {', '.join(kws[:4])}")
        return

    plan = _plan(task, budget)

    print(f"\n=== Agent Action Planner — {now[:10]} ===")
    print(f"Task:   '{task}'")
    print(f"Budget: {budget} tool calls  →  Plan length: {len(plan)}")
    print(f"\n  {'Step':<5} {'Tool':<22} {'Intent Covered':<28} {'Gain':<8} {'Cumul'}")
    print("  " + "-" * 72)
    for p in plan:
        print(f"  {p['step']:<5} {p['tool']:<22} {p['intent'][:27]:<28} "
              f"{p['coverage_gain']:<8.3f} {p['cumulative_coverage']:.3f}")

    final_cov = plan[-1]["cumulative_coverage"] if plan else 0.0
    print(f"\n  Final coverage: {final_cov:.1%}  ({len(plan)}/{budget} budget used)")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now, "task": task, "budget": budget, "plan": plan,
            "final_coverage": final_cov,
        }, indent=2))
        print(f"\nWritten: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", nargs="?",
                        default="research arxiv papers and implement code and run tests")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-tools", action="store_true")
    args = parser.parse_args()
    run(task=args.task, budget=args.budget, dry_run=args.dry_run, list_tools=args.list_tools)


if __name__ == "__main__":
    main()
