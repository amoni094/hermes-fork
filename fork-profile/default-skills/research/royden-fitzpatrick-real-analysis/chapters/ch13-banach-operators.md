# Chapter 13: Continuous Linear Operators Between Banach Spaces

## Core Idea
The three foundational theorems of Banach space operator theory: Open Mapping, Closed Graph, and Uniform Boundedness (Banach-Steinhaus). All follow from the Baire Category Theorem.

## Key Concepts
- **Bounded linear operator**: T: X→Y linear with ‖T‖ = sup{‖Tx‖/‖x‖ : x≠0} < ∞. Equivalent: T is continuous.
- **Open Mapping**: T maps open sets to open sets.
- **Closed Graph**: Graph {(x,Tx)} is closed in X×Y iff T is bounded (for complete spaces).
- **Compact operator**: Maps bounded sets to precompact (totally bounded) sets. Always bounded; not surjective if X infinite-dimensional.

## The Three Theorems (all via Baire Category)

### Open Mapping Theorem
**Statement**: If T: X→Y is a bounded surjective linear operator between Banach spaces, then T is an open mapping (maps open sets to open sets). In particular, T⁻¹ is bounded.

- **Use**: If you have a bijective bounded operator, its inverse is automatically bounded. No need to check separately.
- **Hermes**: A linear memory encoder T: L2(context) → L2(compressed) that is bijective automatically has bounded decoding.

### Closed Graph Theorem
**Statement**: T: X→Y linear. If the graph of T is closed in X×Y and both X,Y are Banach, then T is bounded.

- **Use**: To prove an operator is bounded, it suffices to show: if xₙ → x and Txₙ → y, then Tx = y.
- **Practical form**: "If T preserves limits, T is bounded."

### Uniform Boundedness Principle (Banach-Steinhaus)
**Statement**: If {Tₙ} is a family of bounded linear operators X→Y (X Banach) such that sup_n ‖Tₙ(x)‖ < ∞ for each x, then sup_n ‖Tₙ‖ < ∞.

- **Proof**: Baire applied to closed sets Fₖ = {x: sup_n ‖Tₙ(x)‖ ≤ k}. One Fₖ must contain a ball; expand from there.
- **Hermes application**: If individual routing scores per context are uniformly bounded (pointwise bound), the operator norm (worst-case over all contexts) is also uniformly bounded. Prevents hidden unbounded behavior.
- **Failure mode**: If X is not complete, the theorem fails. Completeness is essential.

### Infinite-Dimensional Normed Spaces Lose Compactness
The closed unit ball of an infinite-dimensional normed space is not compact. This motivates the weak topology.

## Key Takeaways
1. Open Mapping + Closed Graph are "automatic boundedness" theorems — from surjectivity/closed-graph, get bounded inverse/operator.
2. Uniform Boundedness is the workhorse for convergence of operator sequences (e.g., Fourier partial sums).
3. Infinite-dimensional Banach spaces are never locally compact — must use weak topology for compactness arguments.

## Connects To
- **Ch14**: Hahn-Banach extends functionals; enables duality arguments
- **Ch15**: Weak topology recovers compactness in infinite dimensions
