#!/usr/bin/python3
"""
recursive-causal-explorer.py

Enables autonomous environment adaptation without retraining by building
causal graphs from observed tool call sequences — agents discover which
actions reliably cause which outcomes, enabling counterfactual reasoning.

Research basis (RSIAgent / recursive self-improvement — arXiv core agent sweep):
  Agents that accumulate causal models of their environment improve faster
  than those relying on static prompts. This script extracts (action, outcome)
  pairs from session history and builds a lightweight causal DAG using
  do-calculus-inspired edge scoring.

Math basis: causal discovery as conditional independence testing
  Edge A → B is retained iff P(B | do(A)) > P(B) + ε
  Estimated via: P(B|A) = count(A,B) / count(A)  (frequency proxy)
  Edge weight = P(B|A) - P(B)  (causal lift)
  Intervention distribution P(B | do(A)) approximated by observational
  data under the assumption of no hidden confounders within tool chains.

Usage:
  python3 recursive-causal-explorer.py             # build and query causal graph
  python3 recursive-causal-explorer.py --query "terminal" --effect "patch"
  python3 recursive-causal-explorer.py --top 10
  python3 recursive-causal-explorer.py --dry-run
"""
from __future__ import annotations
import os

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HOME         = Path.home()
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "fork")
_RT = _HH / "profiles" / _HP if _HP else _HH
SESSIONS_DIR = _RT / "sessions"
CACHE_DIR    = HOME / ".hermes/cache/monitors"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_FILE   = CACHE_DIR / "causal-graph.json"
OUT_FILE     = CACHE_DIR / "causal-exploration-report.json"

MIN_LIFT = 0.05   # minimum causal lift to retain an edge
MIN_COUNT = 2     # minimum co-occurrence count


def _extract_tool_sequence(session_path: Path) -> list[str]:
    """Extract ordered tool call names from a session JSONL."""
    tools = []
    for line in session_path.read_text().splitlines():
        try:
            ev      = json.loads(line)
            content = ev.get("api_content", ev.get("content", ""))
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tools.append(block.get("name", "unknown"))
        except Exception:
            pass
    return tools


def _build_causal_graph(sessions: list[list[str]]) -> dict:
    """
    Build causal graph from tool sequences.
    Edge A→B: tool B follows tool A within a window of 3 steps.
    """
    pair_counts: dict[tuple[str,str], int] = defaultdict(int)
    single_counts: dict[str, int]          = defaultdict(int)
    total_pairs = 0

    for seq in sessions:
        for i, tool in enumerate(seq):
            single_counts[tool] += 1
            for j in range(i+1, min(i+4, len(seq))):   # window=3
                pair_counts[(tool, seq[j])] += 1
                total_pairs += 1

    total_tools = sum(single_counts.values()) or 1

    # Compute causal lift for each pair
    edges = []
    for (a, b), count in pair_counts.items():
        if count < MIN_COUNT:
            continue
        p_a  = single_counts[a] / total_tools
        p_b  = single_counts[b] / total_tools
        p_ab = count / total_tools
        # Causal lift: P(B|A) - P(B)
        p_b_given_a = p_ab / p_a if p_a > 0 else 0.0
        lift        = p_b_given_a - p_b
        if lift >= MIN_LIFT:
            edges.append({
                "cause":  a,
                "effect": b,
                "lift":   round(lift, 4),
                "count":  count,
                "p_b_given_a": round(p_b_given_a, 4),
                "p_b":    round(p_b, 4),
            })

    edges.sort(key=lambda e: -e["lift"])
    return {
        "nodes":  dict(single_counts),
        "edges":  edges,
        "total_sessions": len(sessions),
        "total_tool_calls": total_tools,
    }


def _query_graph(graph: dict, cause: str, effect: str | None) -> list[dict]:
    edges = graph.get("edges", [])
    if effect:
        return [e for e in edges if e["cause"] == cause and e["effect"] == effect]
    return [e for e in edges if e["cause"] == cause or e["effect"] == cause]


def _load_graph() -> dict | None:
    if GRAPH_FILE.exists():
        try:
            return json.loads(GRAPH_FILE.read_text())
        except Exception:
            pass
    return None


def run(query_cause: str | None, query_effect: str | None,
        top_n: int, dry_run: bool) -> int:
    now   = datetime.now(timezone.utc).isoformat()
    paths = sorted(SESSIONS_DIR.glob("*.jsonl"))

    sequences = [_extract_tool_sequence(p) for p in paths]
    sequences = [s for s in sequences if s]   # drop empty

    if not sequences:
        print(f"[causal-explorer] No tool sequences found — need sessions with tool calls")
        # Load cached graph if exists
        graph = _load_graph()
        if graph:
            print(f"[causal-explorer] Using cached graph: {graph.get('total_sessions',0)} sessions")
        else:
            print("[causal-explorer] No cached graph — dry-run with synthetic data")
            # Synthetic demo
            sequences = [
                ["web_search", "web_extract", "write_file", "terminal"],
                ["web_search", "web_extract", "patch", "terminal"],
                ["skill_view", "write_file", "terminal", "patch"],
                ["skill_view", "patch", "terminal"],
                ["web_search", "write_file", "patch"],
            ]
            graph = _build_causal_graph(sequences)
    else:
        graph = _build_causal_graph(sequences)

    print(f"\n=== Recursive Causal Explorer — {now[:10]} ===")
    print(f"Sessions: {graph['total_sessions']} | Tool calls: {graph['total_tool_calls']}")
    print(f"Nodes: {len(graph['nodes'])} tools | Edges: {len(graph['edges'])} causal links")

    if query_cause:
        results = _query_graph(graph, query_cause, query_effect)
        if results:
            print(f"\nCausal edges for '{query_cause}':")
            for e in results[:10]:
                print(f"  {e['cause']} → {e['effect']}  lift={e['lift']:.4f}  "
                      f"P(effect|cause)={e['p_b_given_a']:.4f}  n={e['count']}")
        else:
            print(f"No edges found for cause='{query_cause}'")
    else:
        print(f"\nTop {top_n} causal links (by lift):")
        for e in graph["edges"][:top_n]:
            print(f"  {e['cause']:<22} → {e['effect']:<22} lift={e['lift']:.4f}  "
                  f"P(e|c)={e['p_b_given_a']:.4f}  n={e['count']}")

    # Counterfactual summary: what would happen if we always used top cause?
    if graph["edges"]:
        top_edge = graph["edges"][0]
        print(f"\nCounterfactual: if '{top_edge['cause']}' is used, "
              f"'{top_edge['effect']}' follows with P={top_edge['p_b_given_a']:.2f} "
              f"(vs baseline {top_edge['p_b']:.2f})")

    if not dry_run:
        _tmp_graph_file = GRAPH_FILE.with_suffix('.tmp')
        _tmp_graph_file.write_text(json.dumps(graph, indent=2))
        _tmp_graph_file.replace(GRAPH_FILE)
        _tmp_out_file = OUT_FILE.with_suffix('.tmp')
        _tmp_out_file.write_text(json.dumps({"ts": now, "graph_summary": {
            "nodes": len(graph["nodes"]), "edges": len(graph["edges"]),
            "top_edges": graph["edges"][:5],
        }}, indent=2))
        _tmp_out_file.replace(OUT_FILE)
        print(f"\nGraph saved: {GRAPH_FILE}")

    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--query",  default=None, metavar="CAUSE_TOOL")
    p.add_argument("--effect", default=None, metavar="EFFECT_TOOL")
    p.add_argument("--top",    type=int, default=10)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(run(args.query, args.effect, args.top, args.dry_run))


if __name__ == "__main__":
    main()
