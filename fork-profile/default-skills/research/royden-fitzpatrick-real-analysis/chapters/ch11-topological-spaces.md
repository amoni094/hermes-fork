# Chapters 11–12: Topological Spaces

## Core Idea (Ch11)
Generalizes metric spaces to topological spaces where the notion of "open set" is axiomatic, not distance-induced. Proves compactness and connectedness in this abstract setting.

## Core Idea (Ch12)
Three fundamental theorems: Urysohn's Lemma (separating closed sets by continuous functions), Tychonoff's Product Theorem (product of compact spaces is compact), Stone-Weierstrass (polynomials are dense in C(X)).

## Key Concepts
- **Topological space (X,τ)**: τ ⊆ 2^X with ∅,X ∈ τ, closed under finite intersections and arbitrary unions.
- **Hausdorff (T₂)**: Distinct points have disjoint open neighborhoods. Metric spaces are Hausdorff.
- **Compact**: Every open cover has a finite subcover. In metric spaces: equivalent to sequential compactness.
- **Normal space**: Disjoint closed sets can be separated by disjoint open sets.

## Key Theorems

### Urysohn's Lemma
If X is normal, A and B are disjoint closed sets, then ∃ continuous f: X → [0,1] with f|_A = 0 and f|_B = 1.
- **Use**: Constructing continuous functions to "interpolate" between two closed regions. Foundation of partitions of unity.

### Tychonoff's Product Theorem
Arbitrary product of compact spaces (with product topology) is compact.
- **Proof**: Uses Zorn's Lemma (or ultrafilters). Requires Axiom of Choice for infinite products.
- **Hermes**: Product space of bounded memory components is compact — a theoretical foundation for memory state space compactness.

### Stone-Weierstrass Theorem
If A ⊆ C(X) is a subalgebra separating points and containing constants, then A is dense in C(X).
- **Special case**: Polynomials are dense in C[a,b] (classical Weierstrass approximation).
- **Use**: Justifying that parameterized function families (e.g., neural network functions) can approximate any continuous function arbitrarily well.

## Key Takeaways
1. Topology = structure for talking about convergence and continuity without a metric.
2. Compactness in product spaces (Tychonoff) is the key to weak-* compactness (Alaoglu in Ch15).
3. Stone-Weierstrass: a rich-enough class of functions is always dense — the foundation for approximation theory.

## Connects To
- **Ch15**: Alaoglu's theorem uses Tychonoff on product of intervals
- **Ch21**: Topology and measure interact; Radon measures on compact Hausdorff spaces
