#!/usr/bin/python3
"""
gdop-aware-tool-selector.py

Routes multi-step queries to tool chains with provably low uncertainty
amplification, using Geometric Dilution of Precision (GDOP) from
navigation theory.

Math basis (computational_geometry / estimation_theory): in GPS positioning,
GDOP measures how satellite geometry amplifies measurement noise into
position uncertainty: σ_pos = GDOP × σ_measurement. For Hermes tool chains:
  - Each tool call introduces measurement noise (latency, output variance)
  - Chaining tools compounds noise: σ_chain = GDOP_chain × σ_base
  - GDOP_chain = sqrt(trace((A^T A)^{-1})) where A is the tool-dependency matrix
  - Low GDOP chains concentrate information; high GDOP chains amplify noise

For a given query, compute GDOP for candidate tool orderings and prefer
the chain with lowest GDOP (most geometrically compact information flow).

Practically:
  - Tool dependency matrix A: rows = query dimensions, cols = tools
  - A[i,j] = fraction of query dimension i that tool j resolves
  - GDOP = sqrt(trace((A^T A)^{-1})) — scalar uncertainty amplification factor
  - Prefer chains where the GDOP-weighted residual is minimal
"""

from __future__ import annotations

import argparse
import json
import math
import re
from itertools import permutations
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
OUT_FILE  = CACHE_DIR / "gdop-tool-chains.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Tool capability profiles: which query dimensions each tool resolves
# Dimensions: [file_ops, web, code, memory, search, analysis]
TOOL_PROFILES: dict[str, np.ndarray] = {
    "read_file":        np.array([0.9, 0.0, 0.0, 0.1, 0.1, 0.2]),
    "write_file":       np.array([0.8, 0.0, 0.1, 0.1, 0.0, 0.1]),
    "terminal":         np.array([0.4, 0.0, 0.8, 0.1, 0.1, 0.3]),
    "web_search":       np.array([0.0, 0.9, 0.0, 0.1, 0.8, 0.2]),
    "web_extract":      np.array([0.0, 0.8, 0.0, 0.1, 0.6, 0.4]),
    "search_files":     np.array([0.6, 0.0, 0.1, 0.2, 0.7, 0.2]),
    "skill_view":       np.array([0.1, 0.0, 0.0, 0.8, 0.3, 0.5]),
    "execute_code":     np.array([0.2, 0.0, 0.9, 0.1, 0.1, 0.7]),
    "patch":            np.array([0.7, 0.0, 0.3, 0.1, 0.0, 0.2]),
    "browser_exec":     np.array([0.0, 0.9, 0.2, 0.0, 0.5, 0.4]),
}

DIM_NAMES = ["file_ops", "web", "code", "memory", "search", "analysis"]


def _gdop(tool_chain: list[str]) -> float:
    """
    Compute GDOP for a tool chain.
    A = stacked tool capability vectors (n_tools × n_dims).
    GDOP = sqrt(trace((A^T A)^{-1})).
    """
    vecs = [TOOL_PROFILES.get(t, np.ones(6) * 0.1) for t in tool_chain]
    if not vecs:
        return float("inf")
    A = np.vstack(vecs)   # shape: (n_tools, n_dims)
    ATA = A.T @ A
    try:
        inv = np.linalg.inv(ATA + np.eye(ATA.shape[0]) * 1e-4)  # regularize
        return float(np.sqrt(np.trace(inv)))
    except np.linalg.LinAlgError:
        return float("inf")


def _query_to_dims(query: str) -> np.ndarray:
    """Map query keywords to capability dimension weights."""
    q = query.lower()
    dims = np.zeros(6)
    if any(w in q for w in ["file","read","write","path","script"]):
        dims[0] = 1.0
    if any(w in q for w in ["web","search","url","browse","fetch"]):
        dims[1] = 1.0
    if any(w in q for w in ["code","python","run","execute","compile","test"]):
        dims[2] = 1.0
    if any(w in q for w in ["memory","skill","recall","remember","context"]):
        dims[3] = 1.0
    if any(w in q for w in ["find","search","grep","locate","list"]):
        dims[4] = 1.0
    if any(w in q for w in ["analyse","analyze","inspect","audit","check","monitor"]):
        dims[5] = 1.0
    if dims.sum() == 0:
        dims = np.ones(6) * 0.3  # uniform if no match
    return dims / dims.sum()


def recommend_chain(
    query: str,
    candidate_tools: list[str] | None = None,
    max_chain: int = 4,
) -> list[dict]:
    """
    Recommend tool orderings for a query ranked by ascending GDOP.
    Considers subsets of candidate_tools up to max_chain length.
    """
    if candidate_tools is None:
        candidate_tools = list(TOOL_PROFILES.keys())

    query_dims = _query_to_dims(query)

    # Filter tools by relevance to query dimensions
    relevant = []
    for t in candidate_tools:
        profile = TOOL_PROFILES.get(t, np.ones(6) * 0.1)
        relevance = float(np.dot(profile, query_dims))
        if relevance > 0.1:
            relevant.append((t, relevance))
    relevant.sort(key=lambda x: -x[1])
    top_tools = [t for t, _ in relevant[:6]]  # keep top 6 candidates

    # Enumerate chains of length 2–max_chain
    results: list[dict] = []
    seen_chains: set[tuple] = set()

    for length in range(2, min(max_chain + 1, len(top_tools) + 1)):
        for perm in permutations(top_tools, length):
            key = tuple(sorted(perm))
            if key in seen_chains:
                continue
            seen_chains.add(key)
            gdop = _gdop(list(perm))
            results.append({
                "chain": list(perm),
                "gdop": round(gdop, 4),
                "length": length,
            })

    results.sort(key=lambda x: x["gdop"])
    return results[:10]


def run(query: str, dry_run: bool = False) -> None:
    now = datetime.now(timezone.utc).isoformat()
    chains = recommend_chain(query)

    print(f"\n=== GDOP-Aware Tool Selector — {now[:10]} ===")
    print(f"Query: '{query}'")
    print(f"\n  {'GDOP':>6}  Chain")
    print("  " + "-" * 65)
    for c in chains:
        tools = " → ".join(c["chain"])
        print(f"  {c['gdop']:>6.3f}  {tools}")

    if chains:
        best = chains[0]
        print(f"\nRecommended chain (GDOP={best['gdop']:.3f}):")
        print(f"  {' → '.join(best['chain'])}")

    if not dry_run:
        OUT_FILE.write_text(json.dumps({
            "ts": now, "query": query, "chains": chains
        }, indent=2))
        print(f"Written: {OUT_FILE}")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser(description="GDOP-aware tool chain selector")
    parser.add_argument("query", nargs="?",
                        default="analyse code files and search memory for context",
                        help="Query to route")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(query=args.query, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
