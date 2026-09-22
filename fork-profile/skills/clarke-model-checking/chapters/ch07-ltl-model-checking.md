# Chapter 7: LTL Model Checking

## Core Idea
LTL is checked by translating ¬φ to a Büchi automaton, forming the product with M, and testing emptiness of the language of fair (accepting) infinite runs. Safety is “bad state unreachable”; liveness needs fairness.

## Frameworks Introduced
- **Automata-theoretic MC** (Vardi/Wolper): M ⊦ φ iff L(M) ∩ L(A_{¬φ}) = ∅.
  - When to use: path properties, response, persistence, fairness-constrained runs.
  - How: tableau or LTL→Büchi; product; nested DFS (or SCC) for an accepting cycle reachable from S₀.
- **Safety vs liveness** (Alpern/Schneider, used throughout):
  - Safety: every violating trace has a *finite bad prefix*. Form: G ¬bad (invariants).
  - Liveness: every finite prefix can be extended to satisfaction. Form: F good, G(req → F ack).
- **Fairness**:
  - **Weak fairness / justice**: FG enabled(t) → GF taken(t), equivalently GF(¬en(t) ∨ taken(t)).
  - **Strong fairness / compassion**: GF enabled(t) → GF taken(t), equivalently FG ¬en(t) ∨ GF taken(t).
  - When to use: any AF/F/GF claim on a scheduler that *may* starve a process.
  - How: add fairness sets to the Büchi acceptance (generalized Büchi / Streett).

## Key Concepts
- **Büchi acceptance**: Inf(π) ∩ F ≠ ∅ — some accept state infinitely often.
- **Lasso counterexample**: stem + cycle; the cycle is the “unfair” or “never good” loop.
- **Complexity**: LTL MC is PSPACE-complete in |φ|; for fixed φ, polynomial in |M|. Tableau |A_φ| is exponential in |φ| worst case.
- **Stutter invariance**: LTL without X is preserved by finite stuttering — required for POR (Ch 8).

## Mental Models
- If AG/G holds with explicit labelling, you do not need Büchi.
- If AF fails, first ask: *is there an unfair scheduler that starves the good event?* Add justice/compassion before changing code.
- Strong fairness is the right default for “if requested infinitely often, eventually served” under a mutex (skill router beta posteriors).

## Anti-patterns
- Proving liveness on a model that allows a process to be ignored forever.
- Using weak fairness when the transition is only *occasionally* enabled (need compassion).
- Treating nested-DFS “no cycle” as a safety proof of G ¬bad — use reachability for safety; it is cheaper.

## Worked Example
Atomic write: I/O automaton with actions begin_write, commit, abort. Visible states never contain a torn page. LTL safety: G ¬partial_write_visible. Violation is a finite prefix ending in a reader-observed torn page — no fairness involved.

Gate-audit liveness: AF calibration_data_available. Holds iff every path eventually runs the sweep. A self-loop at cold-start with sweep never scheduled is the lasso; adding justice “if sweep_enabled then taken i.o.” makes the property the scheduler’s obligation.

## Key Takeaways
1. LTL MC = product emptiness with A_{¬φ}.
2. G ¬bad is reachability; F/G mixtures need cycles.
3. Justice vs compassion is a modelling choice that changes truth.
4. Counterexamples are lassos; replay them.

## Connects To
- **Ch 3**: LTL syntax.
- **Ch 8**: POR on stutter-invariant LTL.
- **Cheatsheet**: atomic write, gate-audit, skill-router GF.
