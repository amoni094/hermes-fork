# Chapter 15: Compactness Regained — The Weak Topology

## Core Idea
The norm topology on infinite-dimensional Banach spaces has no compactness of bounded sets. The weak topology (induced by the dual) restores sequential compactness for bounded sets in reflexive spaces, via Alaoglu's, Kakutani's, and Eberlein-Smulian theorems.

## Key Theorems

### Alaoglu's Theorem (Extension of Helley's)
**Statement**: The closed unit ball of X* is compact in the weak-* topology (pointwise convergence topology on X).

- **Proof**: Unit ball B* ⊆ ∏_{x∈X} [-‖x‖, ‖x‖]. This product is compact by Tychonoff. B* is closed in the product topology → compact.
- **Consequence**: Any bounded sequence {Tₙ} in X* has a weak-* cluster point (subnet converging weak-*). For separable X, cluster point is a limit of a subsequence.
- **Hermes**: Bounded sequences of linear scoring templates always have cluster points in the weak-* topology — scoring "strategies" cannot drift unboundedly.

### Kakutani's Theorem
**Statement**: X is reflexive if and only if the closed unit ball of X is weakly compact.

- **Direction 1** (reflexive ⟹ weakly compact): Use Alaoglu on X** ≅ X; pull back to X.
- **Direction 2** (weakly compact ⟹ reflexive): Via Krein-Milman and separation.
- **Hermes**: Working memory state space (L2 finite-dimensional approximation) is reflexive, hence the unit ball is weakly compact. Memory state searches on bounded sets always terminate with a limit point.

### Eberlein-Smulian Theorem
**Statement**: For a Banach space X, a subset K is weakly compact iff every sequence in K has a weakly convergent subsequence (weak sequential compactness = weak compactness).

- **Significance**: Compactness and sequential compactness coincide for the weak topology in Banach spaces (unlike for general topological spaces).
- **Use when**: Proving existence of weakly convergent subsequences — you only need to check bounded sequences.

### Metrizability of Weak Topology on Bounded Sets
If X is a separable Banach space, the weak topology on bounded subsets of X is metrizable. Similarly, if X is separable, weak-* topology on bounded subsets of X* is metrizable.

- **Consequence**: For separable spaces, compactness = sequential compactness = existence of convergent subsequences — no need for nets or ultrafilters.

## Key Takeaways
1. Alaoglu: dual unit ball is always weak-* compact, regardless of reflexivity. This is the "compactness you always have."
2. Kakutani: reflexive ↔ weakly compact unit ball. Lp (1<p<∞) and Hilbert spaces are reflexive.
3. Eberlein-Smulian: in Banach spaces, weak compactness reduces to finding weakly convergent subsequences.
4. Strategy for infinite-dimensional optimization: bounded constraint set + lower semicontinuous objective → extract weakly convergent minimizing subsequence → lower semicontinuity gives the minimum.

## Connects To
- **Ch12**: Tychonoff's theorem is the engine of Alaoglu
- **Ch14**: Kakutani links to reflexivity defined via J: X → X**
- **Ch19**: Dunford-Pettis characterizes weak compactness in L1 via UI (replaces Kakutani for non-reflexive L1)
