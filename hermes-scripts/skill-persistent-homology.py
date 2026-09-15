#!/usr/bin/env python3
"""
skill-persistent-homology.py — Persistent homology on the Hermes skill graph.

Pure Python + scipy + networkx only (no gudhi / ripser / POT).

Algorithm
---------
1. Load all SKILL.md files from ~/.hermes/skills/ and
   ~/.hermes/profiles/fork/skills/ and parse the `description` field.
2. Build a complete weighted graph:
      edge weight  = 1 - jaccard(tokens_a, tokens_b)
   where tokens_* come from splitting the description into lower-case words.
3. Vietoris-Rips filtration (scratch implementation):
   - Sort all edges by weight.
   - Walk thresholds epsilon ∈ sorted edge weights.
   - H0 (connected components): union-find tracking.
       birth = 0 for every node; death = epsilon at which it merges into an
       older component. Component that never merges gets death = None.
   - H1 (independent cycles): whenever adding an edge creates a cycle in the
       current subgraph (detected via networkx has_path / cycle detection),
       record birth = that edge weight, death = None (persists to infinity).
4. Output barcode as JSON:
     { "h0": [{birth, death, component_size}],
       "h1": [{birth, death, cycle_length}] }

CLI subcommands
---------------
  barcode    Full persistence diagram JSON.
  gaps       H0 bars with death=null (persistent isolated components).
  redundant  H1 bars with birth < 0.3 (early-forming cycles = redundant clusters).
  summary    Counts + top-5 most persistent features by |death-birth|.

Usage
-----
  python skill-persistent-homology.py barcode
  python skill-persistent-homology.py gaps
  python skill-persistent-homology.py redundant
  python skill-persistent-homology.py summary
"""

from __future__ import annotations

import re
import sys
import json
import argparse
from pathlib import Path
from itertools import combinations

import networkx as nx

# ---------------------------------------------------------------------------
# Skill directories
# ---------------------------------------------------------------------------

SKILLS_DIRS = [
    Path.home() / ".hermes" / "skills",
    Path.home() / ".hermes" / "profiles" / "fork" / "skills",
]

# ---------------------------------------------------------------------------
# Skill loading  (mirrors skill-graph-walk.py patterns)
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_FIELD_RE = {
    "name": re.compile(r"^name:\s*(.+)$", re.MULTILINE),
    "description": re.compile(r"^description:\s*(.+)$", re.MULTILINE),
}


def _extract_frontmatter(text: str) -> dict:
    m = _FM_RE.match(text)
    if not m:
        return {}
    fm = m.group(1)
    out = {}
    for key, pat in _FIELD_RE.items():
        hit = pat.search(fm)
        if hit:
            out[key] = hit.group(1).strip()
    return out


def load_skills() -> dict[str, dict]:
    """Return {skill_name: {description, path}}."""
    skills: dict[str, dict] = {}
    for root in SKILLS_DIRS:
        if not root.is_dir():
            continue
        for skill_md in root.rglob("SKILL.md"):
            if ".archive" in skill_md.parts:
                continue
            try:
                text = skill_md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm = _extract_frontmatter(text)
            name = fm.get("name") or skill_md.parent.name
            desc = fm.get("description", "")
            # Prefer the one that has a non-empty description; avoid duplicates.
            if name in skills and skills[name].get("description"):
                continue
            skills[name] = {"description": desc, "path": str(skill_md)}
    return skills


# ---------------------------------------------------------------------------
# Keyword tokenisation & Jaccard distance
# ---------------------------------------------------------------------------

_STOP = frozenset(
    "a an the and or in of to for with by on at is are was were be been "
    "being have has had do does did will would could should may might "
    "this that these those it its when use using used as from if".split()
)


def _tokens(text: str) -> frozenset[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return frozenset(w for w in words if w not in _STOP and len(w) > 1)


def jaccard_distance(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return 1.0 - inter / union


# ---------------------------------------------------------------------------
# Build weighted graph
# ---------------------------------------------------------------------------

def build_weighted_graph(skills: dict[str, dict]) -> nx.Graph:
    """
    Build complete weighted undirected graph.
    weight(u, v) = 1 - jaccard_similarity = jaccard_distance
    Only add edges that are meaningful (distance < 1.0), i.e. shared tokens exist.
    For the filtration we still need all pairs, but we cap at 1.0 to avoid bloat.
    For large skill sets we restrict to distance <= 0.99 to keep edge count tractable.
    """
    G = nx.Graph()
    names = list(skills.keys())
    tok = {n: _tokens(skills[n]["description"]) for n in names}

    for n in names:
        G.add_node(n)

    for a, b in combinations(names, 2):
        d = jaccard_distance(tok[a], tok[b])
        if d < 1.0:          # At least one shared token
            G.add_edge(a, b, weight=d)

    return G


# ---------------------------------------------------------------------------
# Union-Find (for H0 tracking)
# ---------------------------------------------------------------------------

class UnionFind:
    def __init__(self, nodes):
        self.parent = {n: n for n in nodes}
        self.rank = {n: 0 for n in nodes}
        # Track which representative is "older" (lower index in birth order)
        self.birth_index = {n: i for i, n in enumerate(nodes)}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        """Merge x and y. Return (survivor_root, killed_root) or None if same."""
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return None
        # Older component (lower birth_index) survives.
        if self.birth_index[rx] > self.birth_index[ry]:
            rx, ry = ry, rx  # rx is now the older one
        # ry merges into rx
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
            # Still want older to survive — re-check
        # Actually always keep the one with lower birth_index as parent
        bx = self.birth_index[self.find(rx)]
        by = self.birth_index[self.find(ry)]
        if bx <= by:
            survivor, killed = self.find(rx), self.find(ry)
        else:
            survivor, killed = self.find(ry), self.find(rx)
        self.parent[killed] = survivor
        if self.rank[survivor] == self.rank[killed]:
            self.rank[survivor] += 1
        return survivor, killed


# ---------------------------------------------------------------------------
# Vietoris-Rips filtration
# ---------------------------------------------------------------------------

def vietoris_rips_persistence(G: nx.Graph) -> dict:
    """
    Compute H0 and H1 persistence via Vietoris-Rips filtration.

    Returns:
        {
          "h0": [{"birth": float, "death": float|None, "component_size": int}],
          "h1": [{"birth": float, "death": None, "cycle_length": int}],
        }
    """
    nodes = list(G.nodes())
    edges = sorted(G.edges(data="weight"), key=lambda e: e[2])

    uf = UnionFind(nodes)

    # H0: each node starts as its own component (birth=0)
    # Map root -> component info
    comp_size: dict[str, int] = {n: 1 for n in nodes}
    h0_bars: list[dict] = []
    # All components born at epsilon=0
    # Deaths recorded when merged.

    # H1: track which edges form cycles
    h1_bars: list[dict] = []

    # Subgraph built incrementally for cycle detection
    current_G = nx.Graph()
    current_G.add_nodes_from(nodes)

    for u, v, w in edges:
        ru, rv = uf.find(u), uf.find(v)

        if ru == rv:
            # Edge creates a cycle in the current connected component.
            # Detect cycle length using the path already in the subgraph.
            try:
                path = nx.shortest_path(current_G, u, v)
                cycle_length = len(path)  # number of nodes in cycle
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                cycle_length = 2
            h1_bars.append({
                "birth": round(w, 6),
                "death": None,
                "cycle_length": cycle_length,
            })
        else:
            # Merging two components: record H0 death for the younger component.
            old_size_u = comp_size.get(ru, 1)
            old_size_v = comp_size.get(rv, 1)
            # Older component = lower birth_index
            bi_u = uf.birth_index[ru]
            bi_v = uf.birth_index[rv]
            if bi_u <= bi_v:
                survivor_root, killed_root = ru, rv
                killed_size = old_size_v
            else:
                survivor_root, killed_root = rv, ru
                killed_size = old_size_u

            h0_bars.append({
                "birth": 0.0,
                "death": round(w, 6),
                "component_size": killed_size,
            })

            # Merge in union-find
            uf.union(u, v)
            new_root = uf.find(u)
            comp_size[new_root] = old_size_u + old_size_v
            # Clean up old root entry if different
            for old_root in (ru, rv):
                if old_root != new_root and old_root in comp_size:
                    del comp_size[old_root]

        current_G.add_edge(u, v, weight=w)

    # Surviving H0 components (never merged) — death = None
    seen_roots: set[str] = set()
    for n in nodes:
        r = uf.find(n)
        if r not in seen_roots:
            seen_roots.add(r)
    # Each surviving root is a persistent component.
    for r in seen_roots:
        h0_bars.append({
            "birth": 0.0,
            "death": None,
            "component_size": comp_size.get(r, 1),
        })

    return {"h0": h0_bars, "h1": h1_bars}


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def _load_barcode() -> dict:
    skills = load_skills()
    G = build_weighted_graph(skills)
    return vietoris_rips_persistence(G)


def cmd_barcode(_args) -> None:
    barcode = _load_barcode()
    print(json.dumps(barcode, indent=2))


def cmd_gaps(_args) -> None:
    barcode = _load_barcode()
    gaps = [b for b in barcode["h0"] if b["death"] is None]
    print(json.dumps({"gaps": gaps, "count": len(gaps)}, indent=2))


def cmd_redundant(_args) -> None:
    barcode = _load_barcode()
    redundant = [b for b in barcode["h1"] if b["birth"] < 0.3]
    print(json.dumps({"redundant_clusters": redundant, "count": len(redundant)}, indent=2))


def _persistence(bar: dict) -> float:
    if bar["death"] is None:
        return float("inf")
    return abs(bar["death"] - bar["birth"])


def cmd_summary(_args) -> None:
    barcode = _load_barcode()
    h0 = barcode["h0"]
    h1 = barcode["h1"]

    # Finite persistence only for top-5 (inf ones always top, so separate)
    finite_h0 = [b for b in h0 if b["death"] is not None]
    inf_h0    = [b for b in h0 if b["death"] is None]
    finite_h1 = [b for b in h1 if b["death"] is not None]
    inf_h1    = [b for b in h1 if b["death"] is None]

    top5_h0 = sorted(finite_h0, key=_persistence, reverse=True)[:5]
    top5_h1 = sorted(finite_h1, key=_persistence, reverse=True)[:5]
    # Prepend any infinite ones (persistent gaps / cycles)
    top5_h0 = inf_h0[:5] + top5_h0
    top5_h1 = inf_h1[:5] + top5_h1

    result = {
        "h0_count": len(h0),
        "h1_count": len(h1),
        "h0_persistent_gaps": len(inf_h0),
        "h1_persistent_cycles": len(inf_h1),
        "top5_h0": top5_h0[:5],
        "top5_h1": top5_h1[:5],
    }
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Persistent homology on the Hermes skill graph.",
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("barcode",   help="Full persistence diagram JSON.")
    sub.add_parser("gaps",      help="H0 bars with death=null (persistent isolated components).")
    sub.add_parser("redundant", help="H1 bars with birth < 0.3 (early-forming cycles).")
    sub.add_parser("summary",   help="Counts and top-5 most persistent features.")

    args = parser.parse_args()

    dispatch = {
        "barcode":   cmd_barcode,
        "gaps":      cmd_gaps,
        "redundant": cmd_redundant,
        "summary":   cmd_summary,
    }

    fn = dispatch.get(args.cmd)
    if fn is None:
        parser.print_help()
        sys.exit(1)

    fn(args)


if __name__ == "__main__":
    main()
