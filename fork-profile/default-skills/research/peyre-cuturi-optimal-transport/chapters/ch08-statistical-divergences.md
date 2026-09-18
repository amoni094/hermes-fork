# Chapter 8 — Statistical Divergences

## Core Idea
Compare OT with the other main families of distribution divergences: φ-divergences (KL, TV, Hellinger, χ²), integral probability metrics (IPM, including MMD and W₁). Key findings: W_p is not Hilbertian (no embedding), has poor sample complexity in high dimensions (O(n^{-2/d})), but Sinkhorn divergence achieves O(n^{-1/2}) sample complexity — matching MMD.

## Frameworks Introduced

### 8.1 φ-Divergences
For entropy function φ:
```
Dφ(α|β) = ∫ φ(dα/dβ(x)) dβ(x)
```
Key instances:

| Divergence | φ(s) | Properties |
|---|---|---|
| KL(α\|β) | s log s - s + 1 | Asymmetric, ∞ if supp(α)⊄supp(β) |
| TV(α,β) | \|s-1\|/2 | Symmetric, bounded [0,1] |
| Hellinger | (√s-1)² | Symmetric, bounded, squared |
| χ²(α\|β) | (s-1)² | Asymmetric |

**Dual form**: `Dφ(α|β) = sup_f ∫f dα - ∫φ*(f) dβ` (Fenchel duality)

### 8.2 Integral Probability Metrics (IPM)
```
Dβ(α,β) = sup_{f ∈ B} |∫f dα - ∫f dβ|
```
**Instances**:
- **W₁**: B = {f: Lip(f) ≤ 1} (Kantorovich–Rubinstein)
- **MMD**: B = unit ball in RKHS with kernel k; `MMD(α,β)² = E_{x,x'~α}k(x,x') - 2E_{x~α,y~β}k(x,y) + E_{y,y'~β}k(y,y')`
- **TV**: B = {f: ||f||_∞ ≤ 1}

### 8.3 Wasserstein Spaces Are Not Hilbertian
W_p distances cannot be isometrically embedded in any Hilbert space:
- Triangle inequality with equality fails in specific triangle configurations
- No kernel k(α,β) such that W_p² = ||φ(α)-φ(β)||²_H exactly
- **Consequence**: kernelized methods (MMD-style) cannot exactly reproduce OT geometry
- **Sliced Wasserstein** is positive definite but not a Wasserstein distance

### 8.4 Empirical Estimators for OT, MMD and φ-Divergences
**Sample complexity** (n samples from α,β on R^d):

| Method | Convergence rate |
|---|---|
| W_p (exact) | O(n^{-1/d}) for d≥3; O(n^{-1/2}) for d=1,2 |
| W_p (entropic, ε-fixed) | O(n^{-1/2}) — parametric rate |
| MMD with fixed kernel | O(n^{-1/2}) |
| KL divergence | O(n^{-2/(d+2)}) with kernel estimator |

**Key insight**: W_p suffers curse of dimensionality; Sinkhorn divergence with fixed ε achieves O(n^{-1/2}).

### 8.5 Entropic Regularization: Between OT and MMD
Sinkhorn divergence interpolates:
```
W̃^{p,ε}(α,β) = 2W^{p,ε}(α,β) - W^{p,ε}(α,α) - W^{p,ε}(β,β)
```
- ε → 0: recovers W_p (full OT geometry)
- ε → ∞: recovers energy distance / MMD with kernel k(x,y) = -d(x,y)^p

## Key Concepts
- **φ-divergences**: pointwise ratio comparison (need common support); no transport
- **IPM/weak metrics**: test function comparison (don't need common support); can handle singular measures
- **Curse of dimensionality**: W_p estimation from n samples requires n → ∞ exponentially fast with d
- **Energy distance**: `ED(α,β) = 2E_{x~α,y~β}||x-y|| - E||x-x'|| - E||y-y'||` (equals Sinkhorn div at ε→∞)

## Mental Models
- φ-divergences: "how different are the local densities?" (microscopic)
- W_p: "how far do I need to move mass?" (macroscopic, geometric)
- MMD: "can a test function tell the two distributions apart?" (functional)
- Sinkhorn divergence: smooth bridge between geometry (OT) and function matching (MMD)

## Anti-patterns
- Using W_p for high-d comparison without regularization (O(n^{-1/d}) convergence unacceptable)
- Using KL when distributions have different support (KL = ∞)
- Forgetting bias in Sinkhorn: L^ε_C(α,α) ≠ 0 — must use debiased Sinkhorn divergence
- Assuming Wasserstein kernels are positive definite (they are not in general)

## Code Examples
```python
import numpy as np

# MMD with Gaussian kernel
def mmd_squared(X, Y, sigma=1.0):
    """Maximum Mean Discrepancy (squared) with Gaussian kernel."""
    def rbf(X, Y):
        diff = X[:, None, :] - Y[None, :, :]
        return np.exp(-np.sum(diff**2, axis=-1) / (2*sigma**2))
    return (rbf(X,X).mean() - 2*rbf(X,Y).mean() + rbf(Y,Y).mean())

# φ-divergence estimators (KL via k-NN)
def kl_knn_estimator(X, Y, k=5):
    """Kozachenko-Leonenko KL estimator via k-NN distances."""
    from sklearn.neighbors import NearestNeighbors
    n, m, d = len(X), len(Y), X.shape[1]
    # Distances in X to k-th NN in X (excluding self)
    nn_x = NearestNeighbors(n_neighbors=k+1).fit(X)
    rx = nn_x.kneighbors(X)[0][:, -1]  # k-th NN distance in X
    # Distances from X to k-th NN in Y
    nn_y = NearestNeighbors(n_neighbors=k).fit(Y)
    sy = nn_y.kneighbors(X)[0][:, -1]  # k-th NN distance in Y
    return d * np.mean(np.log(sy / rx)) + np.log(m / (n-1))

# Sinkhorn divergence (debiased)
def sinkhorn_divergence(a_samples, b_samples, eps=0.1):
    from ot import sliced_wasserstein_distance
    # Use sliced wasserstein as proxy
    return sliced_wasserstein_distance(a_samples, b_samples, n_projections=50)
```

## Reference Tables

| Divergence | Symmetric | Triangle ineq. | Handles disjoint supp. | Sample rate |
|---|---|---|---|---|
| KL | No | No | No (∞) | O(n^{-2/(d+2)}) |
| TV | Yes | Yes | Yes | O(n^{-2/(d+2)}) |
| W_p | Yes | Yes | Yes | O(n^{-1/d}) |
| MMD | Yes | Yes | Yes | O(n^{-1/2}) |
| Sinkhorn div | Yes | Yes* | Yes | O(n^{-1/2}) |

## Key Takeaways
1. W_p is not Hilbertian — cannot be exactly kernelized
2. W_p has curse of dimensionality (O(n^{-1/d})) but Sinkhorn divergence achieves O(n^{-1/2})
3. φ-divergences require common support; W_p and MMD do not
4. Sinkhorn divergence interpolates between OT geometry (ε→0) and MMD (ε→∞)
5. For d ≥ 5, prefer sliced Wasserstein or Sinkhorn for empirical comparisons

## Connects To
- Ch 4: Sinkhorn divergence formally defined here
- Ch 6: W₁ as IPM with Lipschitz functions
- Ch 9: choice of divergence for variational inference/generative models
- Ch 10: sliced Wasserstein achieves O(n^{-1/2}) for high dimensions
