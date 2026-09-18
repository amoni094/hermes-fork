# Chapter 22: Invariant Measures

## Core Idea
On compact topological groups and dynamical systems, invariant measures exist by fixed-point arguments (Kakutani's fixed-point theorem). Haar measure (unique group-invariant probability measure) exists on every compact group. Ergodic measures exist for any continuous map on a compact metric space.

## Key Concepts
- **Compact topological group**: Group G with compact Hausdorff topology and continuous group operations (multiplication, inversion). Examples: circle group S¹, SO(n), finite groups, products of compact groups.
- **Haar measure**: Borel probability measure μ on G with μ(gE) = μ(E) for all g∈G and Borel E (left-invariance). Also right-invariant for compact groups. Unique (up to scalar).
- **T-invariant measure**: μ on (X,B) with μ(T⁻¹E) = μ(E) for all Borel E. Equivalently, ∫f∘T dμ = ∫f dμ.
- **Ergodic measure**: T-invariant μ with the property: T⁻¹E = E ⟹ μ(E) ∈ {0,1}. No "nontrivial" T-invariant subsets.

## Key Theorems

### Kakutani's Fixed-Point Theorem (§22.2)
**Statement**: Let C be a compact convex subset of a locally convex topological vector space. If T: C→2^C is upper semicontinuous with nonempty compact convex values T(x), then T has a fixed point: ∃x*∈C with x*∈T(x*).

- **Use when**: Proving existence of invariant measures, equilibria in game theory.
- **Proof strategy**: In the measure-space setting, use weak-* compactness of probability measures (Alaoglu) and convexity of the space of invariant measures.

### Von Neumann's Theorem — Haar Measure (§22.3)
**Statement**: Every compact topological group G has a unique (up to scalar) left-invariant Borel probability measure μ (Haar measure): μ(gE) = μ(E) for all g∈G and Borel E.

- **Proof**: Apply Kakutani to the compact convex set of probability measures on G, acted on by the group.
- **Consequence**: ∫_G f(gx) dμ(x) = ∫_G f(x) dμ(x) for all g — Haar measure is the "uniform distribution" invariant under group translations.

### Bogoliubov-Krylov Theorem — Existence of Invariant Measures (§22.4)
**Statement**: If T: X→X is a continuous map on a compact metric space X, then ∃ a Borel probability measure μ with T*μ = μ (T-invariant).

- **Proof**: Start from any probability measure ν. The Cesàro averages μₙ = (1/n)Σ_{k=0}^{n-1} T^k_* ν form a tight sequence. Extract weakly convergent subsequence μₙₖ → μ. Then μ is T-invariant.
- **Hermes**: Every continuous routing map on a compact context space has an invariant measure — a "stable routing distribution" that the system naturally converges to over repeated use.

### Ergodic Theorem (implied)
For ergodic μ, time averages = space averages: (1/n)Σ_{k=0}^{n-1} f(Tᵏx) → ∫f dμ for μ-a.e. x. Ergodic measures are the "extremal" invariant measures (cannot be decomposed as convex combinations).

## Key Takeaways
1. Haar measure: every compact group has a canonical uniform distribution. Symmetry gives you a free measure.
2. Bogoliubov-Krylov: existence of invariant measures for any continuous map on compact space — no special structure needed beyond continuity and compactness.
3. Ergodic measures = indecomposable invariant measures. Every invariant measure = integral (mixture) of ergodic measures.
4. The Cesàro average construction is the bridge: empirical averages of pushed-forward measures converge weakly to an invariant measure.

## Connects To
- **Ch15**: Alaoglu and Kakutani theorems from Ch15 are the key technical tools here
- **Ch21**: Radon measures on compact spaces; Riesz-Markov provides the setting
- **Ch17-18**: General measure theory infrastructure
