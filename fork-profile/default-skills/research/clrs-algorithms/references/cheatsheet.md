# CLRS cheatsheet (4th ed)

## Asymptotics (Ch 3)

| Notation | Means |
|----------|--------|
| f = O(g) | f grows no faster than g (upper) |
| f = Ω(g) | f grows at least as fast as g (lower) |
| f = Θ(g) | both: tight bound (Thm 3.1) |

Drop lower-order terms and leading constants. State *which case* (best/worst/all). Do not use O when you mean Θ.

Common: lg n = log₂ n. Base of log does not change Θ.

## Master theorem (Ch 4.5, Thm 4.1)

T(n) = a T(n/b) + f(n), W = n^{log_b a}

1. f = O(W / n^ε) → T = Θ(W)
2. f = Θ(W lg^k n) → T = Θ(W lg^{k+1} n)
3. f = Ω(W n^ε) and a f(n/b) ≤ c f(n), c<1 → T = Θ(f)

Merge sort: 2T(n/2)+Θ(n) → Θ(n lg n). Strassen: 7T(n/2)+Θ(n²) → Θ(n^{lg 7}).

## Loop invariants (Ch 2.1)

Initialization → Maintenance → Termination. Termination + exit condition = postcondition.

## Sorting (Ch 6–8)

| Algorithm | Worst | Average | Extra space | Notes |
|-----------|-------|---------|-------------|-------|
| Insertion | Θ(n²) | Θ(n²) | O(1) | Θ(n) already-sorted |
| Merge | Θ(n lg n) | Θ(n lg n) | Θ(n) | stable |
| Heap | Θ(n lg n) | Θ(n lg n) | O(1) | priority queues Ch 6.5 |
| Quick (rand) | Θ(n²) | Θ(n lg n) | O(lg n) | expected |
| Counting/radix | Θ(n+k) / Θ(d(n+k)) | same | Θ(n+k) | not comparison sorts |

Comparison sorts: Ω(n lg n) in worst case (Ch 8.1).

## Hashing (Ch 11)

Expected O(1) search at load α = n/m. Collisions required. Chaining vs open addressing. Direct address: worst-case O(1), space Θ(|U|).

## Amortized (Ch 16)

Dynamic table doubling: O(1) amortized insert. Multipop stack: O(1) amortized. Binary counter increment: O(1) amortized. Union-find + rank + path compression: O(m α(n)) (Ch 19).

## Graphs (Ch 20, 22)

| Problem | Algorithm | Constraint | Time |
|---------|-----------|------------|------|
| Unweighted dist | BFS | — | Θ(V+E) |
| Topo / SCC | DFS | directed | Θ(V+E) |
| SSSP nonnegative | Dijkstra | w ≥ 0 | depends on heap |
| SSSP general | Bellman-Ford | detect neg cycle | O(VE) |
| APSP dense | Floyd-Warshall | — | Θ(V³) |
| MST | Kruskal / Prim | undirected | nearly O(E lg V) |

## DP vs greedy (Ch 14–15)

Need overlapping subproblems + optimal substructure → DP. Greedy-choice + one leftover subproblem → greedy. Cannot prove greedy-choice → do not ship greedy.
