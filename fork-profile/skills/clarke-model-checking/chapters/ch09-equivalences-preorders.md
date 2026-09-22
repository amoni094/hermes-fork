# Chapter 9: Equivalences and Preorders between Structures

## Core Idea
Bisimulation equivalence preserves all CTL* (hence CTL and LTL). Simulation preorder preserves ACTL. Quotient by the largest bisimulation to shrink S before checking.

## Frameworks Introduced
- **Bisimulation ~**: relation B ⊆ S×S' such that related states have the same L, and every transition is matched in both directions.
  - When to use: replace M by M/~ ; check φ on the quotient.
  - How: partition refinement (Paige–Tarjan / Kanellakis–Smolka); stable blocks.
- **Simulation ≼**: one-direction matching. If M ≼ M' and M' ⊦ ψ for ACTL ψ, then M ⊦ ψ.
  - When to use: over-approximate implementations by specs; abstract models (Ch 11).
- **Trace equivalence**: same linear traces; preserves LTL, not CTL (branching lost).

## Key Concepts
- **Logical characterization**: s ~ t iff they satisfy the same CTL* formulas.
- **Stuttering bisimulation**: matches finite stuttering; preserves CTL* without X.
- **Preorder vs equivalence**: simulation can prove universal properties of an implementation via a smaller spec; it cannot disprove them without a matching counterexample in both.

## Mental Models
- Minimize first, then check — if ~ is cheap.
- If you only have AG/AX (ACTL), a simulating abstraction that satisfies φ is a proof; one that fails φ may be spurious.

## Anti-patterns
- Using trace quotient and then checking AG EF p (branching).
- Claiming bisimulation of *fair* structures without matching fairness constraints.

## Worked Example
Exit-code machine: fail and crash may be bisimilar if both label ¬exit0 ∧ ¬intentional and have the same self-loop. Merge them; AG (exit0 ∨ intentional) is unchanged.

## Key Takeaways
1. Bisimulation ⇔ CTL* equivalence.
2. Simulation ⇔ ACTL preservation one way.
3. Quotient before labelling when |S| is symmetry-free but redundant.

## Connects To
- **Ch 11**: existential abstraction is a simulation from concrete to abstract.
- **Ch 12**: symmetry is a special bisimulation (group action).
