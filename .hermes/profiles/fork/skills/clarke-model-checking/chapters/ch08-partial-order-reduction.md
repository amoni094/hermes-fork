# Chapter 8: Partial Order Reduction

## Core Idea
Independent concurrent actions generate equivalent interleavings. Explore only an ample (stubborn, persistent) subset of enabled(s) so that every Mazurkiewicz trace still has a representative, preserving stutter-invariant LTL (and, with extra care, CTL).

## Frameworks Introduced
- **Independence relation I**: α I β (symmetric, irreflexive) iff in every state where both are enabled they commute (αβ and βα same state) and neither disables the other.
  - When to use: local assignments, disjoint file writes, independent cron jobs.
- **Ample sets** (Peled) — conditions on ample(s) ⊆ enabled(s):
  - **C0**: ample(s)=∅ iff enabled(s)=∅.
  - **C1** (persistent / no ignored dependent): along any path, a transition dependent on some α ∈ ample(s) cannot occur before a member of ample(s).
  - **C2** (invisibility): if ample(s) ≠ enabled(s) (a *non-expanded* state), every α ∈ ample(s) is invisible — it does not change L(s) for atoms in φ.
  - **C3** (cycle / ignoring): every cycle in the reduced graph contains a fully expanded state (or, equivalently, an ample transition of each ignored action is taken on the cycle).
- **Stubborn sets** (Valmari): a set T that is closed under “must-fire-before” dependencies; similar guarantees, different static analysis.
- **Persistent sets** (Godefroid): a set whose members cannot be disabled by actions outside the set.

## Key Concepts
- **Visible vs invisible**: visibility is relative to φ; shrinking AP improves reduction.
- **Full expansion**: ample(s)=enabled(s); always legal; use when C1–C3 fail.
- **On-the-fly**: compute ample during DFS (SPIN); do not build the full graph first.
- **CTL POR**: needs extra conditions (no ignoring of branches); reduction is typically weaker than for LTL without X.

## Mental Models
- POR is **trace theory**, not heuristic skipping. If C1–C3 hold, LTL_{-X} is preserved.
- Prefer making actions invisible (keep AP observational) over weakening independence.

## Anti-patterns
- Ample-set of a *visible* lock take while leaving the other process’s lock take out — C2 fails, you can miss races.
- Forgetting C3: a cycle of only invisible local steps can ignore a dependent action forever (liveness bugs vanish).
- Using POR on formulas with X.

## Worked Example
Two cron jobs writing disjoint logs. enabled = {w1, w2}. w1 I w2, both invisible to AG ¬(writer_db1 ∧ writer_db2) if that property only watches the DB mutex. ample(s)={w1} is legal at states where C3 will expand on the cycle. SPIN-style: DFS, if a back-edge would close a cycle without expansion, expand fully.

## Key Takeaways
1. Independence + invisibility + cycle condition.
2. Ample / stubborn / persistent are sibling constructions.
3. SPIN is the tool; Promela processes are the local machines.
4. No X in the formula.

## Connects To
- **Ch 2**: product interleavings.
- **Ch 7**: LTL_{-X}.
- **Ch 16**: SPIN.
