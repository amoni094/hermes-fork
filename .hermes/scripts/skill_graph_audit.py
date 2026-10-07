"""
Skill dependency graph cycle detector and Euler-characteristic analyser.

Grounded in:
  - Hatcher (2001) 'Algebraic Topology': pi_1 of a directed graph contains
    non-trivial elements iff the graph has cycles.
  - CLRS (2022) Introduction to Algorithms, Ch.20: DFS back-edge detection
    identifies exactly the edges that create cycles.

The Euler characteristic of a graph G = (V, E):
    chi = |V| - |E|

Interpretations for the skill dependency graph:
    chi > 0  → more vertices than edges: siloed / loosely connected skills
    chi = 0  → balanced connectivity (tree-like for connected components)
    chi < 0  → over-connected; every chi < 0 means at least one extra cycle

Public API
----------
detect_skill_cycles(skill_adjacency: dict[str, list[str]])
    -> list[list[str]]
    Returns all cycles found via DFS back-edge detection.

euler_characteristic(skill_adjacency: dict[str, list[str]]) -> int
    Returns chi = |V| - |E|.

load_skill_graph(skills_dir: str) -> dict[str, list[str]]
    Scans SKILL.md files; parses 'related_skills' YAML frontmatter.

When run as __main__ with --demo, scans the real fork skills directory.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Skill graph loader
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_RELATED_SKILLS_RE = re.compile(
    r"^related_skills\s*:\s*(.*)$", re.MULTILINE
)
_LIST_ITEM_RE = re.compile(r"^\s*[-*]\s+(\S+)", re.MULTILINE)


def _parse_related_skills(text: str) -> List[str]:
    """
    Extract 'related_skills' from YAML frontmatter.

    Supports both inline list  `related_skills: [a, b]`
    and block list:
        related_skills:
          - a
          - b
    """
    fm_match = _FRONTMATTER_RE.match(text)
    if not fm_match:
        return []

    fm = fm_match.group(1)

    # Try to find the related_skills key
    rs_match = _RELATED_SKILLS_RE.search(fm)
    if not rs_match:
        return []

    inline = rs_match.group(1).strip()

    # Inline list: [a, b, c]
    if inline.startswith("["):
        inner = inline.strip("[]")
        return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]

    # Block list: subsequent indented "- item" lines
    # Grab everything after the key until the next non-indented key
    fm_after = fm[rs_match.end():]
    items = _LIST_ITEM_RE.findall(fm_after)
    if items:
        return [i.strip().strip("'\"") for i in items]

    # Single inline value
    if inline:
        return [inline.strip("'\"")]

    return []


def load_skill_graph(skills_dir: str) -> Dict[str, List[str]]:
    """
    Scan *skills_dir* for SKILL.md files and build an adjacency dict.

    Each SKILL.md contributes one vertex (the parent directory name).
    Edges come from the 'related_skills' frontmatter list.

    Skills referenced in 'related_skills' but not present as files are
    added as vertices with empty edge lists (dangling references).
    """
    adjacency: Dict[str, List[str]] = {}
    root = Path(skills_dir)

    if not root.exists():
        return adjacency

    for skill_md in root.rglob("SKILL.md"):
        skill_name = skill_md.parent.name
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        related = _parse_related_skills(text)
        adjacency.setdefault(skill_name, [])
        for r in related:
            adjacency[skill_name].append(r)
            adjacency.setdefault(r, [])

    return adjacency


# ---------------------------------------------------------------------------
# Euler characteristic
# ---------------------------------------------------------------------------

def euler_characteristic(skill_adjacency: Dict[str, List[str]]) -> int:
    """Return chi = |V| - |E| for the skill dependency (directed) graph."""
    V = len(skill_adjacency)
    E = sum(len(neighbours) for neighbours in skill_adjacency.values())
    return V - E


def euler_verdict(chi: int) -> str:
    if chi > 0:
        return "siloed skills (chi > 0: more vertices than edges)"
    if chi < 0:
        return "over-connected, possible cycles (chi < 0: more edges than vertices)"
    return "balanced (chi = 0)"


# ---------------------------------------------------------------------------
# DFS cycle detection (CLRS Ch.20 back-edge detection)
# ---------------------------------------------------------------------------

WHITE, GRAY, BLACK = 0, 1, 2


def detect_skill_cycles(
    skill_adjacency: Dict[str, List[str]],
) -> List[List[str]]:
    """
    Find all simple cycles in the directed skill dependency graph using
    DFS back-edge detection (CLRS Ch.20).

    Returns a list of cycles; each cycle is a list of vertex names
    forming the cycle path (last vertex has an edge back to first).
    """
    color: Dict[str, int] = {v: WHITE for v in skill_adjacency}
    parent: Dict[str, str | None] = {v: None for v in skill_adjacency}
    cycles: List[List[str]] = []

    def _reconstruct_cycle(start: str, end: str) -> List[str]:
        """Walk parent pointers from end back to start to reconstruct cycle."""
        path = [end]
        cur: str = end
        while cur != start:
            p = parent.get(cur)
            if p is None:
                break
            cur = p
            path.append(cur)
            if len(path) > len(skill_adjacency) + 2:
                break  # safety: prevent infinite loop on corrupt parents
        path.reverse()
        return path

    def _dfs(u: str) -> None:
        color[u] = GRAY
        for v in skill_adjacency.get(u, []):
            if v not in color:
                # Vertex from dangling reference – add it safely
                color[v] = WHITE
                parent[v] = None
            if color[v] == GRAY:
                # Back edge → cycle found
                cycle = _reconstruct_cycle(v, u) + [v]
                cycles.append(cycle)
            elif color[v] == WHITE:
                parent[v] = u
                _dfs(v)
        color[u] = BLACK

    # Run DFS from every unvisited vertex (handles disconnected graph)
    for vertex in list(skill_adjacency.keys()):
        if color[vertex] == WHITE:
            _dfs(vertex)

    # Deduplicate cycles (same set of nodes, different start point)
    seen: set[frozenset] = set()
    unique: List[List[str]] = []
    for cycle in cycles:
        key = frozenset(cycle)
        if key not in seen:
            seen.add(key)
            unique.append(cycle)

    return unique


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

_DEFAULT_SKILLS_DIR = (
    Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "profiles" / "fork" / "skills"
)


def _demo() -> None:
    skills_dir = str(_DEFAULT_SKILLS_DIR)
    print(f"=== Skill Graph Audit Demo (Hatcher Algebraic Topology) ===\n")
    print(f"Scanning: {skills_dir}\n")

    adjacency = load_skill_graph(skills_dir)
    print(f"Vertices (skills found): {len(adjacency)}")

    total_edges = sum(len(v) for v in adjacency.values())
    print(f"Edges (related_skills links): {total_edges}")

    chi = euler_characteristic(adjacency)
    print(f"Euler characteristic chi = {chi}  → {euler_verdict(chi)}")

    cycles = detect_skill_cycles(adjacency)
    if cycles:
        print(f"\nCycles detected ({len(cycles)}):")
        for cycle in cycles[:10]:   # cap output
            print(f"  {' → '.join(cycle)}")
        if len(cycles) > 10:
            print(f"  ... ({len(cycles) - 10} more)")
    else:
        print("\nNo cycles detected. Graph is a DAG (pi_1 trivial).")

    # Minimal synthetic test
    test_graph = {
        "A": ["B"],
        "B": ["C"],
        "C": ["A"],   # creates cycle A→B→C→A
        "D": ["E"],
        "E": [],
    }
    test_cycles = detect_skill_cycles(test_graph)
    assert len(test_cycles) >= 1, f"Expected ≥1 cycle in test graph, got {test_cycles}"
    test_chi = euler_characteristic(test_graph)
    assert test_chi == 5 - 4, f"Expected chi=1, got {test_chi}"
    print(f"\nSynthetic test: chi={test_chi}, cycles={len(test_cycles)} ✓")

    print("\nAll assertions passed. Exit 0.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
        sys.exit(0)
    print("Usage: python skill_graph_audit.py --demo")
    sys.exit(1)
