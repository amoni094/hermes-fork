---
name: clrs-algorithms
description: "Knowledge base from CLRS Introduction to Algorithms. Use when analyzing algorithm complexity, implementing classic algorithms (sorting, graphs, DP), or studying algorithm correctness proofs."
---

# Introduction to Algorithms (CLRS, 4th ed, 2022)
**Authors**: Cormen, Leiserson, Rivest, Stein | **Pages**: ~1312 | **Chapters**: 35 + appendices A–D

Knowledge base from CLRS *Introduction to Algorithms*. Use when reasoning about algorithmic complexity, data structures, sorting, graph algorithms, dynamic programming, or performance analysis in code.

Synthesized toolkit, not the book text. Cite chapter/section when applying a rule. Load [references/cheatsheet.md](references/cheatsheet.md), [references/patterns.md](references/patterns.md), or [references/glossary.md](references/glossary.md) for lookup; load a chapter file for worked detail.

## How to use

- Complexity / Big-O disputes → Ch 3 + cheatsheet
- Recursion performance → Ch 4 Master theorem (do this *before* profiling)
- Loop correctness → Ch 2.1 loop invariants
- Arrays that grow / heaps / union-find cost → Ch 16 amortized analysis, Ch 19
- Hashing → Ch 11
- DP vs greedy → Ch 14 vs Ch 15
- Graphs: BFS/DFS → Ch 20; Dijkstra/Bellman-Ford → Ch 22

---

## Core frameworks

### Loop invariants (Ch 2.1)

A loop is correct iff you can state a property that holds at the start of every iteration and, with the exit condition, implies the postcondition. Prove three things:

1. **Initialization** — true before the first iteration (base case).
2. **Maintenance** — if true before an iteration, true before the next (inductive step).
3. **Termination** — the loop ends; substituting the exit into the invariant yields a useful correctness claim.

Unlike infinite induction, the “induction” stops when the loop exits. Use this for any non-trivial loop, not as a style comment: the invariant is the correctness argument. Insertion-sort example: at the start of the `for i` loop, `A[1..i-1]` is the original prefix in sorted order; at `i = n+1` the whole array is sorted.

### Asymptotic notation (Ch 3.1–3.2)

- **O(g)** — asymptotic *upper* bound (set of functions).
- **Ω(g)** — asymptotic *lower* bound.
- **Θ(g)** — tight bound: both O and Ω (Theorem 3.1).

Drop lower-order terms and constant coefficients of the leading term. Prefer the tightest true statement: insertion sort is Θ(n²) *worst case* and Θ(n) *best case*; saying “running time is Θ(n²)” (all cases) is an overstatement. O(n²) is always true for it. Do not conflate O with Θ: “an O(n log n) algorithm is faster than an O(n²) algorithm” is false if the O(n²) one is actually Θ(n).

### Master theorem (Ch 4.5, Theorem 4.1)

For T(n) = a T(n/b) + f(n) with a > 0, b > 1 (floors/ceilings ignorable for asymptotics):

Let watershed W = n^{log_b a}.

1. f(n) = O(W / n^ε) for some ε > 0 → T(n) = Θ(W). Leaves dominate.
2. f(n) = Θ(W lg^k n), k ≥ 0 → T(n) = Θ(W lg^{k+1} n). Levels cost about the same. Common: k=0 → Θ(W lg n). Merge sort: a=2, b=2, f=Θ(n) → Θ(n lg n).
3. f(n) = Ω(W · n^ε) *and* regularity a f(n/b) ≤ c f(n) for c < 1 → T(n) = Θ(f(n)). Root dominates.

Cases 1 and 3 need *polynomial* separation from W, not just “a little faster.” If none of the three apply, use substitution (Ch 4.3) or a recursion tree (Ch 4.4), not a hand-waved Big-O.

### Amortized analysis (Ch 16)

A single operation can be Θ(n) while a *sequence* of n operations is O(n). Do not review dynamic arrays, Multipop-style stacks, binary counters, heaps with decrease-key, or union-find by per-operation worst case.

Three equivalent methods (pick the one that matches the structure):

| Method | Idea | Typical use |
|--------|------|-------------|
| **Aggregate** (16.1) | Bound total T(n) for n ops; amortized = T(n)/n (same for every op) | Multipop: each item pushed once, popped once → O(1) amortized |
| **Accounting** (16.2) | Charge extra now, store credit on objects; credit never negative | Push costs 2, pop/multipop cost 0 |
| **Potential** (16.3) | čy_i = c_i + Φ(D_i) − Φ(D_{i-1}); keep Φ ≥ Φ(D_0) | Stack: Φ = size; counter: Φ = number of 1-bits |

**Dynamic tables (16.4):** doubling on insert (load factor ≥ 1/2) gives O(1) amortized insert even though a resize costs Θ(n). Geometric series of copy costs is < 2n. Same idea as Python/Go/Rust/Java array growth.

**Disjoint sets (Ch 19):** union-by-rank + path compression is O(m α(n)) for m operations — α(n) ≤ 4 in practice. Quote amortized, not “each Find is O(n).”

### Dynamic programming (Ch 14.3)

Applies when an optimization problem has **optimal substructure** (an optimal solution contains optimal solutions to subproblems — prove by cut-and-paste) *and* **overlapping subproblems** (a naive recursion recomputes the same subproblems). Two implementations: bottom-up table, or top-down recursion + memoization. Pattern: (1) characterize an optimal choice, (2) assume you are given that choice, (3) name the subproblems, (4) cut-and-paste to prove subsolutions must be optimal. Keep the subproblem space as simple as it can be, then expand.

### Greedy (Ch 15.2)

Greedy is DP with one remaining subproblem after a locally optimal choice. Two ingredients: **greedy-choice property** (a locally best choice is always safe — some optimal solution includes it) and **optimal substructure**. DP usually needs subproblem solutions *before* choosing; greedy chooses first, then solves what remains. If you cannot prove greedy-choice, do not ship a greedy algorithm — fall back to DP or search.

### Hash tables (Ch 11.2–11.4)

When |K| ≪ |U|, hash to m slots: expected O(1) search, not worst-case (direct addressing is worst-case O(1) but uses Θ(|U|) space). Collisions are inevitable (|U| > m). Resolve with chaining or open addressing. Load factor α = n/m governs expected cost. Simple `k mod m` is often a poor h; h must be deterministic. Average-case claims need an input distribution *or* a randomly chosen hash family — say which.

### Graphs (Ch 20, 22)

- Represent as adjacency lists (sparse) or matrix (dense) — Ch 20.1.
- **BFS (20.2):** FIFO queue; white/gray/black; computes unweighted distances and a BFS tree. Archetype for Prim and Dijkstra.
- **DFS (20.3):** parentheses theorem, classification of edges; topological sort (20.4) on DAGs; strongly connected components (20.5).
- **Bellman-Ford (22.1):** |V|−1 rounds of relax-all-edges; then one more pass detects a negative cycle reachable from s. Handles negative weights. O(VE).
- **Dijkstra (22.3):** nonnegative weights only. Generalizes BFS: min-priority queue instead of FIFO. Extract-min + decrease-key. Faster than Bellman-Ford with a heap; wrong if any w < 0.

**Anti-pattern:** Dijkstra on graphs with negative edges; BFS for weighted shortest paths; Floyd-Warshall (Ch 23.2) on huge sparse graphs (use Johnson, 23.3).

---

## Chapter index

| # | Title | Load when |
|---|-------|-----------|
| [ch02](references/ch02-loop-invariants.md) | Getting Started | loop invariants, insertion/merge sort |
| [ch03](references/ch03-asymptotics.md) | Characterizing Running Times | O/Ω/Θ, notation abuse |
| [ch04](references/ch04-divide-conquer.md) | Divide-and-Conquer | recurrences, Master theorem |
| 6–8 | Heapsort, Quicksort, linear-time sort | comparison lower bound Ω(n lg n); counting/radix/bucket |
| 11 | Hash Tables | expected O(1), collisions, open addressing |
| 14 | Dynamic Programming | rod cutting, LCS, optimal BST |
| 15 | Greedy Algorithms | activity selection, Huffman |
| [ch16](references/ch16-amortized.md) | Amortized Analysis | aggregate/accounting/potential, dynamic tables |
| 19 | Disjoint Sets | union-find, α(n) |
| 20 | Elementary Graph Algorithms | BFS, DFS, topo, SCC |
| 22 | Single-Source Shortest Paths | Bellman-Ford, Dijkstra |
| 23 | All-Pairs Shortest Paths | Floyd-Warshall, Johnson |
| 34–35 | NP-Completeness, Approximation | when exact poly-time is unlikely |

## Topic index

- Amortized / dynamic arrays / potential → Ch 16
- Asymptotics O/Ω/Θ → Ch 3
- BFS / DFS / topo / SCC → Ch 20
- Dijkstra / Bellman-Ford / negative cycles → Ch 22
- Divide-and-conquer / Master theorem / recurrences → Ch 4
- Dynamic programming / memoization → Ch 14
- Greedy-choice / Huffman → Ch 15
- Hash tables / open addressing → Ch 11
- Heaps / priority queues → Ch 6
- Loop invariants → Ch 2.1
- Sorting lower bound / radix / counting → Ch 8
- Union-find → Ch 19

## Supporting files

- [references/glossary.md](references/glossary.md)
- [references/patterns.md](references/patterns.md)
- [references/cheatsheet.md](references/cheatsheet.md)

## Scope

CLRS 4th edition only. Pseudocode is 1-indexed; translate carefully. Does not replace language-specific coding conventions or a profiler for constants — it tells you the *order of growth* and the *correctness argument* before you measure.
