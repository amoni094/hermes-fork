# Chapter 10: Metric Spaces — Three Fundamental Theorems

## Core Idea
Three cornerstone results with broad applications: Arzelà-Ascoli (compactness via equicontinuity), Baire Category (no complete metric space is meagre), and Banach Contraction Principle (fixed-point iteration).

## Key Concepts
- **Equicontinuous family**: F of functions on a metric space is equicontinuous at x₀ iff ∀ε>0 ∃δ>0 s.t. ∀f∈F: d(x,x₀)<δ ⟹ |f(x)-f(x₀)| < ε. Uniform for all f simultaneously.
- **Pointwise bounded**: F is pointwise bounded iff sup_{f∈F}|f(x)| < ∞ for each x.
- **Meagre (first category)**: Countable union of nowhere-dense sets. A complete metric space is non-meagre.
- **Contraction**: T: X → X with Lip(T) = sup_{x≠y} d(Tx,Ty)/d(x,y) ≤ c < 1.

## The Three Theorems

### Arzelà-Ascoli Theorem
**Statement**: A subset F of C(X) (X compact metric) has compact closure iff F is pointwise bounded and equicontinuous.

- **Use when**: Proving existence of a convergent subsequence of functions (e.g., from a minimizing sequence).
- **How to apply**: Check (1) ‖f‖_∞ ≤ M for all f ∈ F, (2) |f(x)-f(y)| ≤ ω(d(x,y)) for a modulus ω independent of f. Then any sequence in F has a uniformly convergent subsequence.
- **Hermes**: Sequences of routing functions on a compact context space have convergent subsequences if the routing maps are uniformly bounded and equicontinuous (e.g., Lipschitz with shared constant).

### Baire Category Theorem
**Statement**: A complete metric space X is not meagre in itself. Equivalently: if X = ∪Fₙ where each Fₙ is closed, then at least one Fₙ has nonempty interior.

**Corollaries**:
- Uniform Boundedness Principle (Ch13) follows from Baire
- A sequence of continuous functions that converges pointwise on all of X must be continuous at a dense Gδ set of points.

- **Hermes**: If Hermes memory (a complete metric space) were covered by "bad behavior" sets, one of them would have to contain an open ball — i.e., bad behavior is unavoidable on a whole region, not just scattered. Contrapositively: if bad regions are all nowhere-dense, memory can avoid them globally.

### Banach Contraction Principle (Fixed-Point Theorem)
**Statement**: If (X,d) is complete and T: X→X is a contraction (c < 1), then T has a unique fixed point x*, and for any x₀, d(Tⁿx₀, x*) ≤ cⁿ/(1-c) · d(Tx₀, x₀).

- **Use when**: Iterative algorithms, proving convergence of agent loops, existence of solutions.
- **Algorithm**: Iterate x_{n+1} = T(xₙ). Error decreases geometrically: d(xₙ, x*) ≤ cⁿ·d(x₀, x*).
- **Hermes application**: If each step of the memory consolidation loop is a contraction on the state space with constant c < 1, convergence is guaranteed and the rate is cⁿ. To apply: verify the Lipschitz constant of the update operator.

## Key Takeaways
1. Arzelà-Ascoli: compactness in function spaces requires both pointwise bound AND equicontinuity. Lack of either allows non-compact behavior.
2. Baire: completeness prevents a space from being "thin everywhere." Applied via proof by contradiction: assume X is meagre, derive that some open set is empty.
3. Banach Contraction: simple, effective, and gives quantitative convergence rates. The contraction constant c directly controls convergence speed.

## Connects To
- **Ch13**: Baire → Uniform Boundedness Principle → Open Mapping, Closed Graph theorems
- **Ch15**: Compactness in weak topology is proved by different methods (Alaoglu) since Arzelà-Ascoli needs equicontinuity
