#!/usr/bin/env python3
"""
ripple-mem-expander.py — RippleMem-inspired associative memory expansion.

Based on: RippleMem (arXiv:2607.18844) — Associative Recollection via anchor
expansion. Key idea: a recall query activates anchor nodes; those anchors trigger
ripple expansion along semantic similarity edges; the expanded set is ranked by
a recency+relevance product, not just cosine similarity.

Wave 16 implementation: augments unified-recall queries by expanding the initial
result set via skill+memory anchor graph expansion before final ranking.

Usage:
  python3 ripple-mem-expander.py --query "some query" --topk 5   # expand+rank
  python3 ripple-mem-expander.py --build-graph                    # build anchor graph
  python3 ripple-mem-expander.py --stats                          # graph stats
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# -- Profile-aware paths ------------------------------------------------------
_HH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_HP = os.environ.get("HERMES_PROFILE", "")
_RT = (_HH / "profiles" / _HP) if _HP else _HH
_CACHE = _RT / "cache"
_SKILLS = _RT / "skills"

GRAPH_FILE = _CACHE / "ripple-mem-graph.json"
RECALL_LOG = _CACHE / "ripple-mem-recall.jsonl"

# RippleMem hyperparams (from paper ablation at 2-hop, alpha=0.65)
HOP_LIMIT = 2         # max expansion hops
ALPHA = 0.65          # similarity threshold for edges
TOP_K_ANCHORS = 8     # initial anchors from semantic seed
RECENCY_HALF_LIFE = 7.0  # days; recency weight = exp(-age_days / half_life)


def _tokenize(text: str) -> set[str]:
    """Simple whitespace + punctuation tokenizer for BM25-like overlap."""
    return set(re.sub(r'[^a-z0-9\s]', ' ', text.lower()).split())


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _skill_text(skill_dir: Path) -> str:
    """Read skill SKILL.md and first-paragraph description."""
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        return skill_md.read_text(errors="ignore")[:2000]
    return ""


def build_graph() -> dict:
    """Build anchor similarity graph over all skills in profile."""
    skills = []
    for skill_dir in sorted(_SKILLS.iterdir()):
        if not skill_dir.is_dir():
            continue
        text = _skill_text(skill_dir)
        if not text:
            continue
        mtime = (skill_dir / "SKILL.md").stat().st_mtime if (skill_dir / "SKILL.md").exists() else 0
        skills.append({
            "name": skill_dir.name,
            "tokens": list(_tokenize(text)),
            "mtime": mtime,
            "snippet": text[:200],
        })

    # Build edges where Jaccard similarity >= ALPHA
    edges: dict[str, list[str]] = {s["name"]: [] for s in skills}
    for i, a in enumerate(skills):
        ta = set(a["tokens"])
        for b in skills[i+1:]:
            tb = set(b["tokens"])
            sim = _jaccard(ta, tb)
            if sim >= ALPHA:
                edges[a["name"]].append(b["name"])
                edges[b["name"]].append(a["name"])

    graph = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "nodes": {s["name"]: {"mtime": s["mtime"], "snippet": s["snippet"]} for s in skills},
        "edges": edges,
        "skill_count": len(skills),
    }
    _CACHE.mkdir(parents=True, exist_ok=True)
    tmp = GRAPH_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(graph, indent=2))
    tmp.replace(GRAPH_FILE)
    print(f"[ripple-mem] Built graph: {len(skills)} nodes, {sum(len(v) for v in edges.values())//2} edges")
    return graph


def load_graph() -> dict | None:
    if not GRAPH_FILE.exists():
        return None
    try:
        return json.loads(GRAPH_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _recency_weight(mtime: float) -> float:
    age_days = (time.time() - mtime) / 86400.0
    return math.exp(-age_days / RECENCY_HALF_LIFE)


def ripple_expand(query: str, topk: int = 5) -> list[dict]:
    """
    Expand a query using RippleMem associative expansion:
    1. Seed: top-K anchors by Jaccard similarity to query
    2. Ripple: BFS expansion along edges up to HOP_LIMIT
    3. Rank: by recency-weighted similarity score
    """
    graph = load_graph()
    if not graph:
        print("[ripple-mem] No graph. Run --build-graph first.", file=sys.stderr)
        return []

    nodes = graph["nodes"]
    edges = graph["edges"]
    query_tokens = _tokenize(query)

    # Step 1: Seed anchors — compute similarity to all nodes
    sims = {}
    for name, node in nodes.items():
        node_tokens = _tokenize(node.get("snippet", ""))
        sims[name] = _jaccard(query_tokens, node_tokens)

    # Top-K anchors
    anchors = sorted(sims, key=lambda n: sims[n], reverse=True)[:TOP_K_ANCHORS]
    visited = set(anchors)
    frontier = list(anchors)

    # Step 2: BFS ripple expansion
    for _ in range(HOP_LIMIT):
        next_frontier = []
        for node in frontier:
            for neighbor in edges.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.append(neighbor)
        frontier = next_frontier

    # Step 3: Rank expanded set by recency × similarity
    results = []
    for name in visited:
        node = nodes.get(name, {})
        sim = sims.get(name, 0.0)
        rec = _recency_weight(node.get("mtime", 0))
        combined = 0.7 * sim + 0.3 * rec
        results.append({
            "skill": name,
            "similarity": round(sim, 3),
            "recency_weight": round(rec, 3),
            "score": round(combined, 3),
            "snippet": node.get("snippet", "")[:120],
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:topk]

    # Log recall
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "query": query[:200],
        "topk": topk,
        "anchors": anchors[:5],
        "expanded_pool": len(visited),
        "results": [r["skill"] for r in results],
    }
    try:
        with open(RECALL_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except OSError:
        pass

    return results


def cmd_build_graph() -> int:
    build_graph()
    return 0


def cmd_query(query: str, topk: int) -> int:
    results = ripple_expand(query, topk)
    if not results:
        print("[ripple-mem] No results.")
        return 0
    print(f"[ripple-mem] Top-{topk} for query: {query!r}")
    for i, r in enumerate(results):
        print(f"  {i+1}. {r['skill']} (score={r['score']:.3f}, "
              f"sim={r['similarity']:.3f}, rec={r['recency_weight']:.3f})")
        if r["snippet"]:
            print(f"     {r['snippet'][:80]}...")
    return 0


def cmd_stats() -> int:
    graph = load_graph()
    if not graph:
        print("[ripple-mem] No graph found. Run --build-graph first.")
        return 1
    n_edges = sum(len(v) for v in graph.get("edges", {}).values()) // 2
    print(f"[ripple-mem] Graph: {graph.get('skill_count', 0)} nodes, {n_edges} edges")
    print(f"[ripple-mem] Built: {graph.get('ts', 'unknown')}")
    if RECALL_LOG.exists():
        lines = RECALL_LOG.read_text().splitlines()
        print(f"[ripple-mem] Recall log: {len(lines)} entries")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="RippleMem associative memory expansion")
    ap.add_argument("--query", help="Query to expand")
    ap.add_argument("--topk", type=int, default=5, help="Number of results")
    ap.add_argument("--build-graph", action="store_true", help="Build anchor similarity graph")
    ap.add_argument("--stats", action="store_true", help="Graph stats")
    args = ap.parse_args()

    if args.build_graph:
        return cmd_build_graph()
    if args.query:
        return cmd_query(args.query, args.topk)
    if args.stats:
        return cmd_stats()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
