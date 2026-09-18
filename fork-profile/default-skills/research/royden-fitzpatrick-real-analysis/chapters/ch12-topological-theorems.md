# Chapter 12: Topological Spaces — Three Fundamental Theorems

## Core Idea
Three cornerstone theorems for compact Hausdorff spaces: Urysohn's Lemma (separation by continuous functions), Tychonoff's Product Theorem (product of compacts is compact), and Stone-Weierstrass (dense approximation by subalgebras).

## Key Theorems

### Urysohn's Lemma
**Statement**: If X is a normal topological space and A, B are disjoint closed sets, then there exists a continuous function f: X → [0,1] with f(A) = 0 and f(B) = 1.

- **Proof idea**: For each dyadic rational r = k/2^n in [0,1], construct open sets U_r with A ⊆ U₀, B ⊆ U₁ᶜ, and r < s ⟹ cl(U_r) ⊆ U_s. Define f(x) = inf{r: x ∈ U_r}.
- **Use when**: Need to build a continuous function interpolating between two closed regions.
- **Hermes**: On a normal context space, two disjoint closed context classes can always be separated by a continuous scoring function.

### Tychonoff's Product Theorem
**Statement**: Any product of compact topological spaces (with the product topology) is compact.

- **Proof**: Uses Zorn's Lemma (or ultrafilter characterization). For countable products, diagonal argument suffices.
- **Corollary**: [0,1]^I is compact for any index set I — used in Alaoglu's theorem (unit ball of X* as a subset of ℝ^X is compact in product topology).
- **Key role**: Foundation for Alaoglu's theorem (Ch15) — the weak-* compactness of dual unit ball.

### Stone-Weierstrass Theorem
**Statement**: Let X be a compact Hausdorff space. If A ⊆ C(X) is a subalgebra that (1) separates points and (2) contains the constant functions, then A is dense in C(X) (uniform topology).

- **Classical case**: Polynomials on [a,b] are dense in C[a,b] (Weierstrass approximation).
- **Complex version**: If also closed under conjugation, dense in C(X, ℂ).
- **Use when**: Proving that a parameterized function class (e.g., polynomials, trigonometric functions) is expressive enough to approximate any continuous function.

## Key Takeaways
1. Urysohn is the "existence" theorem for continuous functions on topological spaces — normal spaces have rich continuous function algebras.
2. Tychonoff requires Axiom of Choice for uncountable products. Without AC, it fails for general uncountable products.
3. Stone-Weierstrass: the two conditions (separates points + contains constants) are necessary and sufficient for density. Missing either causes failure.

## Connects To
- **Ch11**: Urysohn requires normality (T4) — metric spaces and compact Hausdorff spaces are normal
- **Ch15**: Tychonoff → Alaoglu (weak-* compactness of dual unit ball)
- **Ch21**: Stone-Weierstrass used to approximate continuous functions on compact groups
