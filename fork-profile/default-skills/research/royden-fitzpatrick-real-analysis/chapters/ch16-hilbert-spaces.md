# Chapter 16: Continuous Linear Operators on Hilbert Spaces

## Core Idea
Hilbert spaces (complete inner product spaces) have special structure — orthogonal complement, Riesz-Fréchet duality, Bessel's inequality — enabling the Hilbert-Schmidt theorem (compact symmetric operators have eigenvectors) and the Riesz-Schauder theorem (Fredholm operators of index zero).

## Key Concepts
- **Inner product**: ⟨f,g⟩ satisfying bilinearity, symmetry ⟨f,g⟩=⟨g,f⟩, positivity ⟨f,f⟩>0 for f≠0. Induces norm ‖f‖ = √⟨f,f⟩.
- **Cauchy-Schwarz**: |⟨f,g⟩| ≤ ‖f‖·‖g‖. Equality iff f,g are collinear.
- **Orthogonality**: f ⊥ g iff ⟨f,g⟩ = 0. Pythagorean theorem: ‖f+g‖² = ‖f‖² + ‖g‖² when f⊥g.
- **Orthogonal complement**: Y⊥ = {x∈H: ⟨x,y⟩=0 ∀y∈Y}.
- **Bessel's inequality**: For orthonormal {eₙ}: Σ|⟨f,eₙ⟩|² ≤ ‖f‖².
- **Parseval's identity**: Equality in Bessel's iff {eₙ} is a complete orthonormal basis (ONB): f = Σ⟨f,eₙ⟩eₙ and ‖f‖² = Σ|⟨f,eₙ⟩|².

## Key Theorems

### Riesz-Fréchet Representation
**Statement**: Every bounded linear functional T: H → ℝ has the form T(h) = ⟨h,g⟩ for a unique g ∈ H with ‖T‖ = ‖g‖. Thus H* ≅ H (Hilbert spaces are self-dual).

- **Proof**: Let Y = ker(T). If Y = H, g = 0. Else pick z ⊥ Y with T(z) ≠ 0; set g = T(z)/‖z‖² · z.
- **Hermes**: Every bounded linear scorer on L2 memory states is a dot product with a "template vector" g — the scorer is fully represented by g ∈ L2.

### Orthogonal Decomposition
**Statement**: For closed subspace Y ⊆ H: H = Y ⊕ Y⊥ (every h = y + y⊥, uniquely). The orthogonal projection P: H → Y satisfies ‖h - Ph‖ = d(h, Y) = min_{y∈Y} ‖h-y‖.

- **Hermes application**: Memory compression to subspace Y: compressed state = P_Y(state). Compression error = ‖state - P_Y(state)‖₂ is minimized. Pythagoras: ‖state‖² = ‖compressed‖² + ‖error‖².

### Hilbert-Schmidt Theorem
**Statement**: Let T: H → H be a compact symmetric operator (⟨Tf,g⟩ = ⟨f,Tg⟩). Then H has an orthonormal basis of eigenvectors of T, with eigenvalues → 0.

- **Use when**: Diagonalizing symmetric operators; PCA (covariance operator); spectral theory.
- **Hermes**: Covariance operator of memory state embeddings (if symmetric) can be diagonalized — gives principal components of the memory space.

### Riesz-Schauder Theorem (Fredholm Operators of Index Zero)
T = I - K with K compact on H. Then: ker(T) is finite-dimensional; T(H) is closed; T is injective iff surjective iff bijective. The "Fredholm alternative" holds: either Tf = g has a unique solution for all g, or Tf = 0 has a nontrivial solution.

## Key Takeaways
1. Hilbert spaces are the "nicest" infinite-dimensional spaces: self-dual, orthogonal complement, Pythagorean theorem.
2. Orthogonal projection gives the best approximation in a closed subspace — the foundation for minimum-error compression.
3. Hilbert-Schmidt: compact symmetric operators are "almost finite-dimensional" (diagonalizable with eigenvalues → 0).
4. Riesz-Schauder: Fredholm alternative — either a unique solution or a nontrivial null space, never both.

## Connects To
- **Ch07**: L2(E) is a concrete Hilbert space; this chapter gives the abstract theory
- **Ch14**: Hahn-Banach → Riesz-Fréchet (more general; Hilbert case is cleaner)
- **Ch19**: General L2(X,μ) Hilbert space inherits all these results
