# Chapter 5 — Semidiscrete Optimal Transport

## Core Idea
One marginal is discrete (finite support), the other is continuous. The OT problem decomposes into a partition of X (Laguerre cells) by the discrete support. The dual problem is smooth and concave in one variable, amenable to SGD. This is the bridge from discrete to continuous OT.

## Frameworks Introduced

### 5.1 c-Transform and c̄-Transform
For a discrete measure with support (y_j) and weights b and dual potential g:
```
(g^{C̄})_i = min_j (C_{ij} - g_j)    [discrete C̄-transform]
f^c(x) = min_j (c(x, y_j) - g_j)      [continuous c-transform]
```
The continuous c-transform defines a partition of X into **Laguerre cells**:
```
Lag_j(g) = {x ∈ X : c(x,y_j) - g_j ≤ c(x,y_k) - g_k  ∀k≠j}
```
For squared Euclidean cost: Laguerre cells = power cells (Voronoi + weights).

### 5.2 Semidiscrete Formulation
**Problem**: α continuous, β = Σ_j b_j δ_{y_j} discrete.

**Dual** (concave maximization in g ∈ R^m):
```
G(g) = ∫_X f^c(x) dα(x) + ⟨g, b⟩
     = Σ_j g_j b_j + ∫_{Lag_j(g)} (c^c_transform(x)) dα(x)
```
**Gradient**: `∂G/∂g_j = b_j - α(Lag_j(g))` (difference of target mass and Laguerre cell mass)

**Optimal condition**: `α(Lag_j^*(g^*)) = b_j  ∀j` — Laguerre cells have prescribed mass.

### 5.3 Entropic Semidiscrete Formulation
**Regularized dual**:
```
G^ε(g) = -ε ∫_X log(Σ_j e^{(g_j - c(x,y_j))/ε}) dα(x) + ⟨g, b⟩
```
**Gradient**: `∂G^ε/∂g_j = b_j - ∫_X σ_j^ε(x) dα(x)` where σ_j^ε(x) = softmax weights.

This is smooth in g (no discontinuity at Laguerre cell boundaries).

### 5.4 Stochastic Optimization Methods
Since α is continuous (samples available), use:
- **SGD**: draw x_i ~ α, estimate gradient, update g
- **SAG/SVRG**: variance-reduced SGD for faster convergence

## Key Concepts
- **Laguerre tessellation**: generalized Voronoi diagram where cells are determined by dual potentials g
- **Power diagram**: Laguerre cells for squared Euclidean cost; efficient computation via convex hull
- **Brenier's theorem**: for square Euclidean cost, optimal Monge map T(x) = ∇φ(x) where φ is a convex function
- **Dual smoothness**: G^ε is strongly concave in g with Hessian bounded by 1/ε

## Mental Models
- Laguerre cells = "delivery zones": each point x goes to the nearest-adjusted target y_j
- Dual g = price adjustments that balance supply and demand across cells
- SGD = real-time gradient estimation by sampling from the continuous source distribution

## Anti-patterns
- Forgetting that Laguerre cells can be empty (measure zero mass) — use regularization
- Computing gradients of G(g) without handling cell boundary discontinuities
- Ignoring that semi-discrete OT requires a numerical integration step

## Code Examples
```python
import numpy as np
from scipy.spatial import Voronoi

def laguerre_cells_approx(Y, g, X_samples):
    """Approximate Laguerre cell assignment via MC sampling.
    
    Args:
        Y: (m, d) discrete support points
        g: (m,) dual potentials
        X_samples: (n_samples, d) samples from continuous source α
    Returns:
        assignments: (n_samples,) index of assigned Laguerre cell
    """
    # For each x, find j minimizing c(x,y_j) - g_j
    # c(x,y) = ||x-y||^2 for W2
    dists = np.sum((X_samples[:, None, :] - Y[None, :, :])**2, axis=-1)
    scores = dists - g[None, :]  # n_samples × m
    return np.argmin(scores, axis=1)

def semidiscrete_gradient(Y, b, g, X_samples):
    """Gradient of semidiscrete OT dual via MC."""
    assignments = laguerre_cells_approx(Y, g, X_samples)
    # Estimate cell masses
    cell_mass = np.bincount(assignments, minlength=len(b)) / len(X_samples)
    return b - cell_mass  # ∂G/∂g_j = b_j - α(Lag_j)

def semidiscrete_sgd(Y, b, alpha_sampler, n_iter=1000, lr=0.01, batch_size=100):
    """SGD for semidiscrete OT dual."""
    m = len(b)
    g = np.zeros(m)
    for t in range(n_iter):
        X_batch = alpha_sampler(batch_size)
        grad = semidiscrete_gradient(Y, b, g, X_batch)
        g += lr * grad  # maximize G
    return g
```

## Reference Tables

| Setting | Source α | Target β | Algorithm |
|---|---|---|---|
| Discrete-discrete | Histogram a | Histogram b | Network Simplex / Sinkhorn |
| Semidiscrete | Continuous | Discrete (b, y_j) | Laguerre + gradient descent |
| Continuous | Density ρ_α | Density ρ_β | Monge-Ampère PDE |

## Key Takeaways
1. Semidiscrete OT = smooth concave maximization in dual variable g ∈ R^m
2. Laguerre cells = optimal transport "delivery zones" (generalized Voronoi)
3. SGD works because source samples can be drawn on-the-fly
4. Entropic version makes the gradient smoother (no cell boundary discontinuities)
5. Connection to Brenier's theorem: optimal map is gradient of convex potential

## Connects To
- Ch 3: C-transforms generalized here to continuous setting
- Ch 4: entropic regularization smooths the semidiscrete formulation
- Ch 9: used for min-Kantorovich estimators (generative model training)
