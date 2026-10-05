#!/usr/bin/env python3
"""
evograph-skill-editor.py — EvoGraph-Mem failure-aware skill insight editor.

Based on: EvoGraph-Mem (arXiv:2606.04917) — Failure-Aware Editable Insight Graph.
Key idea: LLM agent maintains an evolving "insight graph" of skill performance;
when a skill repeatedly fails or produces low-yield outcomes, its insight node
is updated to reflect failure patterns and alternative routing is triggered.

Wave 16 implementation: reads skill yield tracking data (from skill-yield-tracker.py)
and produces a graph of skill "health" edges, flagging skills that need review.
Integrates with skill-router-index to downrank consistently failing skills.

Usage:
  python3 evograph-skill-editor.py --build    # build insight graph from yield data
  python3 evograph-skill-editor.py --query SKILL  # query a skill's health
  python3 evograph-skill-editor.py --report   # report failing skills
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "")
_RT = (_HH / "profiles" / _HP) if _HP else _HH
_CACHE = _RT / "cache"

YIELD_DB = _CACHE / "skill-yield-state.db"
GRAPH_FILE = _CACHE / "evograph-insight-graph.json"
FAILURE_THRESHOLD = 0.35    # yield < this → mark for review
STREAK_THRESHOLD = 3        # consecutive failures to flag
RECOVERY_THRESHOLD = 0.6    # yield >= this → clear failure flag


def _load_yield_data() -> dict:
    """Load skill yield data from the yield tracker's JSON cache."""
    # skill-yield-tracker uses a JSON state file
    yield_cache = _CACHE / "skill-yield-state.json"
    if not yield_cache.exists():
        return {}
    try:
        return json.loads(yield_cache.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def build_graph() -> dict:
    """Build EvoGraph insight graph from yield data."""
    yield_data = _load_yield_data()
    nodes = {}
    edges = []

    for skill_name, data in yield_data.items():
        if not isinstance(data, dict):
            continue
        recent_yields = data.get("recent_yields", [])
        avg_yield = data.get("avg_yield", 0.5)
        call_count = data.get("call_count", 0)
        last_used = data.get("last_used", 0)

        # Determine health status
        if not recent_yields:
            status = "unknown"
            failure_streak = 0
        else:
            tail = recent_yields[-STREAK_THRESHOLD:]
            failure_streak = sum(1 for y in tail if y < FAILURE_THRESHOLD)
            if failure_streak >= STREAK_THRESHOLD:
                status = "failing"
            elif avg_yield >= RECOVERY_THRESHOLD:
                status = "healthy"
            elif avg_yield < FAILURE_THRESHOLD:
                status = "low-yield"
            else:
                status = "marginal"

        nodes[skill_name] = {
            "status": status,
            "avg_yield": round(avg_yield, 3),
            "call_count": call_count,
            "failure_streak": failure_streak,
            "last_used": last_used,
            "needs_review": status in ("failing", "low-yield"),
            "updated": datetime.now(timezone.utc).isoformat(),
        }

        # Edge: skills with similar failure patterns are likely related
        # (structural feature for future routing integration)
        if status in ("failing", "low-yield"):
            edges.append({"from": skill_name, "type": "needs_review", "reason": status})

    graph = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "node_count": len(nodes),
        "nodes": nodes,
        "edges": edges,
    }
    _CACHE.mkdir(parents=True, exist_ok=True)
    tmp = GRAPH_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(graph, indent=2))
    tmp.replace(GRAPH_FILE)

    failing = sum(1 for n in nodes.values() if n["needs_review"])
    print(f"[evograph] Built insight graph: {len(nodes)} skills, {failing} need review")
    return graph


def query_skill(skill_name: str) -> int:
    """Query a specific skill's health."""
    if not GRAPH_FILE.exists():
        print("[evograph] No graph found. Run --build first.")
        return 1
    graph = json.loads(GRAPH_FILE.read_text())
    node = graph.get("nodes", {}).get(skill_name)
    if not node:
        print(f"[evograph] Skill not found in graph: {skill_name}")
        return 1
    print(f"[evograph] {skill_name}:")
    print(f"  Status: {node['status']}")
    print(f"  Avg yield: {node['avg_yield']:.3f}")
    print(f"  Call count: {node['call_count']}")
    print(f"  Failure streak: {node['failure_streak']}")
    print(f"  Needs review: {node['needs_review']}")
    return 0


def report() -> int:
    """Report failing/low-yield skills."""
    if not GRAPH_FILE.exists():
        print("[evograph] No graph found. Run --build first.")
        return 1
    graph = json.loads(GRAPH_FILE.read_text())
    nodes = graph.get("nodes", {})
    flagged = [(name, node) for name, node in nodes.items() if node.get("needs_review")]

    print(f"[evograph] Graph: {len(nodes)} skills, {len(flagged)} flagged")
    print(f"[evograph] Built: {graph.get('ts', '?')}")
    if not flagged:
        print("[evograph] No skills need review.")
        return 0
    print("[evograph] Skills needing review:")
    for name, node in sorted(flagged, key=lambda x: x[1]["avg_yield"]):
        print(f"  {name}: {node['status']} (yield={node['avg_yield']:.3f}, "
              f"calls={node['call_count']}, streak={node['failure_streak']})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="EvoGraph skill health tracker")
    ap.add_argument("--build", action="store_true", help="Build insight graph from yield data")
    ap.add_argument("--query", metavar="SKILL", help="Query a skill's health")
    ap.add_argument("--report", action="store_true", help="Report failing skills")
    args = ap.parse_args()

    if args.build:
        build_graph()
        return 0
    if args.query:
        return query_skill(args.query)
    if args.report:
        return report()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
