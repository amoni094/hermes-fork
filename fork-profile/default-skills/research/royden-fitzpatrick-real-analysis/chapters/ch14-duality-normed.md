# Chapters 14–16: Duality, Weak Topology, Hilbert Spaces

## Ch14 Core Idea: Duality for Normed Spaces
The Hahn-Banach theorem — every bounded linear functional on a subspace extends to the whole space — is the foundational existence theorem for dual spaces. From it flow reflexivity, separation of convex sets, and the Krein-Milman theorem.

## Ch15 Core Idea: Compactness Regained via Weak Topology
The norm topology on an infinite-dimensional Banach space has no compactness. The weak topology (induced by the dual) restores sequential compactness on bounded sets for reflexive spaces.

## Ch16 Core Idea: Hilbert Space Operators
Hilbert spaces (complete inner product spaces) have an orthogonal complement for every closed subspace, enabling the Hilbert-Schmidt and Riesz-Schauder (Fredholm) theorems.

## Key Theorems

### Hahn-Banach Theorem (Ch14)
**Statement**: If p is a sublinear functional on X and f is a linear functional on subspace Y with f ≤ p on Y, then ∃ extension F: X→ℝ with F|_Y = f and F ≤ p on all of X.

**Corollaries**:
- Every x ≠ 0 is separated from 0 by a bounded linear functional: ∃ T ∈ X* with T(x) = ‖x‖, ‖T‖* = 1.
- ‖x‖ = sup{|T(x)| : T ∈ X*, ‖T‖* ≤ 1} — the norm equals the "supremum of testing with functionals."
- **Separation**: Two disjoint convex sets can be separated by a hyperplane (under appropriate conditions).

### Reflexivity (Ch14)
X is reflexive iff the natural embedding J: X → X** (x ↦ evaluation at x) is surjective. Reflexive spaces: Hilbert spaces, Lp for 1<p<∞. Non-reflexive: L1, L∞, C[a,b].

### Alaoglu's Theorem (Ch15)
The closed unit ball of X* is compact in the weak-* topology (pointwise convergence on X).

- **Use**: Every bounded sequence in X* has a weak-* convergent subnet (or subsequence if X is separable).
- **Hermes**: The space of bounded linear scoring functionals (dual of memory space) is compact in the weak-* topology — every sequence of scoring templates has a cluster point.

### Kakutani's Theorem (Ch15)
X is reflexive iff the closed unit ball of X is weakly compact.

### Eberlein-Smulian Theorem (Ch15)
In a Banach space, weak compactness = weak sequential compactness. A set K is weakly compact iff every sequence in K has a weakly convergent subsequence.

### Hilbert Space: Orthogonal Complement (Ch16)
For closed subspace Y of Hilbert space H: H = Y ⊕ Y⊥ (orthogonal direct sum). Every h ∈ H has a unique best approximation in Y: Py (the orthogonal projection).

- **Hermes**: Working memory state h ∈ L2 projected onto the "relevant subspace" Y gives the nearest compressed representation Py(h). Compression error: ‖h - Py(h)‖ is minimized.

### Riesz-Fréchet Representation (Ch16)
Every bounded linear functional T on Hilbert space H is of the form T(h) = ⟨h,g⟩ for a unique g ∈ H with ‖T‖ = ‖g‖. [H* ≅ H — Hilbert spaces are self-dual.]

## Key Takeaways
1. Hahn-Banach: existence of many bounded linear functionals — the dual space is "large."
2. Weak topology is coarser than norm: more compact sets, but harder to check continuity.
3. Reflexive spaces (Lp, 1<p<∞) have best possible weak compactness — bounded sequences always have weakly convergent subsequences.
4. Hilbert spaces are the "nicest" infinite-dimensional spaces: orthogonal complement, Pythagoras, Cauchy-Schwarz, self-dual.

## Connects To
- **Ch08**: Riesz representation for Lp is the concrete version of Ch14/16 abstract dual theory
- **Ch19**: Same reflexivity/compactness results for general Lp(X,μ)
