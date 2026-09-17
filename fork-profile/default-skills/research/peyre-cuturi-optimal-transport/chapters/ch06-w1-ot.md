# Chapter 6 — W₁ Optimal Transport

## Core Idea
The W₁ (1-Wasserstein, Earth Mover's Distance) has special structure: its dual = supremum over Lipschitz-1 functions. This leads to computationally efficient formulations on metric spaces, Euclidean spaces, and graphs, with connections to total variation, maximum mean discrepancy, and WGAN.

## Frameworks Introduced

### 6.1 W₁ on Metric Spaces
**Kantorovich–Rubinstein duality**:
```
W₁(α, β) = sup_{f: Lip(f)≤1} ∫f dα - ∫f dβ
```
where Lip(f) = sup_{x≠y} |f(x)-f(y)|/d(x,y) ≤ 1.

**Key consequence**: W₁ is a weak metric — bounded by: `W₁ ≤ d_max · TV(α,β)` and `TV(α,β) ≤ W₁/d_min`.

### 6.2 W₁ on Euclidean Spaces
For α,β supported on R^d with d > 1:
- Dual = vector field s with |s(x)| ≤ 1 and div(s) = α - β
- Can be computed via L∞-constrained divergence problems
- Numerical solution via proximal splitting (see Ch 7)

### 6.3 W₁ on Graphs
For graphs G = (V, E) with edge weights:
- Ground distance = shortest path distance d_G(i,j)
- W₁ solvable via min-cost flow on graph
- O(|E| log |V|) with Dijkstra + LP on graph

## Key Concepts
- **Lipschitz constraint**: the "witness function" in Kantorovich–Rubinstein must be 1-Lipschitz
- **W₁ vs W₂**: W₁ more robust to outliers; W₂ has smoother geometry
- **WGAN connection**: discriminator approximates Lipschitz-1 witness function
- **Sliced W₁**: project to 1D (sorting), average → avoids high-dim curse (see Ch 10)

## Mental Models
- W₁ = area between CDFs in 1D (exact, O(n log n))
- Witness function f = "value map" telling you where mass is scarce vs abundant
- Graph W₁ = min-cost flow problem on the graph topology

## Anti-patterns
- Using W₁ when you need smooth gradients (prefer W₂ or Sinkhorn)
- Computing W₁ in high dimensions directly (use sliced or entropic approximation)
- Training WGAN with unconstrained discriminator (must enforce Lipschitz via gradient penalty or spectral norm)

## Code Examples
```python
# W1 in 1D via sorting
def w1_1d(x, y, p=1):
    xs, ys = np.sort(x), np.sort(y)
    return np.mean(np.abs(xs - ys)**p)**(1/p)

# W1 on graphs via scipy shortest path + LP
from scipy.sparse.csgraph import shortest_path

def graph_distance_matrix(adj_matrix):
    return shortest_path(adj_matrix, directed=False)

def w1_graph(a, b, adj_matrix):
    D = graph_distance_matrix(adj_matrix)
    return emd2(a, b, D)  # network simplex on graph W1

# WGAN gradient penalty (Gulrajani et al.)
def gradient_penalty(real, fake, discriminator, lambda_gp=10):
    alpha = torch.rand(real.size(0), 1)
    interpolated = alpha * real + (1-alpha) * fake
    d_interp = discriminator(interpolated)
    grad = torch.autograd.grad(d_interp, interpolated)[0]
    return lambda_gp * ((grad.norm(2, dim=1) - 1)**2).mean()
```

## Key Takeaways
1. W₁ dual = supremum over Lipschitz-1 functions (Kantorovich–Rubinstein)
2. W₁ on graphs reduces to min-cost flow (polynomial time)
3. W₁ in 1D = ∫|F_α^{-1}(t) - F_β^{-1}(t)| dt (area between CDFs)
4. WGAN uses discriminator as approximate Lipschitz-1 witness
5. Sliced Wasserstein approximates W_p in high dimensions via 1D projections

## Connects To
- Ch 8: W₁ comparison with TV and other divergences
- Ch 10: sliced Wasserstein for high-dimensional approximation
