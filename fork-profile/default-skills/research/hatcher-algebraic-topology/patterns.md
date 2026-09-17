# Patterns: Applying Algebraic Topology (Hatcher)

## Pattern 1: Detecting Holes via Homology

**Trigger**: You need to find "missing connections" or "gaps" in a graph/network.

**Framework**: Model the graph as a 1-dimensional simplicial complex.
- H₀ = free abelian on connected components (rank = # components)
- H₁ = free abelian on independent cycles (rank = # independent loops)

**Algorithm**:
```python
import networkx as nx

def compute_graph_homology(G):
    """
    H₀ rank = number of connected components
    H₁ rank = E - V + C (where C = # connected components)
    This follows from the Euler characteristic: χ = V - E = C - rank(H₁)
    """
    V = G.number_of_nodes()
    E = G.number_of_edges()
    C = nx.number_connected_components(G)
    h0_rank = C                    # H₀(G) ≅ ℤ^C
    h1_rank = E - V + C            # H₁(G) by Euler-Poincaré
    return {"H0": h0_rank, "H1": h1_rank, "euler_char": V - E}
```

**Interpretation**:
- H₁ rank = 0: graph is a forest (tree per component), no loops/holes
- H₁ rank = k: k independent "holes" / redundant edges
- For skill graph: H₁ > 0 means circular skill dependencies exist

**Limitations**: Only works for 1-dim complexes (graphs). For detecting
2-dimensional gaps (missing skill clusters), need 2-simplices (triangles).

---

## Pattern 2: Euler Characteristic as Graph Audit

**Trigger**: Quick structural audit of a graph/network.

**Framework**: χ = V - E + F for a planar graph (F = faces including outer).
For general CW complex: χ = Σ(-1)ⁿ cₙ = Σ(-1)ⁿ bₙ.

**Algorithm**:
```python
def euler_characteristic_audit(skills, dependencies, clusters):
    """
    skills = list of skill nodes (0-cells)
    dependencies = list of (s1, s2) edges (1-cells)
    clusters = list of (s1, s2, s3) triangles of mutually related skills (2-cells)
    """
    V = len(skills)
    E = len(dependencies)
    F = len(clusters)
    chi = V - E + F
    # For a connected graph (no 2-cells): chi = 1 - h1_rank (tree if chi=1)
    # For closed orientable surface of genus g: chi = 2 - 2g
    return {
        "vertices": V, "edges": E, "faces": F,
        "euler_char": chi,
        "interpretation": "forest-like" if chi > 0 else "has cycles" if chi == 0 else "complex topology"
    }
```

**Hermes application**: Run on skill graph monthly. χ decreasing → skills becoming more interconnected. χ increasing → skills becoming siloed.

---

## Pattern 3: Fundamental Group for Dependency Cycle Detection

**Trigger**: Check for circular dependencies in skill invocation graph.

**Framework**: π₁ of a directed graph detects cycles. For an undirected graph,
π₁ is free on (E - V + C) generators.

**Algorithm**:
```python
import networkx as nx

def find_dependency_cycles(skill_graph):
    """
    Uses the fact that π₁ of a graph is free of rank = E - V + C.
    Generators of π₁ = independent cycles = spanning tree complement edges.
    """
    cycles = list(nx.simple_cycles(skill_graph))
    spanning_tree = nx.minimum_spanning_tree(skill_graph.to_undirected())
    non_tree_edges = [e for e in skill_graph.edges() 
                     if not spanning_tree.has_edge(*e)]
    # Each non-tree edge determines a generator of π₁
    # Each simple cycle is a word in these generators
    return {
        "pi1_rank": len(non_tree_edges),
        "cycle_generators": non_tree_edges,
        "all_cycles": cycles
    }
```

**Covering space interpretation**: The universal cover of the skill graph
is the infinite tree of all dependency paths (no cycles). The fundamental
group encodes all ways to return to a starting skill.

---

## Pattern 4: Homotopy Equivalence for Skill Deduplication

**Trigger**: Determine if two skills are functionally redundant.

**Framework**: Two spaces X≃Y (homotopy equivalent) have identical algebraic
invariants (homology, homotopy groups). For skills: if two skills have the
same "shape" of inputs→outputs, they are homotopy equivalent.

**Practical criteria** (conservative):
1. Same trigger conditions (same "attractor basin" in skill space)
2. Same tool calls (same "homotopy type" of execution path)
3. Outputs compose to identity (fg≃id, gf≃id)

**Algorithm** (approximation):
```python
def skill_similarity_matrix(skills):
    """
    Approximate homotopy equivalence via:
    - Jaccard similarity on trigger keywords
    - Jaccard similarity on tool sets
    - Output schema overlap
    Two skills are "homotopy equivalent" if similarity > threshold
    """
    from itertools import combinations
    pairs = []
    for s1, s2 in combinations(skills, 2):
        trigger_sim = jaccard(s1.triggers, s2.triggers)
        tool_sim = jaccard(s1.tool_calls, s2.tool_calls)
        combined = 0.5 * trigger_sim + 0.5 * tool_sim
        if combined > 0.8:  # threshold
            pairs.append((s1.name, s2.name, combined))
    return pairs
```

**Limitation**: True homotopy equivalence is undecidable in general. Use as
approximation only. Mark pairs for human review.

---

## Pattern 5: Mayer-Vietoris for Decomposed Graph Analysis

**Trigger**: Graph is naturally divided into two overlapping subgraphs A and B.

**Framework**: If X = A∪B, then homology satisfies:
→H₁(A∩B) → H₁(A)⊕H₁(B) → H₁(X) → H₀(A∩B) → H₀(A)⊕H₀(B) → H₀(X) → 0

**Hermes application**: Split skill graph into two categories (e.g., devops vs research).
Compute:
- H₁(devops) = independent cycles within devops skills
- H₁(research) = independent cycles within research skills  
- H₁(devops∩research) = cycles in bridging skills
- H₁(all) via Mayer-Vietoris LES (can detect cross-category holes)

**Algorithm**:
```python
def mayer_vietoris_analysis(G, A_nodes, B_nodes):
    A = G.subgraph(A_nodes)
    B = G.subgraph(B_nodes)
    AB = G.subgraph(set(A_nodes) & set(B_nodes))
    
    def h01(g):
        V, E, C = g.number_of_nodes(), g.number_of_edges(), nx.number_connected_components(g)
        return C, E - V + C  # H0 rank, H1 rank
    
    h0_A, h1_A = h01(A)
    h0_B, h1_B = h01(B)
    h0_AB, h1_AB = h01(AB)
    # Full homology via LES (simplified: rank computation)
    # Long exact sequence gives H₁(X) from components above
    return {"H1_A": h1_A, "H1_B": h1_B, "H1_A∩B": h1_AB}
```

---

## Pattern 6: Van Kampen for Skill Dependency Decomposition

**Trigger**: Compute π₁ of skill graph from subgraph decompositions.

**Framework**: π₁(A∪B) = π₁(A) ∗_{π₁(A∩B)} π₁(B) when A∩B is connected.

**Interpretation**: The "fundamental group" of the skill dependency graph encodes
all ways to traverse skill dependencies in a loop. Independent cycle generators
correspond to distinct circular dependency patterns.

For a graph: π₁ is always free. The presentation has:
- Generators = non-tree edges (one per independent cycle)
- Relations = none (free group)

Split by van Kampen: π₁(G) = π₁(G[A]) ∗_{π₁(G[A∩B])} π₁(G[B])

**Use**: When skill graph grows, van Kampen lets you update π₁ incrementally
by adding one subgraph at a time, without recomputing from scratch.

---

## Anti-Patterns

**Don't use**: Persistent homology (requires gudhi/ripser, not installed).
→ Use static graph homology instead (networkx + manual computation).

**Don't use**: Spectral sequences for Hermes skill analysis (too complex, no clear benefit).
→ Mayer-Vietoris is sufficient for decomposition analysis.

**Don't use**: Higher homotopy groups πₙ (n≥2) for skill graphs.
→ Skill graphs are at most 2-dimensional. π₁ suffices.

**Careful**: Poincaré duality requires closed orientable manifolds.
→ Skill graphs are not manifolds. Duality doesn't apply directly.
