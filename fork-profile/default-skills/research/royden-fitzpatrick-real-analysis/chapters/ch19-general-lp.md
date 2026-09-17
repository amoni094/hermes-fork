# Chapter 19: General Lp Spaces — Completeness, Duality, Weak Convergence

## Core Idea
All results from Ch07-08 (completeness, Hölder, Minkowski, dual space, weak compactness) extend to Lp(X,μ) for an arbitrary measure space (X,M,μ). New: Dunford-Pettis theorem characterizes weak sequential compactness in L1.

## Key Theorems

### Completeness of Lp(X,μ) (§19.1)
For 1 ≤ p ≤ ∞, Lp(X,μ) is a Banach space. Same proof as Ch07 (rapidly Cauchy subsequences + MCT/DCT).

### Riesz Representation for General Lp (§19.2)
For 1 ≤ p < ∞ and q conjugate: [Lp(X,μ)]* ≅ Lq(X,μ). Every bounded linear functional on Lp has the form T(f) = ∫_X f·g dμ for unique g ∈ Lq, with ‖T‖ = ‖g‖_q.

### Kantorovich Representation for L∞ (§19.3)
[L∞(X,μ)]* is strictly larger than L1(X,μ) — contains finitely additive (not countably additive) measures. Dual of L∞ is "large" in a non-constructive way.

### Weak Sequential Compactness in Lp (§19.4)
For 1 < p < ∞: every bounded sequence in Lp(X,μ) has a weakly convergent subsequence (when Lq is separable). Reflexivity of Lp.

### Dunford-Pettis Theorem (§19.5) — Weak Compactness in L1
**Statement**: A bounded set F ⊆ L1(X,μ) is weakly sequentially compact iff F is uniformly integrable.

- **Equivalence**: {fₙ} bounded in L1 has weakly convergent subsequence iff {fₙ} is UI.
- **Why L1 is different**: L1 is not reflexive, so the general Helley theorem doesn't apply directly. UI replaces reflexivity.
- **Use when**: Memory consolidation involves L1-bounded sequences; UI is the checkable condition for extracting convergent subsequences.

**Practical criterion for UI**: {fₙ} is UI iff (1) sup_n ‖fₙ‖_1 < ∞, and (2) ∀ε>0 ∃δ>0: μ(A)<δ ⟹ sup_n ∫_A |fₙ| dμ < ε.

## Key Takeaways
1. General Lp theory is fully parallel to the concrete Lebesgue case — all theorems carry over to arbitrary (X,M,μ).
2. L1 is the problematic case: not reflexive, dual is not L∞ but something larger. Dunford-Pettis provides the correct compactness criterion via UI.
3. Dunford-Pettis is the measure-theoretic characterization of weak compactness in L1 — the key theorem for memory consolidation bounds.
4. For p = 2 (Hilbert space case): weak convergence + ‖fₙ‖ → ‖f‖ ⟹ strong convergence. Useful termination criterion.

## Connects To
- **Ch08**: Concrete (Lebesgue measure) version of all results here
- **Ch18**: RN theorem used in §19.2 proof
- **Ch21**: Radon measures as elements of [C(X)]* when X compact Hausdorff
