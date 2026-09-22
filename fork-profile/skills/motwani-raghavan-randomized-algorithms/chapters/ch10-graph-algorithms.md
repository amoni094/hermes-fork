# Ch 10 — Graph Algorithms

## All-pairs shortest paths (Ch 10.1)

Randomised reductions (Frobenius / Seidel-style) and sampling of bridges. A random perturbation of edge weights makes the shortest-path DAG unique w.h.p. (isolation; cf. Ch 12 Isolating Lemma), enabling parallel / algebraic methods.

## Min-cut (Ch 10.2)

Implementation of Ch 1.1 contractions. Data structure: adjacency lists / union-find-like contraction. Recursive contraction (Karger–Stein, 1993/1996): contract down to `n/√2` vertices, recurse twice; success probability `Ω(1/log n)` per trial, faster than `n²` independent full contractions.

Near-linear expected time for a min-cut Monte Carlo algorithm; still simpler than flow.

## Minimum spanning trees (Ch 10.3)

Karger–Klein–Tarjan randomised MST: randomly sample edges, recurse on a contracted graph of F-heavy edges. Expected linear time. (Deterministic linear-time MST was open in 1995; still uses randomness in the fastest known algorithms.)

## Hermes

- Graph cuts on a skill/dependency graph: contraction Monte Carlo + amplify, not max-flow, when an approximate or high-probability min-cut is enough.
- Unique shortest path: isolate with random weights rather than lexicographic tie-breaks.
