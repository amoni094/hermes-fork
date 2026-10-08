# Chapter 4: Model Checking

## Core Idea
Explicit-state CTL model checking labels each state with the subformulas it satisfies, bottom-up. Time is linear: O(|S| × |φ|) (CES 1986; with adjacency lists O((|S|+|R|)·|φ|)).

## Frameworks Introduced
- **Labelling algorithm**:
  1. Label p at {s | p ∈ L(s)}.
  2. Boolean connectives from already-labelled sets.
  3. EX ψ: predecessors of the ψ-set.
  4. E[φ U ψ] = μZ. ψ ∨ (φ ∧ EX Z) — start at ψ-states, close under φ-predecessors.
  5. EG φ = νZ. φ ∧ EX Z — in the subgraph of φ-states, keep states that lie on a cycle (or can reach a cycle, given totality).
  - When to use: |S| enumerable (exit-code machines, small protocols).
  - How: worklist / DFS-SCC; do not recompute EX from scratch each round — use a count of labelled successors for EG.
- **Fair CTL**: interpret E/A over paths that satisfy given fairness constraints (infinitely often each justice set). EG^fair φ uses fair SCCs: an SCC is fair if it intersects every fairness set.
- **Counterexample extraction**:
  - AG p false: BFS/DFS from S₀ to a ¬p state.
  - AF p false: a reachable cycle in ¬p (lasso).
  - EG p true: a lasso inside p as a *witness*.

## Key Concepts
- **Subformula closure**: process |φ| nodes of the formula DAG.
- **Least vs greatest fixpoint**: EU is inductive reachability; EG is “can stay forever”.
- **Complexity**: linear in |S|·|φ| for CTL; fair CTL remains linear in the graph per subformula via Tarjan SCCs.
- **CTL* / LTL**: not this algorithm — exponential in |φ| (Ch 7).

## Mental Models
- Think **graph reachability** for EU/EF, **cycle finding** for EG/AF-failure.
- If labelling |S₀| ⊆ [φ], the property holds; else the first unlabelled initial state is the seed of a counterexample.

## Anti-patterns
- Computing EG as “all φ-states” without a cycle check (dead-end φ-states are not EG).
- Quoting O(|S|×|φ|) while using an adjacency *matrix* without noting |R|.
- Using CTL labelling on an LTL formula that is not in CTL.

## Worked Example
Exit-code machine: S = {run, ok, fail, intentional, crash}. AP: exit0, intentional. Target AG (exit0 ∨ intentional). Label atoms; AG φ = ¬EF ¬φ. EF ¬φ is reachability of {fail, crash}. If crash is unreachable from S₀, all initial states get AG.

## Key Takeaways
1. Bottom-up labels; fixpoints for EU/EG.
2. Bound: O(|S| × |φ|).
3. Fairness changes the *paths*, not the syntax — fair SCCs.
4. Always return a path when no.

## Connects To
- **Ch 6**: same fixpoints on BDDs.
- **Ch 7**: LTL needs automata, not this labelling.
- **Cheatsheet**: exit-code AG.
