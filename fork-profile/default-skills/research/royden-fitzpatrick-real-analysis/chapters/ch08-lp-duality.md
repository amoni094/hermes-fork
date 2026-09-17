# Chapter 8: The Lp Spaces — Duality and Weak Convergence

## Core Idea
Identifies the dual space of Lp as Lq (Riesz Representation), defines and exploits weak sequential convergence in Lp, and uses weak compactness to prove existence of minimizers for convex functionals.

## Key Concepts
- **Dual space X***: Bounded linear functionals T: X → ℝ. Norm ‖T‖* = sup{|T(f)| : ‖f‖ ≤ 1}.
- **Riesz Representation for Lp**: For 1 < p < ∞ and q conjugate, every bounded linear functional T on Lp(E) is of the form T(f) = ∫_E fg dμ for a unique g ∈ Lq(E), with ‖T‖* = ‖g‖_q. So [Lp]* ≅ Lq.
- **Weak convergence in Lp**: fₙ ⇀ f iff ∫fₙg → ∫fg for all g ∈ Lq. Notation: "⇀" vs "→" (strong).
- **Weak vs. strong**: Strong convergence ⟹ weak convergence. Weak convergence ≠ strong (in infinite dimension).
- **Helley's Theorem**: A bounded sequence in a reflexive Banach space has a weakly convergent subsequence.
- **Minimization of convex functionals**: If F: Lp(E) → ℝ is convex, lower semicontinuous, and coercive (F(fₙ)→∞ as ‖fₙ‖→∞), then F attains its minimum.

## Frameworks Introduced

### Riesz Representation Theorem
**Statement**: For 1 ≤ p < ∞, [Lp(E,μ)]* ≅ Lq(E,μ) via the map g ↦ Tg where Tg(f) = ∫fg.

- **Proof sketch**: Assume T bounded on Lp. Define ν(A) = T(1_A). Show ν ≪ μ. Apply Radon-Nikodym (Ch18): ν(A) = ∫_A g dμ for some g. Extend T(f) = ∫fg by linearity and density.
- **Hermes application**: Every linear scoring functional on L2 memory states is represented by an inner product with a "weight vector" in L2. The dual pairing ⟨score_template, memory_state⟩ is the canonical form.

### Weak Sequential Compactness in Lp (1 < p < ∞)
**Theorem**: If ‖fₙ‖_p ≤ M for all n, then ∃ subsequence fₙₖ ⇀ f weakly in Lp.

**Proof**: [Lp]* = Lq is separable for 1 < p < ∞. Diagonal argument on a countable dense set in Lq extracts a weakly convergent subsequence.

- **Hermes application**: A bounded sequence of memory state vectors in L2 always has a weakly convergent subsequence. "Memory compactness" — every bounded memory history has a limiting state (in the weak sense), preventing unbounded drift.

### Minimization Theorem
To minimize convex, lower-semicontinuous, coercive F on Lp: take infimizing sequence {fₙ}, extract weakly convergent subsequence (by Helley), show F(f) ≤ lim inf F(fₙ) by lower-semicontinuity.

- **Use when**: Existence proofs for optimal policies, regularization-based memory compression, minimum-norm estimators.

## Key Takeaways
1. [Lp]* = Lq for 1 < p < ∞: duality is symmetric. For p = 1: [L1]* = L∞. For p = ∞: [L∞]* ⊋ L1 (strictly larger — contains finitely additive measures).
2. Weak convergence is the "right" convergence for infinite-dimensional optimization: it's compact on bounded sets.
3. Weak convergence preserves norm bounds: fₙ ⇀ f ⟹ ‖f‖_p ≤ lim inf ‖fₙ‖_p (Fatou-type lower bound).
4. Strong convergence = weak convergence + ‖fₙ‖_p → ‖f‖_p.

## Connects To
- **Ch14**: Hahn-Banach generalizes the dual-space framework to any normed space
- **Ch15**: Alaoglu and Kakutani theorems give weak compactness in general Banach spaces
- **Ch19**: Same results for abstract Lp(X,μ)
