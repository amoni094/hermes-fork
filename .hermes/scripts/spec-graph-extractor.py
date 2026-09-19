#!/usr/bin/python3
"""
spec-graph-extractor.py

Treats specification documents (SKILL.md, plan files, task descriptions)
as queryable versioned graphs. Extracts entities and constraints, builds
an adjacency structure, and answers queries like "what must X complete
before Y?" without LLM calls.

CS SPIKE basis (CIT-CAD: Constraint Intent Tree-based CAD Code Generation):
applies constraint-intent graph extraction to Hermes spec documents.

Math basis: directed constraint graph G = (V, E, W) where
  V = entities (tasks, skills, tools, configs)
  E = constraint edges (depends_on, blocks, requires, produces)
  W = extracted from imperative verbs + prepositions in text

Features:
  - Parses SKILL.md, plan files, AGENTS.md
  - Extracts dependency edges via regex patterns on imperative sentences
  - Answers reachability / topological-order queries
  - Zero LLM calls — deterministic NLP only

Usage:
  python3 spec-graph-extractor.py ~/.hermes/skills/  # index all skills
  python3 spec-graph-extractor.py --query "what depends on github?"
  python3 spec-graph-extractor.py --dry-run
"""

from __future__ import annotations
import os

import argparse
import json
import re
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

HOME      = Path.home()
CACHE_DIR = HOME / ".hermes/cache/monitors"
GRAPH_OUT = CACHE_DIR / "spec-graph.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Patterns that signal constraint edges
_DEPENDS_PATTERNS = [
    r"(?i)\b(requires?|needs?|depends on|must have|call first)\b\s+['\"]?([a-z][a-z0-9_\-]+)",
    r"(?i)\b(after|before)\b\s+['\"]?([a-z][a-z0-9_\-]+)",
    r"(?i)\b(load|reload|view|import|activate)\s+['\"]?([a-z][a-z0-9_\-]+)",
]
_PRODUCES_PATTERNS = [
    r"(?i)\b(writes?|produces?|emits?|outputs?|writes to|saves? to)\b.{0,20}['\"]?([a-z][a-z0-9_\-\/\.]+)",
]
_ENTITY_PATTERN = re.compile(r"`([a-z][a-z0-9_\-\.]+\.(?:py|json|yaml|md|sh))`|`([a-z][a-z0-9_\-]+)`")


class Edge(NamedTuple):
    src: str
    dst: str
    label: str  # depends_on | produces | calls


def extract_entities(text: str, doc_name: str) -> set[str]:
    entities = set()
    for m in _ENTITY_PATTERN.finditer(text):
        e = m.group(1) or m.group(2)
        if e and len(e) > 3 and e != doc_name:
            entities.add(e)
    entities.add(doc_name)
    return entities


def extract_edges(text: str, doc_name: str) -> list[Edge]:
    edges = []
    for pattern in _DEPENDS_PATTERNS:
        for m in re.finditer(pattern, text):
            dst = m.group(2).strip("'\"").lower()
            if dst and dst != doc_name and len(dst) > 2:
                edges.append(Edge(src=doc_name, dst=dst, label="depends_on"))
    for pattern in _PRODUCES_PATTERNS:
        for m in re.finditer(pattern, text):
            dst = m.group(2).strip("'\"").lower()
            if dst and dst != doc_name and len(dst) > 2:
                edges.append(Edge(src=doc_name, dst=dst, label="produces"))
    return edges


def build_graph(spec_paths: list[Path]) -> tuple[set[str], list[Edge]]:
    all_entities: set[str] = set()
    all_edges: list[Edge] = []
    for p in spec_paths:
        try:
            text = p.read_text(errors="replace")
        except Exception:
            continue
        doc_name = p.parent.name if p.name == "SKILL.md" else p.stem
        entities = extract_entities(text, doc_name)
        edges    = extract_edges(text, doc_name)
        all_entities |= entities
        all_edges.extend(edges)
    # Deduplicate edges
    unique_edges = list({(e.src, e.dst, e.label): e for e in all_edges}.values())
    return all_entities, unique_edges


def reachable_from(node: str, edges: list[Edge]) -> list[str]:
    """BFS: what nodes are reachable from `node` via depends_on?"""
    adj: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e.label == "depends_on":
            adj[e.src].append(e.dst)
    visited, queue = set(), deque([node])
    while queue:
        cur = queue.popleft()
        if cur in visited:
            continue
        visited.add(cur)
        queue.extend(adj.get(cur, []))
    return sorted(visited - {node})


def what_depends_on(node: str, edges: list[Edge]) -> list[str]:
    """What entities depend on `node`?"""
    return sorted({e.src for e in edges if e.label == "depends_on" and e.dst == node})


def topological_order(nodes: set[str], edges: list[Edge]) -> list[str]:
    """Kahn's algorithm — returns [] if cycle detected."""
    in_degree: dict[str, int] = {n: 0 for n in nodes}
    adj: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e.label == "depends_on" and e.src in nodes and e.dst in nodes:
            adj[e.dst].append(e.src)
            in_degree[e.src] += 1
    queue = deque(n for n, d in in_degree.items() if d == 0)
    order = []
    while queue:
        n = queue.popleft()
        order.append(n)
        for succ in adj[n]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)
    return order if len(order) == len(nodes) else []


def run(spec_root: Path, query: str | None, dry_run: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()

    # Collect spec files
    spec_files: list[Path] = []
    if spec_root.is_file():
        spec_files = [spec_root]
    else:
        spec_files = list(spec_root.rglob("SKILL.md"))[:100]
        # Also check default skills
        default = HOME / ".hermes/skills"
        if default.exists() and default != spec_root:
            spec_files += list(default.rglob("SKILL.md"))[:100]

    print(f"[spec-graph] Indexing {len(spec_files)} spec files...")
    entities, edges = build_graph(spec_files)
    print(f"[spec-graph] Entities: {len(entities)},  Edges: {len(edges)}")

    edge_summary = [{"src": e.src, "dst": e.dst, "label": e.label} for e in edges]

    if query:
        # Parse query: "what depends on X?" / "what does X depend on?" / "order"
        q = query.lower()
        m = re.search(r"depends on ([a-z0-9_\-]+)", q)
        if m:
            node = m.group(1)
            result = what_depends_on(node, edges)
            print(f"\nEntities that depend on '{node}': {result}")
        m2 = re.search(r"what does ([a-z0-9_\-]+) depend", q)
        if m2:
            node = m2.group(1)
            result = reachable_from(node, edges)
            print(f"\n'{node}' transitively depends on: {result}")
        if "order" in q or "topolog" in q:
            order = topological_order(entities, edges)
            print(f"\nTopological order ({len(order)} nodes): {order[:20]}{'...' if len(order)>20 else ''}")
        if not m and not m2 and "order" not in q:
            print(f"Query not parsed. Try: 'what depends on <name>' / 'what does <name> depend on' / 'topological order'")

    if not dry_run:
        _tmp_graph_out = GRAPH_OUT.with_suffix('.tmp')
        _tmp_graph_out.write_text(json.dumps({
            "ts": now, "spec_files": len(spec_files),
            "entities": sorted(entities), "edges": edge_summary,
        }, indent=2))
        _tmp_graph_out.replace(GRAPH_OUT)
        print(f"\n[spec-graph] Graph written: {GRAPH_OUT}")
        print(f"[spec-graph] Top edges by src:")
        from collections import Counter
        top_srcs = Counter(e.src for e in edges).most_common(5)
        for src, cnt in top_srcs:
            print(f"  {src}: {cnt} outgoing edges")
    else:
        print("(dry-run)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec_root", nargs="?",
                        default=str(Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "profiles" / os.environ.get("HERMES_PROFILE", "fork") / "skills"),
                        type=Path)
    parser.add_argument("--query", "-q", default=None, help="Graph query")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(spec_root=args.spec_root, query=args.query, dry_run=args.dry_run)


if __name__ == "__main__":
    main()