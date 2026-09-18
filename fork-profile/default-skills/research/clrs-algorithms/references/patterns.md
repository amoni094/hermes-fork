# CLRS patterns and anti-patterns (4th ed)

## Patterns

**Document the loop invariant (Ch 2.1).** For every non-trivial loop, write initialization, maintenance, and termination. The invariant plus the exit test *is* the proof. Nested loops get nested invariants.

**Model recursion as a recurrence, then Master (Ch 4).** Before profiling a recursive routine, write T(n) = a T(n/b) + f(n) (or a recursion tree). If it is a master recurrence, apply Theorem 4.1. Profiling without an asymptotic model wastes time on the wrong n.

**Amortize sequences, not single ops (Ch 16, 19).** Dynamic arrays, Multipop, binary increment, Fibonacci-heap decrease-key, union-find: quote amortized (or aggregate) cost. A Θ(n) resize does not make vector push Θ(n) per call.

**DP checklist (Ch 14.3).** Optimal substructure (cut-and-paste) + overlapping subproblems → memoize or fill a table. Keep the subproblem index as small as it can be.

**Greedy checklist (Ch 15.2).** Prove greedy-choice (some optimum includes the local choice) and that one subproblem remains. If the proof fails, it is not a greedy problem.

**Pick the SSSP algorithm by edge weights (Ch 22).** Unweighted → BFS. Nonnegative → Dijkstra. Negative allowed → Bellman-Ford (and check the extra pass). Negative cycle reachable from s → no shortest paths.

**Hash only when |K| ≪ |U| (Ch 11).** Direct addressing if the universe is small. Otherwise hash, plan for collisions, and state whether O(1) is expected or worst-case.

## Anti-patterns

- Calling a bound Θ when it is only O, or omitting “worst-case” when best and worst differ (Ch 3.2). Insertion sort is not Θ(n²) in all cases.
- Claiming “O(n log n) beats O(n²)” (Ch 3.2). O is an upper bound; the O(n²) algorithm might be linear.
- Applying Master theorem without polynomial separation (Ch 4.5). f a shade below W is not case 1.
- Dijkstra with a negative edge (Ch 22.3).
- BFS as weighted shortest path (Ch 20.2 vs 22.3).
- Greedy without a greedy-choice proof (Ch 15.2).
- Recursion that looks like DP but has overlapping subproblems and no memo table (Ch 14.3) — exponential blow-up.
- Reviewing `vec.push` / hash resize / union-find Find as O(n) worst-case per call and rejecting the design (Ch 16, 19).
- Testing only the final output of a loop and calling the algorithm verified (Ch 2.1) — the invariant can fail at init or after one iteration and still luck into a good last state on the fixtures.
