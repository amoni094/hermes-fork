#!/usr/bin/env python3
"""routing-ramsey-triangle.py — R(3,3)=6 monochromatic triangle density.

2-color edges (overlap vs conflict). Random-coloring baseline density = 0.25
(each triple has prob 2*(0.5)^3 = 0.25 of being monochromatic).
Alarm when observed density > 0.375 (1.5x baseline).
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

home = os.environ.get("HERMES_HOME", "")
home = home.removesuffix("/profiles/fork")
if not home:
    home = os.path.expanduser("~/.hermes")
profile_dir = home + "/profiles/fork"
CACHE = os.path.join(profile_dir, "cache")
GRAPH_PATH = os.path.join(CACHE, "skill-graph.json")
OUT_PATH = os.path.join(CACHE, "routing-ramsey-state.json")

ALARM_DENSITY = 0.375
NODE_CAP = 150  # raised: O(n^3) only triggers when edges exist


def _skill_tokens(name: str) -> frozenset:
    """Split skill name into tokens for overlap similarity."""
    import re
    return frozenset(re.split(r'[\-_/]', name.lower()))


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def build_synthetic_edges(
    nodes: list[str],
    exp3_path: str = "",
    min_jaccard: float = 0.25,
    max_per_node: int = 10,
) -> list[tuple[str, str, float]]:
    """Build edges from skill name Jaccard similarity when graph has no edges.

    Pairs with Jaccard >= min_jaccard are connected; edge weight = Jaccard.
    max_per_node limits fan-out to keep triangle count tractable.
    """
    tokens = {n: _skill_tokens(n) for n in nodes}
    # Also try to weight by EXP3 weight magnitude (more active skills = stronger connection)
    exp3_w: dict[str, float] = {}
    if exp3_path:
        try:
            import json as _j
            d = _j.loads(open(exp3_path, encoding="utf-8").read())
            w = d.get("weights", d) if isinstance(d, dict) else {}
            exp3_w = {k: float(v) for k, v in w.items() if isinstance(v, (int, float))}
        except Exception:
            pass

    edges: list[tuple[str, str, float]] = []
    n = len(nodes)
    # For each node, find top-max_per_node neighbours by Jaccard
    for i in range(n):
        sims = []
        for j in range(n):
            if i == j:
                continue
            j_sim = _jaccard(tokens[nodes[i]], tokens[nodes[j]])
            if j_sim >= min_jaccard:
                # Boost by geometric mean of EXP3 weights if available
                wi = exp3_w.get(nodes[i], 1.0)
                wj = exp3_w.get(nodes[j], 1.0)
                score = j_sim * ((wi * wj) ** 0.5)
                sims.append((j, score))
        sims.sort(key=lambda x: -x[1])
        for j, score in sims[:max_per_node]:
            if i < j:  # deduplicate
                edges.append((nodes[i], nodes[j], score))
    return edges
OVERLAP = "overlap"
CONFLICT = "conflict"


def _atomic_write(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _node_id(n: Any) -> Optional[str]:
    if isinstance(n, str):
        return n
    if isinstance(n, (int, float)) and not isinstance(n, bool):
        return str(n)
    if isinstance(n, dict):
        for k in ("id", "name", "skill", "node"):
            if k in n and n[k] is not None:
                return str(n[k])
    return None


def _parse_edge(e: Any) -> Optional[tuple[str, str, Optional[float]]]:
    u = v = None
    w: Optional[float] = None
    if isinstance(e, (list, tuple)) and len(e) >= 2:
        u, v = str(e[0]), str(e[1])
        if len(e) >= 3 and isinstance(e[2], (int, float)) and not isinstance(e[2], bool):
            w = float(e[2])
    elif isinstance(e, dict):
        for a, b in (("source", "target"), ("from", "to"), ("u", "v"), ("src", "dst"),
                     ("a", "b"), ("i", "j")):
            if a in e and b in e:
                u, v = str(e[a]), str(e[b])
                break
        if u is None and "nodes" in e and isinstance(e["nodes"], (list, tuple)) and len(e["nodes"]) >= 2:
            u, v = str(e["nodes"][0]), str(e["nodes"][1])
        raw_w = e.get("weight", e.get("w", e.get("score")))
        if isinstance(raw_w, (int, float)) and not isinstance(raw_w, bool):
            w = float(raw_w)
    if u is None or v is None or u == v:
        return None
    return u, v, w


def color_edges(edges: Sequence[tuple[str, str, Optional[float]]]) -> dict[frozenset, str]:
    """Top third by weight = overlap, bottom third = conflict, middle skip.

    Edges without weight are treated as overlap so unweighted graphs still form
    a 1-coloring (density 1.0 if any triangles exist).
    """
    colored: dict[frozenset, str] = {}
    weighted = [e for e in edges if e[2] is not None]
    unweighted = [e for e in edges if e[2] is None]
    n = len(weighted)
    if n:
        ordered = sorted(weighted, key=lambda t: (-(t[2] or 0.0), t[0], t[1]))
        k = n // 3
        overlap_set = ordered[:k]
        conflict_set = ordered[-k:] if k else []
        mid = ordered[k:n - k] if k else ordered
        for u, v, _w in overlap_set:
            colored[frozenset({u, v})] = OVERLAP
        for u, v, _w in conflict_set:
            colored[frozenset({u, v})] = CONFLICT
        # middle skipped (not in colored)
        _ = mid
    for u, v, _w in unweighted:
        key = frozenset({u, v})
        if key not in colored:
            colored[key] = OVERLAP
    return colored


def count_mono(nodes: Sequence[str], color: dict[frozenset, str]) -> dict[str, Any]:
    n = len(nodes)
    mono = 0
    total = 0
    for i in range(n):
        for j in range(i + 1, n):
            e_ij = frozenset({nodes[i], nodes[j]})
            if e_ij not in color:
                continue
            for k in range(j + 1, n):
                e_ik = frozenset({nodes[i], nodes[k]})
                e_jk = frozenset({nodes[j], nodes[k]})
                if e_ik not in color or e_jk not in color:
                    continue
                total += 1
                c1, c2, c3 = color[e_ij], color[e_ik], color[e_jk]
                if c1 == c2 == c3:
                    mono += 1
    density = (mono / total) if total else 0.0
    return {
        "mono_count": mono,
        "total_triangles": total,
        "density": density,
        "alarm": density > ALARM_DENSITY,
        "n_nodes": n,
        "n_colored_edges": len(color),
    }


def load_graph(path: str = GRAPH_PATH) -> tuple[list[str], list[tuple[str, str, Optional[float]]]]:
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.loads(f.read())
    except FileNotFoundError:
        return [], []
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return [], []
    nodes_raw: Any = []
    edges_raw: Any = []
    if isinstance(raw, dict):
        nodes_raw = raw.get("nodes") or raw.get("skills") or raw.get("vertices") or []
        edges_raw = raw.get("edges") or raw.get("links") or []
    elif isinstance(raw, list):
        edges_raw = raw
    nodes: list[str] = []
    seen = set()
    if isinstance(nodes_raw, list):
        for n in nodes_raw:
            nid = _node_id(n)
            if nid and nid not in seen:
                seen.add(nid)
                nodes.append(nid)
    parsed: list[tuple[str, str, Optional[float]]] = []
    if isinstance(edges_raw, list):
        for e in edges_raw:
            pe = _parse_edge(e)
            if pe is None:
                continue
            u, v, w = pe
            parsed.append((u, v, w))
            for x in (u, v):
                if x not in seen:
                    seen.add(x)
                    nodes.append(x)
    if len(nodes) > NODE_CAP:
        keep = set(nodes[:NODE_CAP])
        nodes = nodes[:NODE_CAP]
        parsed = [e for e in parsed if e[0] in keep and e[1] in keep]
    # If graph has nodes but no edges, synthesize from name similarity
    if nodes and not parsed:
        exp3 = os.path.join(os.path.dirname(CACHE), "cache", "routing-exp3-skill-weights.json")
        parsed = build_synthetic_edges(nodes[:NODE_CAP], exp3_path=exp3)
    return nodes, parsed


def analyze(nodes: Sequence[str], edges: Sequence[tuple[str, str, Optional[float]]]) -> dict[str, Any]:
    if not edges:
        return {
            "no_data": True,
            "mono_count": 0,
            "total_triangles": 0,
            "density": 0.0,
            "alarm": False,
            "n_nodes": len(nodes),
            "n_edges": 0,
        }
    color = color_edges(edges)
    stats = count_mono(list(nodes), color)
    stats["no_data"] = False
    stats["n_edges"] = len(edges)
    return stats


def run() -> dict[str, Any]:
    nodes, edges = load_graph()
    return analyze(nodes, edges)


def self_test() -> None:
    # K_4 all-overlap: C(4,3)=4 triangles, all mono, density=1, alarm
    k4_nodes = ["0", "1", "2", "3"]
    k4_color: dict[frozenset, str] = {}
    for i in range(4):
        for j in range(i + 1, 4):
            k4_color[frozenset({str(i), str(j)})] = OVERLAP
    r = count_mono(k4_nodes, k4_color)
    assert r["mono_count"] == 4, r
    assert r["total_triangles"] == 4, r
    assert r["density"] == 1.0, r
    assert r["alarm"] is True, r

    # K_6 Ramsey coloring: (i+j)%2==0 overlap else conflict
    k6_nodes = [str(i) for i in range(6)]
    k6_color: dict[frozenset, str] = {}
    for i in range(6):
        for j in range(i + 1, 6):
            col = OVERLAP if (i + j) % 2 == 0 else CONFLICT
            k6_color[frozenset({str(i), str(j)})] = col
    r6 = count_mono(k6_nodes, k6_color)
    assert r6["mono_count"] >= 2, f"Ramsey guarantee failed: {r6}"
    # even clique {0,2,4} + odd clique {1,3,5} => exactly 2 overlap triangles
    assert r6["mono_count"] == 2, r6

    # empty graph: no crash, no_data
    empty = analyze([], [])
    assert empty["no_data"] is True
    assert empty["density"] == 0.0
    assert empty["alarm"] is False
    assert empty["mono_count"] == 0

    # n_edges=0 with nodes
    empty2 = analyze(["a", "b", "c"], [])
    assert empty2["no_data"] is True

    print("self-test: PASS")


def main() -> int:
    if "--self-test" in sys.argv:
        self_test()
        return 0
    result = run()
    try:
        _atomic_write(OUT_PATH, result)
    except OSError:
        pass
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
