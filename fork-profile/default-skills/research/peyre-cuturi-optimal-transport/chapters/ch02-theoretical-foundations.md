# Chapter 2 — Theoretical Foundations

## Core Idea
Formalize OT as a linear program over a transportation polytope. Three equivalent frameworks handle progressively more general measures: histograms, discrete measures, arbitrary measures. The Wasserstein distance arises naturally and inherits geometry from the ground metric.

## Frameworks Introduced

### 2.1 Histograms and Measures
- **Probability simplex**: `Σ_n = {a ∈ R+^n : Σ_i a_i = 1}`
- **Discrete measures**: `α = Σ_i a_i δ_{x_i}` with locations x_i ∈ X
- **General measures**: Radon measures M(X), integration against continuous test functions

### 2.2 Monge Problem
Deterministic map T: X → Y minimizing cost with mass conservation (push-forward T_# α = β):
```
min_{T: T_#α=β} Σ_i c(x_i, T(x_i))    (discrete)
min_{T: T_#α=β} ∫ c(x, T(x)) dα(x)    (general)
```
**Problem**: nonconvex, may have no solution (e.g., splitting mass impossible)

### 2.3 Kantorovich Relaxation
Replace maps with coupling matrices P ∈ U(a,b):
```
U(a,b) = {P ∈ R+^{n×m} : P 1_m = a, P^T 1_n = b}
LC(a,b) = min_{P ∈ U(a,b)} ⟨C, P⟩ = Σ_{i,j} C_{i,j} P_{i,j}
```
**Key theorem (Birkhoff)**: Vertices of U(1/n, 1/n) = permutation matrices → Kantorovich tightens assignment problem

### 2.4 Metric Properties
For cost C_{ij} = d(x_i, y_j)^p with distance d:
- **W_p(a,b) = LC(a,b)^{1/p}** defines a distance on Σ_n × Σ_m
- Triangle inequality holds
- W_p is the Kantorovich-Rubinstein metric (for p=1: dual of Lipschitz-1 functions)

### 2.5 Dual Problem
Strong duality (LP duality):
```
LC(a,b) = max_{(f,g) ∈ R(C)} ⟨f,a⟩ + ⟨g,b⟩
R(C) = {(f,g) ∈ R^n × R^m : f_i + g_j ≤ C_{ij}  ∀i,j}
```
- Dual variables (f,g) = Kantorovich potentials
- C-transform: f^C_j = min_i (C_{ij} - f_i) gives optimal g from optimal f
- Complementary slackness: P_{ij} > 0 ⟹ f_i + g_j = C_{ij}

### 2.6 Special Cases
- **1D distributions**: W_p has closed form via quantile functions: `W_p^p = ∫_0^1 |F_α^{-1}(t) - F_β^{-1}(t)|^p dt`
- **Gaussians**: `W_2^2(N(m_α,Σ_α), N(m_β,Σ_β)) = |m_α-m_β|^2 + B(Σ_α, Σ_β)^2` (Bures metric)
- **Uniform histograms**: W_p reduces to optimal permutation (matching)

## Key Concepts
- **Push-forward T_# α**: moves mass of measure α through map T; T_#(a_i δ_{x_i}) = a_i δ_{T(x_i)}
- **Pull-back T^#**: operates on functions (image warping), dual to push-forward
- **Coupling π**: joint distribution with marginals α, β; encodes correlation structure
- **Transportation polytope**: bounded convex polytope with n+m equality constraints, (n+m-1) tight at vertices
- **Monge-Ampère equation**: PDE characterizing optimal T for densities on R^d

## Mental Models
- P_{ij} = probability of sending unit of mass from source i to target j
- f_i = price to "ship from" bin i; g_j = "receive at" bin j; price constraint f_i + g_j ≤ C_{ij}
- Wasserstein distance = minimum expected cost under optimal joint distribution
- W_2 geometry on Gaussians is Euclidean in (mean, std) coordinates

## Anti-patterns
- Conflating push-forward (moves measures) with pull-back (warps functions)
- Assuming Monge map always exists for general discrete measures
- Using W_p without ensuring both measures have the same total mass

## Code Examples
```python
import numpy as np
from scipy.optimize import linprog

def kantorovich_lp(a, b, C):
    """Solve OT as a linear program."""
    n, m = len(a), len(b)
    # Flatten C to vector
    c_vec = C.flatten()
    # Constraints: row sums = a, col sums = b
    A_eq = np.zeros((n + m, n * m))
    for i in range(n):
        A_eq[i, i*m:(i+1)*m] = 1.0
    for j in range(m):
        A_eq[n+j, j::m] = 1.0
    b_eq = np.concatenate([a, b])
    res = linprog(c_vec, A_eq=A_eq, b_eq=b_eq, bounds=[(0,None)]*n*m)
    return res.fun, res.x.reshape(n, m)

# 1D Wasserstein via quantiles
def w1_1d(x, y):
    """W1 between sorted 1D empirical measures."""
    xs, ys = np.sort(x), np.sort(y)
    return np.mean(np.abs(xs - ys))

def w2_1d(x, y):
    """W2 between sorted 1D empirical measures."""
    xs, ys = np.sort(x), np.sort(y)
    return np.sqrt(np.mean((xs - ys)**2))
```

## Reference Tables

| Concept | Discrete form | Continuous form |
|---|---|---|
| Histogram | a ∈ Σ_n | α ∈ M₁⁺(X) |
| Cost | C_{ij} = c(x_i,y_j) | c: X×Y → R |
| Coupling | P ∈ U(a,b) | π ∈ U(α,β) |
| OT value | LC(a,b) = ⟨C,P⋆⟩ | Lc(α,β) = ∫c dπ⋆ |
| Wasserstein | Wp^p = LC(a,b) | Wp^p = Lc(α,β) |
| Dual | max ⟨f,a⟩+⟨g,b⟩ | max ∫f dα + ∫g dβ |

## Worked Example
**2-bin transport**: a = [0.6, 0.4], b = [0.3, 0.7], C = [[0, 1],[2, 0]]
- Optimal coupling: P = [[0.3, 0.3],[0, 0.4]] (verify: P 1 = a, P^T 1 = b)
- Cost: LC = 0·0.3 + 1·0.3 + 2·0 + 0·0.4 = 0.3
- Dual: f = [0, 0], g = [0, 1] → f_i+g_j ≤ C_{ij}: ✓

## Key Takeaways
1. Kantorovich = convex LP relaxation of Monge (always feasible, solvable in poly time)
2. OT defines a metric on distributions that inherits ground geometry
3. Duality is crucial: dual variables are "transport prices" with economic interpretation
4. 1D OT has closed form (quantile matching); higher-d requires algorithms
5. Strong duality holds: primal optimum = dual optimum (LP theory)

## Connects To
- Ch 3: algorithms to solve the LP (network simplex, Hungarian)
- Ch 4: entropic regularization makes this differentiable and scalable
- Ch 8: comparison with other statistical divergences (KL, TV, MMD)
- Ch 9: Wasserstein as loss function for ML
