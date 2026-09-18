# Chapter 5: Lebesgue Integration — Further Topics

## Core Idea
Extends convergence theory: the full Vitali Convergence Theorem for infinite-measure domains, convergence in measure as a mode between pointwise and uniform, and the characterization of Riemann vs. Lebesgue integrability.

## Key Concepts
- **General Vitali Theorem** (σ-finite domains): {fₙ} UI + tight over E (possibly infinite measure), fₙ → f a.e. ⟹ ∫_E fₙ → ∫_E f. Tightness condition: ∀ε>0 ∃ finite-measure E₀ ⊆ E s.t. sup_n ∫_{E\E₀} |fₙ| < ε.
- **Convergence in measure**: {fₙ} → f in measure on E iff ∀η>0: lim_{n→∞} m({x∈E : |fₙ(x)-f(x)| > η}) = 0.
- **Hierarchy of convergence modes**:
  - Uniform ⟹ pointwise ⟹ a.e.
  - Uniform ⟹ in measure ⟹ subsequence a.e. (Riesz theorem)
  - L¹ convergence ⟹ in measure (by Markov/Chebyshev inequality)
  - a.e. + finite measure ≠ in measure in general (Egorov bridges them)
- **Riemann integrability**: f: [a,b] → ℝ bounded is Riemann integrable iff the set of discontinuities has Lebesgue measure zero (Lebesgue's theorem, proved here).

## Frameworks Introduced

### Chebyshev's Inequality (Measure-Theoretic Form)
For measurable f ≥ 0 and t > 0: m({f > t}) ≤ (1/t)∫f dμ.
- **Use when**: Bounding the measure of an exceptional set from an integral bound.
- **Hermes**: If ∫|score_n - score|dμ → 0 (L¹ convergence), then for any ε>0, the fraction of contexts where |score_n - score| > ε goes to zero. Controls degradation fraction.

### Riesz Theorem on Convergence in Measure
If fₙ → f in measure, then ∃ subsequence {fₙₖ} → f a.e.
- **Use when**: You have in-measure convergence and need a.e. behavior for a subsequence.

## Key Takeaways
1. Uniform integrability + tightness is the "right" condition for L¹ convergence without a dominator, even on infinite domains.
2. Convergence in measure is the weakest useful mode: implies only subsequential a.e. convergence.
3. Chebyshev converts L¹ bounds to measure bounds — fundamental for moving between "integral small" and "set small."
4. A bounded function on [a,b] is Riemann integrable iff its discontinuities form a null set — Lebesgue measure zero is the right concept here.

## Connects To
- **Ch04**: Vitali here generalizes the finite-measure version
- **Ch07**: Lp convergence implies in-measure convergence (Chebyshev with |fₙ-f|^p)
- **Ch18**: Same modes of convergence appear for abstract measures
