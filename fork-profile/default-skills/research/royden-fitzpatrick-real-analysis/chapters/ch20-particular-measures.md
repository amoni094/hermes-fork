# Chapters 20–22: Particular Measures, Measure-Topology, Invariant Measures

## Ch20 Core Idea: Constructing Specific Measures
Fubini-Tonelli (product measures), Lebesgue measure on ℝⁿ, Borel measures from distribution functions, and Hausdorff measures on metric spaces.

## Ch21 Core Idea: Measure and Topology
On locally compact Hausdorff spaces, Radon measures are the natural class. The Riesz-Markov theorem identifies [C(X)]* with Radon measures.

## Ch22 Core Idea: Invariant Measures
On compact groups and dynamical systems, invariant measures exist by fixed-point arguments. Haar measure exists on every compact group; ergodic measures exist for continuous maps.

## Key Theorems

### Fubini-Tonelli Theorem (Ch20)
For product measure space (X×Y, M⊗N, μ×ν):
- **Tonelli**: f ≥ 0 measurable on X×Y. Then x ↦ ∫_Y f(x,y)dν(y) is measurable, and ∫_{X×Y} f d(μ×ν) = ∫_X (∫_Y f(x,y)dν) dμ = ∫_Y (∫_X f(x,y)dμ) dν.
- **Fubini**: f integrable on X×Y ⟹ same iterated integral equality; f(x,·) is integrable for a.e. x.
- **Use when**: Computing integrals by iterated integration. Verify nonnegativity or integrability first.
- **Failure mode**: Without nonnegativity/integrability, order of integration can differ (Fubini-counterexample).

### Riesz-Markov Theorem (Ch21)
For X compact Hausdorff, every positive linear functional L on C(X) is given by L(f) = ∫_X f dμ for a unique Radon measure μ on X. ([C(X)]* = space of signed Radon measures.)

- **Hermes**: If skill scoring is a positive linear functional on continuous routing maps, it is represented by a Radon measure on the compact skill space.

### Haar Measure (Ch22)
On every compact topological group G, there exists a unique (up to scalar) translation-invariant Borel probability measure μ (Haar measure): μ(gE) = μ(E) for all g∈G and Borel E.
- **Proof**: Kakutani fixed-point theorem for convex compact sets.
- **Hermes conceptual**: If the space of routing permutations forms a compact group, Haar measure is the "uniform prior" over all routing strategies.

### Ergodic Measures (Ch22) — Bogoliubov-Krylov
For T: X→X continuous on compact metric space X, ∃ Borel probability measure μ with T*μ = μ (T-invariant). Moreover, ergodic measures exist (those for which every T-invariant set has measure 0 or 1).

- **Ergodic theorem** (implied): Time averages equal space averages under ergodic μ. Fundamental for mixing and long-run behavior.

## Key Takeaways (Ch20-22)
1. Fubini: product integrals = iterated integrals when f ≥ 0 (Tonelli) or ∫|f| < ∞ (Fubini). Always check the hypothesis.
2. Radon measures = the right class for measure-topology interaction on compact Hausdorff spaces.
3. Haar measure: every compact group has a canonical uniform measure. Symmetry → measure.
4. Ergodicity: a measure is ergodic iff it cannot be decomposed as a mixture of other invariant measures. Time averages converge to the integral under ergodic measures.

## Connects To
- **Ch17**: Carathéodory construction used for product measures and Hausdorff measures
- **Ch19**: Dunford-Pettis + weak-* compactness of Radon measures used in Ch21 proofs
