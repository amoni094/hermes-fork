# Chapter 10 — Extensions of Optimal Transport

## Core Idea
OT generalizes to: (1) multiple marginals simultaneously (multimarginal), (2) unnormalized measures (unbalanced OT with KL penalty), (3) extra coupling constraints (color preserving), (4) high-dimensional slicing (sliced Wasserstein), (5) vector/matrix-valued measures, (6) measures on different metric spaces (Gromov–Wasserstein). Each extends the framework while preserving key properties.

## Frameworks Introduced

### 10.1 Multimarginal Problems
Couple S distributions simultaneously:
```
min_{P ∈ U(a_s)_s} ⟨C, P⟩   where P ∈ R^{n₁×...×n_S}
```
**Sinkhorn extension**: cycle through s = 1,...,S normalizations:
```
u_{s,i} ← a_{s,i} / Σ_{i'} K_{i,i'} Π_{r≠s} u_{r,i'}
```
**Applications**: quantum chemistry (Coulomb cost), multimarginal barycenters, tracking.

### 10.2 Unbalanced Optimal Transport
Relax marginal constraints by KL penalty:
```
UOT_λ(α,β) = min_P [⟨C,P⟩ + λ KL(P1|a) + λ KL(P^T1|b)]
```
**Sinkhorn for unbalanced OT**:
```
u^(ℓ+1) = (a ⊘ (Kv))^{λ/(λ+ε)}    (soft marginal update)
v^(ℓ+1) = (b ⊘ (K^T u))^{λ/(λ+ε)}
```
λ → ∞: standard OT; λ → 0: independent coupling.

**Applications**: comparing images with different total masses, robust OT, partial transport.

### 10.4 Sliced Wasserstein Distance
**Definition**:
```
SW_p(α,β) = ∫_{S^{d-1}} W_p(P_θ#α, P_θ#β) dσ(θ)
```
where P_θ(x) = ⟨x,θ⟩ is the 1D projection onto direction θ.

**Properties**:
- O(Kn log n) for K Monte Carlo projections (vs O(n²) for exact OT)
- Positive definite kernel: k(α,β) = -SW(α,β)
- **Not** equal to W_p in general (lower bound)
- Achieves O(n^{-1/2}) sample complexity in any dimension

**Max-Sliced Wasserstein**: `max_{θ} W_p(P_θ#α, P_θ#β)` — more discriminative

**Sliced Wasserstein barycenter**: project → 1D barycenter → reconstruct.

### 10.5 Transporting Vectors and Matrices
Extend to vector-valued measures α ∈ M(X; R^d):
- Cost: c((x,u),(y,v)) = d(x,y) + ||u-v||²
- Applications: texture synthesis, color transfer with spatial context
- **Matrix OT**: compare positive semidefinite matrices (Bures metric = W₂ on Gaussians)
- Sinkhorn-like algorithm for matrix scaling (Gurvits)

### 10.6 Gromov–Wasserstein Distance
Compare distributions on different (incompatible) metric spaces (X, d_X) and (Y, d_Y):
```
GW((a,D), (b,D'))² = min_{P∈U(a,b)} Σ_{i,j,i',j'} |D_{ii'} - D'_{jj'}|² P_{ij} P_{i'j'}
```
**Properties**: invariant to isometries; satisfies triangle inequality.
**Algorithm**: iterative linearization (Frank-Wolfe):
```
Initialize P ∈ U(a,b)
Iterate:
  Compute gradient G_{ij} = Σ_{i'j'} |D_{ii'} - D'_{jj'}|² P_{i'j'}
  Solve linear OT: P_new = argmin_{P∈U} ⟨G, P⟩
  Update: P ← (1-γ)P + γ P_new
```
**Entropic GW**: add -εH(P) → Sinkhorn per linearization step.

**Applications**: cross-modal alignment (text-images), cross-lingual word embeddings, shape matching.

## Key Concepts
- **Multimarginal**: generalize to S-way coupling (tensor), applications in quantum chemistry
- **Unbalanced OT**: mass can be created/destroyed; parameter λ controls penalty
- **Sliced Wasserstein**: 1D projections → sorting → average; avoids curse of dimensionality
- **Gromov–Wasserstein**: no shared embedding needed; compare by internal structure
- **Partial OT**: transport only a fraction m ≤ 1 of mass (robust to outliers)

## Mental Models
- Sliced Wasserstein = "Radon transform of distributions" → average 1D comparisons
- GW = "shape matching": find coupling that best preserves pairwise distances
- Unbalanced OT = OT with a "trash bin" (mass can disappear at cost λ per unit)
- Multimarginal = "multi-way assignment problem" for S simultaneous distributions

## Anti-patterns
- Using GW for aligned distributions (standard OT is faster and exact)
- Using sliced Wasserstein when the projection direction matters critically (use max-sliced or GW)
- Forgetting that GW is nonconvex — local minima possible, initialization matters
- Running GW without entropic regularization (extremely slow for large n)

## Code Examples
```python
import numpy as np
import ot

# Sliced Wasserstein Distance
def sliced_wasserstein(X, Y, n_proj=200, p=2, seed=42):
    """Monte Carlo sliced Wasserstein distance."""
    rng = np.random.default_rng(seed)
    d = X.shape[1]
    a = np.ones(len(X)) / len(X)
    b = np.ones(len(Y)) / len(Y)
    sw = 0.0
    for _ in range(n_proj):
        theta = rng.standard_normal(d)
        theta /= np.linalg.norm(theta)
        x1d = X @ theta
        y1d = Y @ theta
        sw += ot.wasserstein_1d(x1d, y1d, a, b, p=p)
    return (sw / n_proj) ** (1/p)

# Gromov-Wasserstein (using POT)
def gromov_wasserstein_dist(X, Y, n_iter=100):
    """Approximate GW distance between point clouds."""
    n, m = len(X), len(Y)
    a = np.ones(n) / n
    b = np.ones(m) / m
    # Distance matrices
    DX = np.sum((X[:, None] - X[None])**2, axis=-1)
    DY = np.sum((Y[:, None] - Y[None])**2, axis=-1)
    T, log = ot.gromov.gromov_wasserstein(DX, DY, a, b, 'square_loss', log=True)
    return log['gw_dist']

# Unbalanced Sinkhorn
def unbalanced_sinkhorn(a, b, C, eps=0.1, lam=1.0, n_iter=100):
    """Unbalanced OT via Sinkhorn with KL marginal relaxation."""
    K = np.exp(-C / eps)
    v = np.ones(len(b))
    alpha = lam / (lam + eps)  # soft marginal exponent
    for _ in range(n_iter):
        u = (a / (K @ v)) ** alpha
        v = (b / (K.T @ u)) ** alpha
    return np.diag(u) @ K @ np.diag(v)

# Multimarginal Sinkhorn (S = 3 marginals)
def multimarginal_sinkhorn(distributions, C_tensor, eps=0.1, n_iter=50):
    """C_tensor: (n1,n2,n3,...,nS) cost tensor."""
    S = len(distributions)
    K = np.exp(-C_tensor / eps)
    scalings = [np.ones(len(d)) for d in distributions]
    
    for _ in range(n_iter):
        for s in range(S):
            # Contract K along all dimensions except s
            axes = [i for i in range(S) if i != s]
            K_contracted = K.copy()
            for t in axes[::-1]:
                K_contracted = np.tensordot(K_contracted, scalings[t], 
                                           axes=([t if t < s else t], [0]))
            scalings[s] = distributions[s] / K_contracted
    return K  # scaled tensor

# Entropic GW
def entropic_gromov_wasserstein(DX, DY, a, b, eps=0.1, n_iter=20):
    """Entropic Gromov-Wasserstein via Sinkhorn linearization."""
    return ot.gromov.entropic_gromov_wasserstein(DX, DY, a, b, 'square_loss', eps, 
                                                   numItermax=n_iter)
```

## Reference Tables

| Extension | Use Case | Key Change | Algorithm |
|---|---|---|---|
| Multimarginal | S-way matching, barycenters | S-dimensional coupling | Cyclic Sinkhorn |
| Unbalanced OT | Different total masses | KL marginal penalty | Soft Sinkhorn |
| Sliced W | High-dim comparison | 1D projections | Sort + average |
| Gromov-W | Different metric spaces | Relative distances | Frank-Wolfe + Sinkhorn |
| Partial OT | Robust (outliers) | Transport fraction m | Sinkhorn + threshold |

## Key Takeaways
1. Sliced Wasserstein: O(Kn log n) vs O(n²) — the practical choice for high dimensions
2. GW solves cross-modal alignment without requiring a shared embedding
3. Unbalanced OT handles mass mismatch (essential for comparing unnormalized measures)
4. Multimarginal Sinkhorn extends naturally by cycling through S normalizations
5. Entropic regularization makes all these extensions tractable (and differentiable)

## Connects To
- Ch 4: Sinkhorn foundation used in all extensions
- Ch 8: sliced Wasserstein achieves O(n^{-1/2}) sample complexity regardless of d
- Ch 9: multimarginal formulation of barycenters; GW for cross-lingual learning
