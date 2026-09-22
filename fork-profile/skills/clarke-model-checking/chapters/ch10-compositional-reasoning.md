# Chapter 10: Compositional Reasoning

## Core Idea
Do not build the full product. Prove properties of M1 ∥ M2 from properties of the parts plus assumptions about the environment (assume-guarantee).

## Frameworks Introduced
- **Assume-guarantee**: ⟨ψ⟩ M ⟨φ⟩ — if the environment satisfies ψ, M satisfies φ.
  - When to use: cron job vs SQLite, router vs skill subprocess.
  - How: discharge ⟨ψ⟩ M1 ⟨φ⟩ and ⟨true⟩ M2 ⟨ψ⟩ (or circular rules with care / time-shift).
- **Non-circular AG rule** (sound): if M1 ⊦ (ψ → φ) under env modelled as M2’s interface, and M2 ⊦ ψ, then M1 ∥ M2 ⊦ φ.
- **Circular rules**: need extra hypotheses (e.g. φ depends only on a delayed ψ) — unsound if used naively.

## Key Concepts
- **Interface AP**: only shared propositions appear in ψ.
- **Soundness obligation**: the composition’s R restricted to the interface must refine the assumed environment.
- **Thread of proof**: smaller model checks, not one giant SMV file.

## Mental Models
- Write the *contract* ψ as ACTL on the shared lock/mailbox, check each side.
- Composition is explosion control, not a different logic.

## Anti-patterns
- Circular “each assumes the other is correct” without a well-founded delay.
- Assumptions that mention hidden state of the other component (not on the interface).

## Worked Example
Writer M_w and mutex M_m. Assume AG ¬(grant1 ∧ grant2) of the mutex; prove AG (writer_active → AX ¬concurrent_writer) of the writer in that environment. Then prove the mutex invariant on M_m alone (small).

## Key Takeaways
1. Split product along interfaces.
2. Non-circular AG is the safe default.
3. Assumptions must be checked, not hoped.

## Connects To
- **Ch 2**: product.
- **Ch 11**: abstraction of the environment is a form of assumption.
