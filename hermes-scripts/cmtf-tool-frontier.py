#!/usr/bin/env python3
"""
cmtf-tool-frontier.py — Causal Minimal Tool Filtering (CMTF).

Based on: arXiv:2606.06284 "ToolChoiceConfusion: Causal Minimal Tool Filtering".
Key result: CMTF reduces visible tools from 100 to ~1 per step via precondition-
effect contracts; 90% token reduction while matching strongest causal baseline.

Wave 16 implementation: a filtering layer that, given the current agent state
(last tool call, pending goal), returns the minimal set of tools causally needed
for the next step. Works without fine-tuning — contracts are heuristic.

Usage:
  python3 cmtf-tool-frontier.py --state-file JSONL  # filter from state
  python3 cmtf-tool-frontier.py --goal "read file"  # list causal next tools
  python3 cmtf-tool-frontier.py --audit              # show tool exposure stats
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "")
_RT = (_HH / "profiles" / _HP) if _HP else _HH
_CACHE = _RT / "cache"

EXPOSURE_LOG = _CACHE / "cmtf-exposure-log.jsonl"

# Causal precondition-effect contracts
# Format: precondition_patterns → available_next_tools
# These encode the "frontier" — only the minimal next-step tools needed.
TOOL_CONTRACTS = [
    # Reading/browsing → can now write or search
    {
        "preconditions": [r'\bread_file\b', r'\bweb_extract\b', r'\bweb_search\b'],
        "effects": ["write_file", "patch", "terminal", "browser_navigate"],
        "label": "read → write/navigate",
    },
    # Terminal command → can now read its output or issue another command
    {
        "preconditions": [r'\bterminal\b'],
        "effects": ["read_file", "terminal", "patch", "write_file"],
        "label": "terminal → read/patch",
    },
    # Writing/patching → should verify (compile/test)
    {
        "preconditions": [r'\bwrite_file\b', r'\bpatch\b'],
        "effects": ["terminal", "read_file", "browser_navigate"],
        "label": "write → verify",
    },
    # Search → refine or extract
    {
        "preconditions": [r'\bweb_search\b'],
        "effects": ["web_extract", "web_search", "write_file", "browser_navigate"],
        "label": "search → extract",
    },
    # Browser → can extract, search, or interact
    {
        "preconditions": [r'\bbrowser_navigate\b', r'\bbrowser_click\b'],
        "effects": ["web_extract", "browser_snapshot", "browser_type",
                    "browser_scroll", "browser_click", "browser_press"],
        "label": "browser → interact",
    },
    # Skill view → read more or update skill
    {
        "preconditions": [r'\bskill_view\b', r'\bskills_list\b'],
        "effects": ["skill_manage", "terminal", "write_file"],
        "label": "skill_view → manage",
    },
    # Memory → proceed with any tool (memory is often a setup step)
    {
        "preconditions": [r'\bhindsight_recall\b', r'\bhindsight_retain\b', r'\bmemory\b'],
        "effects": ["*"],  # any tool after memory lookup
        "label": "memory → any",
    },
    # Start of conversation (no last tool) → broad access
    {
        "preconditions": [r'^START$'],
        "effects": ["*"],
        "label": "start → any",
    },
]

# All known tools
ALL_TOOLS = [
    "read_file", "write_file", "patch", "search_files", "terminal",
    "web_search", "web_extract", "browser_navigate", "browser_snapshot",
    "browser_click", "browser_type", "browser_scroll", "browser_press",
    "browser_back", "browser_vision", "skill_view", "skills_list",
    "skill_manage", "memory", "hindsight_recall", "hindsight_retain",
    "hindsight_reflect", "execute_code", "delegate_task", "clarify",
    "vision_analyze",
]


def _last_tool_from_state(state_path: Path) -> str:
    """Extract the last tool call from a JSONL state file."""
    if not state_path.exists():
        return "START"
    lines = state_path.read_text(errors="ignore").splitlines()
    for line in reversed(lines):
        try:
            obj = json.loads(line)
            role = obj.get("role", "")
            if role in ("tool", "assistant"):
                content = str(obj.get("content", ""))
                # Extract tool name from content
                m = re.search(r'"name"\s*:\s*"([a-z_]+)"', content)
                if m:
                    return m.group(1)
        except (json.JSONDecodeError, KeyError):
            continue
    return "START"


def _frontier_for_state(last_tool: str, goal: str = "") -> list[str]:
    """
    Given the last tool call, return the minimal next-step tool frontier.
    """
    for contract in TOOL_CONTRACTS:
        # Check if last_tool matches any precondition
        for pattern in contract["preconditions"]:
            if re.search(pattern, last_tool, re.IGNORECASE):
                effects = contract["effects"]
                if effects == ["*"]:
                    return ALL_TOOLS  # no restriction
                # Filter by goal relevance if goal provided
                if goal:
                    goal_lower = goal.lower()
                    relevant = [t for t in effects if any(
                        w in goal_lower for w in t.replace("_", " ").split()
                    )]
                    if relevant:
                        return relevant
                return effects

    # No match → conservative: all tools
    return ALL_TOOLS


def cmd_state(state_file: str) -> int:
    path = Path(state_file)
    last_tool = _last_tool_from_state(path)
    frontier = _frontier_for_state(last_tool)
    total = len(ALL_TOOLS)
    exposed = len(frontier)
    reduction = round(100 * (1 - exposed / total))

    print(f"[cmtf] Last tool: {last_tool}")
    print(f"[cmtf] Frontier ({exposed}/{total} tools, {reduction}% reduction):")
    print(f"  {frontier}")

    # Log
    _CACHE.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "last_tool": last_tool,
        "exposed": exposed,
        "total": total,
        "frontier": frontier,
    }
    try:
        with open(EXPOSURE_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    return 0


def cmd_goal(goal: str) -> int:
    frontier = _frontier_for_state("START", goal)
    total = len(ALL_TOOLS)
    exposed = len(frontier)
    print(f"[cmtf] Goal: {goal!r}")
    print(f"[cmtf] Causal frontier ({exposed}/{total} tools):")
    print(f"  {frontier}")
    return 0


def cmd_audit() -> int:
    if not EXPOSURE_LOG.exists():
        print("[cmtf] No exposure log found.")
        return 0
    lines = EXPOSURE_LOG.read_text().splitlines()
    if not lines:
        print("[cmtf] Exposure log is empty.")
        return 0
    entries = [json.loads(l) for l in lines if l.strip()]
    avg_exposed = sum(e.get("exposed", len(ALL_TOOLS)) for e in entries) / len(entries)
    avg_reduction = sum(
        100 * (1 - e.get("exposed", len(ALL_TOOLS)) / e.get("total", len(ALL_TOOLS)))
        for e in entries
    ) / len(entries)
    print(f"[cmtf] Audit: {len(entries)} tool calls logged")
    print(f"[cmtf] Avg tools exposed: {avg_exposed:.1f}/{len(ALL_TOOLS)}")
    print(f"[cmtf] Avg reduction: {avg_reduction:.1f}%")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="CMTF causal minimal tool filter")
    ap.add_argument("--state-file", metavar="JSONL", help="Path to session state JSONL")
    ap.add_argument("--goal", help="Goal description for frontier filtering")
    ap.add_argument("--audit", action="store_true", help="Show tool exposure stats")
    args = ap.parse_args()

    if args.state_file:
        return cmd_state(args.state_file)
    if args.goal:
        return cmd_goal(args.goal)
    if args.audit:
        return cmd_audit()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
