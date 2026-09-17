# Chapter 7: The Lp Spaces — Completeness and Approximation

## Core Idea
Constructs the Lp(E) spaces (1 ≤ p ≤ ∞), proves Hölder and Minkowski inequalities, and establishes completeness via the Riesz-Fischer theorem. These are the canonical Banach spaces of analysis.

## Key Concepts
- **Lp(E)**: Equivalence classes of measurable f with ∫_E |f|^p < ∞. Norm ‖f‖_p = (∫|f|^p)^{1/p}.
- **L∞(E)**: Essentially bounded functions. ‖f‖_∞ = ess sup|f| = inf{M : m({|f|>M})=0}.
- **Conjugate exponents**: 1/p + 1/q = 1 for 1 < p < ∞. Conjugate of 1 is ∞ and vice versa.
- **Rapidly Cauchy sequence**: Σ ‖fₙ₊₁ - fₙ‖_p < ∞. Key tool for completeness proof.

## Frameworks Introduced

### Young's Inequality
For a,b ≥ 0, 1/p + 1/q = 1: ab ≤ a^p/p + b^q/q.
- **Proof**: Concavity of log. Equality iff a^p = b^q.
- **Use**: Step 1 of Hölder proof. Also: bounds products by weighted means.

### Hölder's Inequality
‖fg‖₁ = ∫|fg| ≤ ‖f‖_p · ‖g‖_q.
- **Proof**: Normalize to ‖f‖_p = ‖g‖_q = 1, apply Young pointwise, integrate.
- **Use when**: Bounding the integral of a product. The inner product ⟨f,g⟩ = ∫fg is bounded by Lp × Lq norms.
- **Hermes**: ∫|routing_weight · score| ≤ ‖routing_weight‖_2 · ‖score‖_2. Concentration of weights (L2 norm) controls the contribution of any single score component.

### Minkowski's Inequality (Triangle Inequality in Lp)
‖f + g‖_p ≤ ‖f‖_p + ‖g‖_p for 1 ≤ p ≤ ∞.
- **Proof**: For p > 1, apply Hölder to ∫|f+g|^p ≤ ∫|f||f+g|^{p-1} + ∫|g||f+g|^{p-1}.
- **Use**: Makes Lp a normed space. Perturbation of distributions is bounded.

### Riesz-Fischer Theorem (Completeness of Lp)
**Statement**: Lp(E) is complete for 1 ≤ p ≤ ∞. Every Cauchy sequence in Lp converges in Lp norm.

**Proof strategy via rapidly Cauchy subsequences**:
1. Extract a rapidly Cauchy subsequence {fₙₖ}.
2. Define g = Σ|fₙₖ₊₁ - fₙₖ|. By MCT, ‖g‖_p ≤ Σ ‖fₙₖ₊₁ - fₙₖ‖_p < ∞, so g ∈ Lp.
3. The partial sums of fₙₖ form an absolutely convergent series a.e. → converges to f a.e.
4. By DCT (with dominator |f_{n₁}| + g), fₙₖ → f in Lp.
5. Since the original sequence is Cauchy and has a convergent subsequence, the whole sequence converges.

**Hermes application**: Working memory vectors in L2 form a complete space — every Cauchy sequence of memory states converges to a valid memory state. No "memory gap" can appear in the limit.

### Separability and Approximation
Lp(E) for 1 ≤ p < ∞ is separable: simple functions with rational coefficients on rational intervals are dense. L∞ is not separable.

- **Use when**: Numerical approximation, discretization. Dense subsets guarantee that any Lp function can be approximated by simple functions.

## Key Takeaways
1. Hölder is the master inequality: Young → Hölder → Minkowski. All Lp analysis flows from these three.
2. Riesz-Fischer completeness means Lp is a Banach space — closed under limits, reliable for iterative approximation.
3. For p = 2: L2 is a Hilbert space. Inner product ⟨f,g⟩ = ∫fg. Pythagoras holds: ‖f+g‖² = ‖f‖² + 2⟨f,g⟩ + ‖g‖².
4. p = 1: weakest Lp norm, biggest space; p = ∞: strongest norm, smallest space. L∞ ⊆ Lq ⊆ Lp ⊆ L1 on finite-measure sets when p > q.

## Connects To
- **Ch08**: Dual space of Lp is Lq; weak convergence in Lp
- **Ch19**: Same results for general (abstract) measure spaces
