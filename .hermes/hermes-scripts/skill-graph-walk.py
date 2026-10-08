#!/usr/bin/env python3
"""
skill-graph-walk.py — Graph-of-Skills dependency traversal for the Hermes skill library.

Usage:
    python skill-graph-walk.py <skill-name>
    python skill-graph-walk.py academic-literature-review
    python skill-graph-walk.py topo [--path DIR]
    python skill-graph-walk.py capability-reach --cap CAPABILITY [--path DIR] [--max-hops 3]
    python skill-graph-walk.py alt-path --from SRC --to DST [--weight tokens|hops]
    python skill-graph-walk.py sheaf-check [--provides-file PATH]

Based on arXiv:2604.05333 (Graph-of-Skills): flat skill loading saturates context and misses
prerequisite chains. This script reads depends_on/provides/or_deps frontmatter from all SKILL.md
files, builds a dependency graph, and returns the transitive closure for a requested skill sorted
topologically (deepest dependencies first, requested skill last).

Convention:
    depends_on: [skill-a, skill-b]   # ALL of these are required prerequisites
    or_deps: [skill-c, skill-d]      # ANY ONE of these suffices as an alternative
    provides: [capability-x, cap-y]  # capability tags this skill offers (outputs)

Graph-walk script location: ~/.hermes/scripts/skill-graph-walk.py
"""

import sys
import os
import re
import json
import argparse
import heapq
from pathlib import Path

SKILLS_DIR = Path.home() / ".hermes" / "skills"
TAXONOMY_PATH = Path.home() / ".hermes" / "cache" / "provides-taxonomy.json"


def parse_frontmatter(path: Path) -> dict:
    """Extract YAML frontmatter (between --- markers) from a SKILL.md file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    # Match opening --- and closing ---
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    fm_text = match.group(1)

    data = {}
    # Parse name
    name_m = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
    if name_m:
        data["name"] = name_m.group(1).strip()

    for field in ("depends_on", "provides", "or_deps"):
        items = _parse_list_field(fm_text, field)
        if items is not None:
            data[field] = items

    return data


def _parse_list_field(fm_text: str, field: str):
    """Parse an inline or block YAML list field. Returns None if absent."""
    m = re.search(rf"^{re.escape(field)}:\s*\[([^\]]*)\]", fm_text, re.MULTILINE)
    if m:
        return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]
    block_m = re.search(rf"^{re.escape(field)}:\s*\n((?:  - .+\n?)+)", fm_text, re.MULTILINE)
    if block_m:
        return [x.strip() for x in re.findall(r"  - (.+)", block_m.group(1))]
    return None


def load_all_skills(skills_dir=None) -> dict:
    """
    Walk ~/.hermes/skills/, read all SKILL.md frontmatter, return dict:
        skill_name -> {"path": Path, "depends_on": [...], "or_deps": [...], "provides": [...], "token_count": int}
    Skips .archive directory.
    """
    root = Path(skills_dir) if skills_dir else SKILLS_DIR
    skills = {}
    if not root.is_dir():
        return skills
    for skill_md in root.rglob("SKILL.md"):
        # Skip archived skills
        if ".archive" in skill_md.parts:
            continue
        fm = parse_frontmatter(skill_md)
        # Derive name from directory if not in frontmatter
        name = fm.get("name") or skill_md.parent.name
        try:
            body = skill_md.read_text(encoding="utf-8", errors="replace")
            token_count = max(len(body.split()), 1)
        except OSError:
            token_count = 1
        skills[name] = {
            "path": skill_md,
            "depends_on": fm.get("depends_on", []),
            "or_deps": fm.get("or_deps", []),
            "provides": fm.get("provides", []),
            "token_count": token_count,
        }
    return skills


def transitive_closure(skill_name: str, graph: dict) -> list:
    """
    Return transitive closure of skill_name: all transitive dependencies + skill itself.
    Result is topologically sorted: deepest deps first, requested skill last.
    Returns list of skill names.
    """
    visited = set()
    order = []

    def dfs(name: str):
        if name in visited:
            return
        visited.add(name)
        info = graph.get(name)
        if info is None:
            # Unknown skill referenced as dep — include as leaf
            order.append(name)
            return
        for dep in info.get("depends_on", []):
            dfs(dep)
        order.append(name)

    dfs(skill_name)
    return order


def topo_sort_with_cycles(skill_names, depends_on_map):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in skill_names}
    order = []
    cycles = []

    def visit(u):
        color[u] = GRAY
        for v in depends_on_map.get(u, []):
            if v not in color:
                continue  # unknown skill, skip
            if color[v] == GRAY:
                cycles.append((u, v))  # back edge
            elif color[v] == WHITE:
                visit(v)
        color[u] = BLACK
        order.append(u)

    for u in skill_names:
        if color[u] == WHITE:
            visit(u)
    order.reverse()  # prepend = reverse post-order
    return order, cycles


def _depends_on_map(graph: dict) -> dict:
    return {name: list(info.get("depends_on", [])) for name, info in graph.items()}


def cmd_topo(skills_dir=None) -> None:
    graph = load_all_skills(skills_dir)
    names = sorted(graph.keys())
    order, cycles = topo_sort_with_cycles(names, _depends_on_map(graph))
    cycle_pairs = [[u, v] for u, v in cycles]
    print(json.dumps({
        "order": order,
        "cycles": cycle_pairs,
        "cycle_free": len(cycle_pairs) == 0,
    }, indent=2))


def load_taxonomy(path=None) -> dict:
    p = Path(path) if path else TAXONOMY_PATH
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def cmd_capability_reach(cap: str, skills_dir=None, max_hops: int = 3) -> None:
    """BFS: skills that provide CAP (hops=0) and reverse-depends_on reachability."""
    from collections import deque

    taxonomy = load_taxonomy()
    raw = taxonomy if isinstance(taxonomy, dict) else {}
    if "vocabulary" in raw and not any(
        isinstance(v, list) for v in raw.values() if not isinstance(v, str)
    ):
        # Old vocabulary-only format — provides_map is empty
        provides_map = {}
    else:
        provides_map = {k: v for k, v in raw.items() if isinstance(v, list)}
    provides_map.pop("vocabulary", None)
    vocab = taxonomy.get("vocabulary", [])
    vocab_set = set(vocab)
    if cap not in vocab_set:
        print("unknown capability; see provides-taxonomy.json", file=sys.stderr)
        sys.exit(1)

    graph = load_all_skills(skills_dir)
    for info in graph.values():
        info["provides"] = [p for p in info.get("provides", []) if p in vocab_set]

    dependents = {name: [] for name in graph}
    for name, info in graph.items():
        for dep in info.get("depends_on", []):
            if dep in dependents:
                dependents[dep].append(name)

    visited = set()
    queue = deque()
    for name, info in graph.items():
        if cap in info.get("provides", []):
            queue.append((name, 0, [name]))
            visited.add(name)

    results = []
    while queue:
        name, hops, path = queue.popleft()
        results.append({"name": name, "hops": hops, "path": path})
        if hops >= max_hops:
            continue
        for child in dependents.get(name, []):
            if child not in visited:
                visited.add(child)
                queue.append((child, hops + 1, path + [child]))

    results.sort(key=lambda x: (x["hops"], x["name"]))
    print(json.dumps({
        "capability": cap,
        "skills": results,
        "vocabulary": vocab,
    }, indent=2))


ALT_PATH_NOTE = "or_deps edges are OR-alternatives; depends_on edges are AND-required"


def _edge_weight(dest: str, graph: dict, weight_mode: str) -> int:
    if weight_mode == "hops":
        return 1
    info = graph.get(dest) or {}
    return max(int(info.get("token_count") or 1), 1)


def cmd_alt_path(src: str, dst: str, weight_mode: str = "tokens", skills_dir=None) -> None:
    """Dijkstra over depends_on + or_deps edges. Diagnostic shortest alternative path."""
    graph = load_all_skills(skills_dir)
    adj = {}
    for name, info in graph.items():
        adj.setdefault(name, [])
        for dep in info.get("depends_on", []) + info.get("or_deps", []):
            adj.setdefault(dep, [])
            adj[name].append((dep, _edge_weight(dep, graph, weight_mode)))

    if src not in adj:
        print("no path found")
        return
    if src == dst:
        print(json.dumps({
            "path": [src],
            "cost": 0,
            "weight_mode": weight_mode,
            "note": ALT_PATH_NOTE,
        }))
        return

    dist = {src: 0}
    prev = {}  # node -> predecessor (src has no predecessor)
    pq = [(0, src)]
    seen = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in seen:
            continue
        seen.add(u)
        if u == dst:
            break
        for v, w in adj.get(u, []):
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    if dst not in dist:
        print("no path found")
        return

    path = []
    cur = dst
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()
    print(json.dumps({
        "path": path,
        "cost": int(dist[dst]),
        "weight_mode": weight_mode,
        "note": ALT_PATH_NOTE,
    }))


def _parse_frontmatter_sheaf(text: str) -> dict:
    """YAML frontmatter parser for sheaf-check. Uses PyYAML if present, else a minimal parser."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), None)
    if end is None:
        return {}
    block = "\n".join(lines[1:end])
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(block)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass
    result = {}
    current_list = None
    for line in lines[1:end]:
        m = re.match(r"^(\w[\w_-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val == "":
                current_list = key
                result[key] = []
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                result[key] = [x.strip().strip("'\"") for x in inner.split(",") if x.strip()] if inner else []
                current_list = None
            else:
                result[key] = val
                current_list = None
            continue
        lm = re.match(r"^\s*-\s+(.+)$", line)
        if lm and current_list is not None:
            result.setdefault(current_list, [])
            if not isinstance(result[current_list], list):
                result[current_list] = []
            result[current_list].append(lm.group(1).strip().strip("'\""))
    return result


def _as_str_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("[") and s.endswith("]"):
            inner = s[1:-1].strip()
            return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()] if inner else []
        if s:
            return [s]
    return []


def _load_sheaf_skills(skills_dir=None) -> dict:
    """Load depends_on/or_deps from every .md file under the skills tree."""
    root = Path(skills_dir) if skills_dir else SKILLS_DIR
    skills = {}
    if not root.is_dir():
        return skills
    for md in root.rglob("*.md"):
        if ".archive" in md.parts:
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = _parse_frontmatter_sheaf(text)
        if md.name.lower() == "skill.md":
            name = str(fm.get("name") or md.parent.name).strip()
        else:
            name = str(fm.get("name") or md.stem).strip()
        if not name:
            continue
        entry = {
            "depends_on": _as_str_list(fm.get("depends_on")),
            "or_deps": _as_str_list(fm.get("or_deps")),
        }
        prev = skills.get(name)
        if prev:
            # Merge duplicate stems without dropping edges.
            deps = list(dict.fromkeys(prev["depends_on"] + entry["depends_on"]))
            ors = list(dict.fromkeys(prev["or_deps"] + entry["or_deps"]))
            skills[name] = {"depends_on": deps, "or_deps": ors}
        else:
            skills[name] = entry
    return skills


def _taxonomy_skill_provides(raw) -> dict:
    """Extract skill_name -> [capability_tag, ...] from provides-taxonomy.json."""
    if not isinstance(raw, dict) or not raw:
        return {}
    provides = {}

    def take_mapping(mapping):
        if not isinstance(mapping, dict):
            return
        for k, v in mapping.items():
            if isinstance(v, list):
                provides[str(k)] = [str(x) for x in v if str(x).strip()]

    take_mapping(raw)
    for wrap in ("skills", "provides", "taxonomy"):
        if isinstance(raw.get(wrap), dict):
            take_mapping(raw[wrap])
    # Drop non-skill metadata keys that happen to hold lists (e.g. vocabulary).
    provides.pop("vocabulary", None)
    return provides


def _direct_provides(skill, provides_map):
    """Direct provides for a skill (not transitive)."""
    return set(provides_map.get(skill) or [])


def _forward_provides_reach(skill: str, graph: dict, provides_map: dict, cache: dict) -> set:
    """BFS from skill over depends_on+or_deps; union of reachable provides tags."""
    from collections import deque

    if skill in cache:
        return cache[skill]
    tags = set()
    seen = set()
    q = deque([skill])
    while q:
        u = q.popleft()
        if u in seen:
            continue
        seen.add(u)
        tags.update(provides_map.get(u, []))
        info = graph.get(u) or {}
        for v in list(info.get("depends_on") or []) + list(info.get("or_deps") or []):
            if v not in seen:
                q.append(v)
    cache[skill] = tags
    return tags


def cmd_sheaf_check(provides_file=None) -> None:
    """Diagnostic sheaf consistency over A->B->C depends_on triples."""
    p = Path(provides_file) if provides_file else TAXONOMY_PATH
    if not p.is_file() or p.stat().st_size == 0:
        print(json.dumps({
            "consistent": True,
            "total_triples": 0,
            "reason": "no_taxonomy",
            "diagnostic_only": True,
        }))
        return
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(json.dumps({
            "consistent": True,
            "total_triples": 0,
            "reason": "no_taxonomy",
            "diagnostic_only": True,
        }))
        return
    if not raw:
        print(json.dumps({
            "consistent": True,
            "total_triples": 0,
            "reason": "no_taxonomy",
            "diagnostic_only": True,
        }))
        return

    if not isinstance(raw, dict):
        provides_map = {}
    elif "vocabulary" in raw and not any(
        isinstance(v, list) for v in raw.values() if not isinstance(v, str)
    ):
        # Old vocabulary-only format — provides_map is empty
        provides_map = {}
    else:
        provides_map = {k: v for k, v in raw.items() if isinstance(v, list)}
    if isinstance(provides_map, dict):
        provides_map.pop("vocabulary", None)
    if not provides_map:
        print(json.dumps({
            "consistent": True,
            "total_triples": 0,
            "reason": "no_taxonomy",
            "diagnostic_only": True,
        }))
        return

    graph = _load_sheaf_skills()
    if not any(info.get("depends_on") for info in graph.values()):
        print(json.dumps({
            "consistent": True,
            "total_triples": 0,
            "reason": "no_dep_triples",
            "diagnostic_only": True,
        }))
        return

    # Triple scan uses ONLY depends_on (not or_deps). Sheaf consistency is
    # meaningful over strict AND-required chains, not OR-alternatives.
    dep_adj = {name: list(info.get("depends_on") or []) for name, info in graph.items()}

    triples = []
    triples_capped = False
    for a, bs in dep_adj.items():
        for b in bs:
            if b not in dep_adj:
                continue
            for c in dep_adj[b]:
                triples.append((a, b, c))
                if len(triples) >= 500:
                    triples_capped = True
                    break
            if triples_capped:
                break
        if triples_capped:
            break

    violations = []
    for a, b, c in triples:
        # Direct provides only (not transitive). If A and C share a capability
        # that B does not directly provide, B is a gap in the chain.
        direct_a = _direct_provides(a, provides_map)
        direct_b = _direct_provides(b, provides_map)
        direct_c = _direct_provides(c, provides_map)
        shared_ac = direct_a & direct_c
        missing = shared_ac - direct_b
        if missing:
            violations.append({
                "a": a,
                "b": b,
                "c": c,
                "missing_caps": sorted(missing),
            })

    out = {
        "total_triples": len(triples),
        "violations": violations,
        "consistent": len(violations) == 0,
        "skills_with_provides": sum(1 for caps in provides_map.values() if caps),
        "diagnostic_only": True,
    }
    if triples_capped:
        out["triples_capped"] = True
    print(json.dumps(out))


def _parse_related_skills(fm_text: str) -> list:
    """Parse related_skills field (block or inline YAML list)."""
    # Block form: related_skills:\n  - item
    block_m = re.search(r"^related_skills:\s*\n((?:[ \t]+-[ \t]+.+\n?)+)", fm_text, re.MULTILINE)
    if block_m:
        return [x.strip() for x in re.findall(r"[ \t]+-[ \t]+(.+)", block_m.group(1))]
    # Inline form: related_skills: [a, b, c]
    inline_m = re.search(r"^related_skills:\s*\[([^\]]*)\]", fm_text, re.MULTILINE)
    if inline_m:
        return [x.strip().strip("'\"") for x in inline_m.group(1).split(",") if x.strip()]
    return []


def _load_graph_with_related(skills_dir=None):
    """
    Load all skills from skills_dir. Returns:
        skills: dict skill_name -> {path, category, depends_on, related_skills}
    Category is derived from the parent-of-parent directory name (top-level category dir).
    """
    root = Path(skills_dir) if skills_dir else SKILLS_DIR
    skills = {}
    if not root.is_dir():
        return skills
    for skill_md in root.rglob("SKILL.md"):
        if ".archive" in skill_md.parts:
            continue
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Frontmatter extraction
        fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        fm_text = fm_match.group(1) if fm_match else ""
        name_m = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
        name = name_m.group(1).strip() if name_m else skill_md.parent.name
        # Derive category: skills_dir/<category>/<skill-name>/SKILL.md
        parts = skill_md.relative_to(root).parts
        category = parts[0] if len(parts) >= 3 else "uncategorized"
        related = _parse_related_skills(fm_text)
        # Also include depends_on edges for richer graph
        deps = _parse_list_field(fm_text, "depends_on") or []
        or_d = _parse_list_field(fm_text, "or_deps") or []
        skills[name] = {
            "path": skill_md,
            "category": category,
            "related_skills": related,
            "depends_on": deps,
            "or_deps": or_d,
        }
    return skills


def _build_nx_graph(skills: dict, directed: bool = True):
    """Build a networkx graph from skills dict using related_skills + depends_on edges."""
    import networkx as nx
    G = nx.DiGraph() if directed else nx.Graph()
    for name in skills:
        G.add_node(name)
    for name, info in skills.items():
        for rel in info.get("related_skills", []):
            if rel in skills:
                G.add_edge(name, rel)
        for dep in info.get("depends_on", []):
            if dep in skills:
                G.add_edge(name, dep)
    return G


# ── HAT-1: topology ──────────────────────────────────────────────────────────

def cmd_topology(skills_dir=None) -> None:
    """HAT-1: Compute homology-inspired graph topology metrics (H0, H1, chi)."""
    import networkx as nx

    skills = _load_graph_with_related(skills_dir)
    G_dir = _build_nx_graph(skills, directed=True)
    G_und = G_dir.to_undirected()

    V = G_und.number_of_nodes()
    E = G_und.number_of_edges()
    H0 = nx.number_connected_components(G_und)   # 0th Betti: connected components
    H1 = E - V + H0                               # 1st Betti: independent cycles
    chi = V - E                                   # graph Euler characteristic (without F)

    print("=== HAT-1: Skill Graph Topology ===")
    print(f"  Vertices (skills)    V = {V}")
    print(f"  Edges (relations)    E = {E}")
    print(f"  H0 (components)      = {H0}")
    print(f"  H1 (cycles)          = {H1}")
    print(f"  chi = V - E          = {chi}")
    print()
    if H0 > 1:
        print(f"  ⚠ H0={H0} > 1: {H0} disconnected skill islands detected.")
        comps = sorted(nx.connected_components(G_und), key=len, reverse=True)
        print(f"    Largest component: {len(comps[0])} skills")
        small = [c for c in comps if len(c) <= 3]
        if small:
            print(f"    Small isolated clusters ({len(small)} total):")
            for c in small[:10]:
                print(f"      {sorted(c)}")
    else:
        print("  ✓ H0=1: all skills are connected in a single component.")
    if H1 > 0:
        print(f"  ⚠ H1={H1} > 0: circular dependency patterns present in graph.")
    else:
        print("  ✓ H1=0: no independent cycles (acyclic graph).")


# ── HAT-2: cw-complex ────────────────────────────────────────────────────────

def cmd_cw_complex(skills_dir=None) -> None:
    """HAT-2: CW-complex Euler characteristic chi = V - E + F (triangles as 2-faces)."""
    import networkx as nx
    from itertools import combinations

    skills = _load_graph_with_related(skills_dir)
    G_dir = _build_nx_graph(skills, directed=True)
    G_und = G_dir.to_undirected()

    V = G_und.number_of_nodes()
    E = G_und.number_of_edges()

    # Find all triangles (3-cliques)
    triangles = []
    nodes = list(G_und.nodes())
    for u, v, w in combinations(nodes, 3):
        if G_und.has_edge(u, v) and G_und.has_edge(v, w) and G_und.has_edge(u, w):
            triangles.append((u, v, w))

    F = len(triangles)
    chi = V - E + F

    print("=== HAT-2: CW-Complex Analysis ===")
    print(f"  Vertices (V)         = {V}")
    print(f"  Edges    (E)         = {E}")
    print(f"  Triangles/2-faces (F)= {F}")
    print(f"  chi = V - E + F      = {chi}")
    print()
    if F == 0:
        print("  No triangles found: graph has no 3-clique structures.")
    else:
        print(f"  {F} triangle(s) found (mutually related skill triplets):")
        for i, (u, v, w) in enumerate(triangles[:20], 1):
            print(f"    {i:3}. ({u}, {v}, {w})")
        if F > 20:
            print(f"    ... and {F - 20} more triangles.")


# ── HAT-3: cycle-basis ───────────────────────────────────────────────────────

def cmd_cycle_basis(skills_dir=None) -> None:
    """HAT-3: Compute cycle basis (generators of H1) of the undirected skill graph."""
    import networkx as nx

    skills = _load_graph_with_related(skills_dir)
    G_dir = _build_nx_graph(skills, directed=True)
    G_und = G_dir.to_undirected()

    cycles = nx.cycle_basis(G_und)

    print("=== HAT-3: Cycle Basis (H1 generators) ===")
    print(f"  Independent cycles found: {len(cycles)}")
    print()
    if not cycles:
        print("  No cycles: the skill graph is a forest (acyclic).")
    else:
        tight = []
        for i, cycle in enumerate(sorted(cycles, key=len), 1):
            length = len(cycle)
            warn = " ⚠ TIGHT CIRCULAR DEPENDENCY" if length <= 3 else ""
            print(f"  Cycle {i:3} (length={length}){warn}:")
            print(f"    {' → '.join(cycle + [cycle[0]])}")
            if length <= 3:
                tight.append(cycle)
        print()
        if tight:
            print(f"  ⚠ {len(tight)} tight circular dependencies (length ≤ 3) detected:")
            for c in tight:
                print(f"    {c}")
        else:
            print("  ✓ No tight circular dependencies (all cycles length > 3).")


# ── HAT-6: domain-gaps ───────────────────────────────────────────────────────

def cmd_domain_gaps(skills_dir=None) -> None:
    """HAT-6: Domain co-occurrence graph and isolated domain detection."""
    import networkx as nx

    root = Path(skills_dir) if skills_dir else SKILLS_DIR
    skills = _load_graph_with_related(skills_dir)

    # Build skill -> category map
    skill_to_domain = {name: info["category"] for name, info in skills.items()}
    domains = sorted(set(skill_to_domain.values()))

    # Build domain co-occurrence graph: edge if any skill links cross-domain via related_skills/depends_on
    D = nx.Graph()
    for d in domains:
        D.add_node(d)

    cross_edges = {}  # (d1, d2) -> count
    for name, info in skills.items():
        src_domain = skill_to_domain[name]
        all_refs = list(info.get("related_skills", [])) + list(info.get("depends_on", []))
        for ref in all_refs:
            dst_domain = skill_to_domain.get(ref)
            if dst_domain and dst_domain != src_domain:
                key = tuple(sorted([src_domain, dst_domain]))
                cross_edges[key] = cross_edges.get(key, 0) + 1

    for (d1, d2), count in cross_edges.items():
        D.add_edge(d1, d2, weight=count)

    H0 = nx.number_connected_components(D)
    isolated = sorted([d for d in D.nodes() if D.degree(d) == 0])

    print("=== HAT-6: Domain Co-occurrence & Coverage Gaps ===")
    print(f"  Total domains:              {len(domains)}")
    print(f"  Cross-domain link pairs:    {len(cross_edges)}")
    print(f"  H0 (domain components):     {H0}")
    print()
    if isolated:
        print(f"  ⚠ Isolated coverage islands ({len(isolated)} domains with zero cross-domain links):")
        for d in isolated:
            skill_count = sum(1 for s, info in skills.items() if info["category"] == d)
            print(f"    - {d} ({skill_count} skills)")
    else:
        print("  ✓ No isolated domains: all domains have cross-domain skill links.")
    print()
    print("  Domain connectivity (cross-domain edge counts):")
    # Sort by degree descending
    degree_list = sorted(D.degree(), key=lambda x: x[1], reverse=True)
    for d, deg in degree_list:
        skill_count = sum(1 for s, info in skills.items() if info["category"] == d)
        print(f"    {d:40s}  degree={deg}  skills={skill_count}")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <skill-name>", file=sys.stderr)
        print(f"       python {sys.argv[0]} topo [--path DIR]", file=sys.stderr)
        print(f"       python {sys.argv[0]} capability-reach --cap CAPABILITY [--path DIR] [--max-hops 3]", file=sys.stderr)
        print(f"       python {sys.argv[0]} alt-path --from SRC --to DST [--weight tokens|hops]", file=sys.stderr)
        print(f"       python {sys.argv[0]} topology [--path DIR]", file=sys.stderr)
        print(f"       python {sys.argv[0]} cw-complex [--path DIR]", file=sys.stderr)
        print(f"       python {sys.argv[0]} cycle-basis [--path DIR]", file=sys.stderr)
        print(f"       python {sys.argv[0]} domain-gaps [--path DIR]", file=sys.stderr)
        print(f"Example: python {sys.argv[0]} academic-literature-review", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd in ("-h", "--help", "help"):
        print(f"Usage: python {sys.argv[0]} <skill-name>")
        print(f"       python {sys.argv[0]} topo [--path DIR]")
        print(f"       python {sys.argv[0]} capability-reach --cap CAPABILITY [--path DIR] [--max-hops 3]")
        print(f"       python {sys.argv[0]} alt-path --from SRC --to DST [--weight tokens|hops]")
        print(f"Example: python {sys.argv[0]} academic-literature-review")
        return
    if cmd == "topo":
        parser = argparse.ArgumentParser(prog="skill-graph-walk.py topo")
        parser.add_argument("--path", dest="skills_path", default=None)
        args = parser.parse_args(sys.argv[2:])
        cmd_topo(args.skills_path)
        return
    if cmd == "capability-reach":
        parser = argparse.ArgumentParser(prog="skill-graph-walk.py capability-reach")
        parser.add_argument("--cap", required=True, help="Controlled-vocabulary capability")
        parser.add_argument("--path", dest="skills_path", default=None)
        parser.add_argument("--max-hops", type=int, default=3)
        args = parser.parse_args(sys.argv[2:])
        cmd_capability_reach(args.cap, args.skills_path, args.max_hops)
        return
    if cmd == "alt-path":
        parser = argparse.ArgumentParser(prog="skill-graph-walk.py alt-path")
        parser.add_argument("--from", dest="src", required=True)
        parser.add_argument("--to", dest="dst", required=True)
        parser.add_argument("--weight", choices=["tokens", "hops"], default="tokens")
        parser.add_argument("--path", dest="skills_path", default=None)
        args = parser.parse_args(sys.argv[2:])
        cmd_alt_path(args.src, args.dst, args.weight, args.skills_path)
        return
    if cmd == "sheaf-check":
        parser = argparse.ArgumentParser(prog="skill-graph-walk.py sheaf-check")
        parser.add_argument("--provides-file", dest="provides_file", default=None)
        args = parser.parse_args(sys.argv[2:])
        cmd_sheaf_check(args.provides_file)
        return
    if cmd == "topology":
        parser = argparse.ArgumentParser(prog="skill-graph-walk.py topology")
        parser.add_argument("--path", dest="skills_path", default=None)
        args = parser.parse_args(sys.argv[2:])
        cmd_topology(args.skills_path)
        return
    if cmd == "cw-complex":
        parser = argparse.ArgumentParser(prog="skill-graph-walk.py cw-complex")
        parser.add_argument("--path", dest="skills_path", default=None)
        args = parser.parse_args(sys.argv[2:])
        cmd_cw_complex(args.skills_path)
        return
    if cmd == "cycle-basis":
        parser = argparse.ArgumentParser(prog="skill-graph-walk.py cycle-basis")
        parser.add_argument("--path", dest="skills_path", default=None)
        args = parser.parse_args(sys.argv[2:])
        cmd_cycle_basis(args.skills_path)
        return
    if cmd == "domain-gaps":
        parser = argparse.ArgumentParser(prog="skill-graph-walk.py domain-gaps")
        parser.add_argument("--path", dest="skills_path", default=None)
        args = parser.parse_args(sys.argv[2:])
        cmd_domain_gaps(args.skills_path)
        return

    target = sys.argv[1]
    graph = load_all_skills()

    if target not in graph:
        # Fuzzy match attempt
        candidates = [k for k in graph if target in k]
        if candidates:
            print(f"Skill '{target}' not found. Did you mean: {', '.join(candidates[:5])}?", file=sys.stderr)
        else:
            print(f"Skill '{target}' not found in {SKILLS_DIR}", file=sys.stderr)
            print(f"Available skills ({len(graph)}): {', '.join(sorted(graph)[:20])} ...", file=sys.stderr)
        sys.exit(1)

    closure = transitive_closure(target, graph)

    print(f"# Transitive closure for: {target}")
    print(f"# Total skills in load order (deps first): {len(closure)}\n")
    for i, name in enumerate(closure, 1):
        info = graph.get(name, {})
        provides = info.get("provides", [])
        deps = info.get("depends_on", [])
        marker = " ← [TARGET]" if name == target else ""
        provides_str = f"  provides: {provides}" if provides else ""
        deps_str = f"  depends_on: {deps}" if deps else ""
        print(f"{i:3}. {name}{marker}{provides_str}{deps_str}")

    print(f"\n# Load this skill set topologically to resolve all prerequisites for '{target}'.")
    print(f"# Graph-walk script: ~/.hermes/scripts/skill-graph-walk.py")


if __name__ == "__main__":
    main()
