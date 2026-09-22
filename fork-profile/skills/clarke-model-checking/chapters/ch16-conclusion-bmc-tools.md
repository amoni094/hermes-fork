# Chapter 16: Conclusion, Tools, BMC, Counterexamples

## Core Idea
The 1999 book closes on industrial model checking: SMV for symbolic CTL, SPIN for explicit LTL+POR, counterexamples as the debugging interface. SAT-based bounded model checking (Biere, Cimatti, Clarke, Zhu, TACAS 1999) is the contemporaneous Clarke-lineage method for shallow bugs.

## Frameworks Introduced
- **SMV** (McMillan): synchronous modules, OBDDs, CTL SPEC, FAIRNESS. Later NuSMV/nuXmv add SAT BMC.
  - When to use: hardware-like next-state, WAL lock boolean models, AG/AX.
- **SPIN** (Holzmann): Promela processes, LTL never-claims, nested DFS, POR.
  - When to use: asynchronous interleaving, protocols, cron job products.
- **Counterexample + guided simulation**:
  - Safety: finite path; replay as a script.
  - Liveness: lasso; the cycle is the starvation loop.
  - When to use: every “no”; never discard the trace.
- **Bounded model checking (SAT)** — Clarke lineage, not a 1999 chapter:
  Unroll: I(s₀) ∧ R(s₀,s₁) ∧ … ∧ R(s_{k-1},s_k) ∧ (∨_{i≤k} ¬p(s_i)) for safety.
  Completeness threshold k*: if unsat for all depths ≤ k* (e.g. recurrence diameter, or |S|), then G p holds.
  - When to use: hunt a short violation; BDDs failed; SAT is cheap.
  - How: increment k; stop at bug or threshold. Unsat at k ≪ k* is *not* a proof.

## Key Concepts
- **Recurrence diameter**: longest loop-free path; a completeness bound for simple safety.
- **Induction / k-induction** (later): BMC + inductive step; mentioned only as successor technique.
- **Industrial lesson**: modelling effort dominates; keep AP observational; iterate model↔cex.

## Mental Models
- BMC is a microscope; BDD/labelling is a proof.
- Tools do not remove the need to write M and φ well.

## Anti-patterns
- BMC unsat(k=20) shipped as AG.
- Running SPIN without POR on a highly independent product.
- Pretty-printing a cex without replaying it on the real log.

## Worked Example
Cron WAL: BMC k=8 finds a trace where two writers overlap if the lock is forgotten — SAT witness is the guided simulation. After the lock is added, BDD AG (writer_active → AX ¬concurrent_writer) on the SMV model is the proof; BMC alone at k=8 would be insufficient.

## Key Takeaways
1. SMV = symbolic CTL; SPIN = explicit LTL+POR.
2. Counterexamples are part of the method.
3. BMC needs a completeness threshold to prove.
4. Explosion mitigations (Ch 8–13) are how the method scales.

## Connects To
- **Ch 4–8**: engines behind the tools.
- **Cheatsheet**: Hermes recipes.
