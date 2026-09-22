# Chapter 5: Binary Decision Diagrams

## Core Idea
Ordered BDDs (Bryant) represent boolean functions canonically. Sets of states and the transition relation become diagrams; equality of functions is pointer equality after reduction.

## Frameworks Introduced
- **OBDD**: Shannon expansion f = ¬x f|_{x=0} ∨ x f|_{x=1} with a fixed variable order x₁ ≺ … ≺ x_n; isomorphic subgraphs merged; no redundant tests (both children equal ⇒ delete).
  - When to use: symbolic image computation, hardware-like next-state functions.
  - How: unique table + ITE apply; never build a truth table.
- **Apply / ITE**: ITE(i,t,e) = i∧t ∨ ¬i∧e implements ∧,∨,¬,∃.
- **Variable order**: good order (interleave current/next, cluster dependent vars) can be linear size; bad order exponential. Dynamic reordering is heuristic, not a guarantee.

## Key Concepts
- **Canonicity**: reduced OBDDs for f and g are identical iff f ≡ g.
- **Quantification**: ∃x f = f|_{x=0} ∨ f|_{x=1} — cost can explode (relational product).
- **Partitioned transition relation**: R = ∧_i R_i; quantify early (and-exists) to keep peaks down.
- **Complement edges / typed BDDs**: implementation tricks in SMV/CUDD, not required for the math.

## Mental Models
- Use BDDs when the **set** of reachable states is huge but **structured**.
- Treat variable order as part of the model, not a tuner you ignore.
- Relational product ∃s. Z(s) ∧ R(s,s') is the operation that usually dies first.

## Anti-patterns
- Current-state variables all before next-state (or the reverse) as a default order.
- Building R as one monolithic BDD when conjunctive partitioning exists.
- Assuming BDD MC is always faster than explicit — random software R is often a worst case.

## Worked Example
Two-bit counter: vars x0,x1, x0',x1'. R: x0' = ¬x0, x1' = x0 ⊕ x1. Order x0 ≺ x0' ≺ x1 ≺ x1' keeps the diagram tiny. Reachable set from 00 is all four states after three images — computed without enumerating paths.

## Key Takeaways
1. Reduced OBDDs are canonical.
2. Image = relational product; that is the bottleneck.
3. Order and partitioning dominate |S|.
4. SMV's engine is this chapter plus Ch 6 fixpoints.

## Connects To
- **Ch 6**: CheckSet on BDDs.
- **Ch 16**: SAT BMC as the alternative when BDDs blow up.
