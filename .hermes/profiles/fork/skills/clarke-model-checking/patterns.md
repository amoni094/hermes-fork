# Patterns — Model Checking Algorithms

## Pattern: CTL labelling (explicit)

**When:** |S| small and enumerable (exit-code machines, tiny protocols).

**Steps:**
1. Parse φ; list subformulas bottom-up.
2. For each subformula, compute its state set:
   - EX: one-step predecessors.
   - EU: worklist from ψ-states through φ-predecessors (μ).
   - EG: SCCs of the φ-subgraph; keep states that reach a non-trivial SCC (ν).
3. Accept iff S₀ ⊆ [φ].
4. If not, reconstruct a path (safety) or lasso (EG/AF).

**Bound:** O(|S| × |φ|) with adjacency lists, more precisely O((|S|+|R|)·|φ|).

**Done when:** every subformula has a set, and S₀ is decided.

## Pattern: Symbolic CheckSet (BDD)

**When:** next-state is a boolean circuit / SMV ASSIGN.

**Steps:**
1. Encode states as bit-vectors; build BDD(R) partitioned.
2. Reachable = lfp of S₀ ∨ Img(·).
3. CheckSet on reachable BDDs (same μ/ν as labelling).
4. Fair EG: nested fixpoints over fairness BDDs.

**Watch:** variable order; relational product blow-up → BMC or cone-of-influence.

## Pattern: LTL via Büchi product

**When:** path properties, response, GF under fairness.

**Steps:**
1. Build A_{¬φ} (tableau / ltl2ba).
2. Product M × A_{¬φ}.
3. Nested DFS (or SCC): reachable accepting cycle?
4. Yes → lasso cex; no → M ⊦ φ.

**Fairness:** encode justice/compassion as extra acceptance sets (generalized Büchi / Streett).

## Pattern: Safety as reachability

**When:** φ = G ¬bad or AG ¬bad.

**Do not** build a Büchi automaton. BFS/DFS or BDD reachability to bad is enough. Cex is a finite path.

## Pattern: Liveness under fairness

**When:** AF/F/GF failed, or a scheduler can starve a transition.

**Steps:**
1. Classify: justice (almost-always enabled) vs compassion (enabled i.o.).
2. Add constraints; re-check.
3. Remaining cex lasso is a *fair* starvation loop — that is a real bug.

**Hermes:** skill-router GF(query → F return) needs **compassion** on `skill_returned` if `skill_queried` is only i.o. enabled.

## Pattern: Ample-set POR

**When:** asynchronous product, LTL without X, many independent actions.

**At each s during DFS:**
1. Compute a candidate ample ⊆ enabled (typically one process’s local actions).
2. Check C1 (no dependent sneaks in), C2 (invisible if not fully expanded), C3 (cycle closing ⇒ expand).
3. If any fail, fully expand.

**Sibling constructions:** stubborn sets (Valmari), persistent sets (Godefroid). Same intent.

## Pattern: Assume-guarantee split

**When:** product M1 ∥ M2 explodes.

**Steps:**
1. Interface AP only.
2. Check ⟨ψ⟩ M1 ⟨φ⟩ and M2 ⊦ ψ (non-circular).
3. Do not use circular assumptions without a delay/well-founded argument.

## Pattern: Existential abstraction + refine

**When:** data domain too large.

**Steps:**
1. Cone of influence (exact).
2. Merge values (h : S → Ŝ); check ACTL on Ŝ.
3. If cex, try to lift; if not liftable, split the offending abstract state; repeat.

**Never** conclude EF from an existential abstraction.

## Pattern: BMC then prove

**When:** looking for a shallow bug, or BDDs died.

**Steps:**
1. SAT unroll to k=1,2,… until SAT (bug) or budget.
2. To *prove* G p, continue to completeness threshold k* (recurrence diameter / |S| / k-induction — successor technique).
3. Unsat(k) for k < k* is evidence, not a theorem.

## Pattern: Counterexample replay

**Always after “no”:**
1. Safety: step the concrete log/scheduler through the finite path.
2. Liveness: identify the cycle; name the starved action.
3. Decide: model bug vs system bug vs missing fairness.

## Pattern: Engine choice

| Situation | Engine |
|---|---|
| Tiny explicit S | CTL labelling |
| Boolean next-state, AG/AX | SMV BDDs |
| Short suspected bug | SAT BMC |
| Async product, LTL_{-X} | SPIN + POR |
| Nested E inside A | CTL (not LTL) |
| ∀n processes | network invariant, not N=8 SPIN |
