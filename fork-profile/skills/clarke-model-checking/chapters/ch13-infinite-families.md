# Chapter 13: Infinite Families of Finite-State Systems

## Core Idea
A parameterized system M(n) (n identical processes) is an *infinite family* of finite Kripke structures. Model checking a single n does not prove ∀n. Invariants that hold for all n need induction, network invariants, or other parameterized methods.

## Frameworks Introduced
- **Network invariant** I: M(1) ≼ I and I ∥ P ≼ I (P a process). Then ∀n. M(n) ≼ I. ACTL on I lifts to every size.
  - When to use: N cron workers, N router children.
  - How: guess I (often M(k) for small k or an abstract environment); check the two simulations.
- **Induction on n**: prove φ(1) by ordinary MC; prove φ(n) ⇒ φ(n+1) by a finite MC on a composition with an abstract “other n”.
- **Cutoff results**: some properties have a finite n₀ such that M(n₀) ⊦ φ ⇒ ∀n. M(n) ⊦ φ (not always; do not assume a cutoff).

## Key Concepts
- **Undecidability**: many parameterized problems are undecidable (Apt/Kozen). Completeness is not promised.
- **Regularity**: token rings, linear arrays sometimes admit automata-theoretic invariants.
- **Symmetry (Ch 12)** is for *fixed* n; this chapter is for *all* n.

## Mental Models
- Checking n=3 is a test, not a parameterized proof.
- If you need ∀n, you are doing compositional/abstract MC, not “run SPIN with N=10”.

## Anti-patterns
- “Works for n=8, ship it” as AG ∀n.
- Using symmetry quotient and claiming parameterized correctness.

## Worked Example
Skill-router with n workers. Network invariant I = “at most one owner of the posterior-update lock”. Check I ∥ worker ≼ I. Then GF(skill_queried → F skill_returned) still needs fairness *inside* I; parameterization does not replace compassion.

## Key Takeaways
1. Family ≠ instance.
2. Network invariants + simulation are the book’s method.
3. Parameterized MC is often undecidable; fail closed.

## Connects To
- **Ch 10**: composition.
- **Ch 12**: fixed-n symmetry.
