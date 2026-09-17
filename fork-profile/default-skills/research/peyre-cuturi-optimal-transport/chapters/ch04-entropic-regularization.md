# Chapter 4 — Entropic Regularization of Optimal Transport

## Core Idea
Add negative entropy regularization to OT: `L^ε_C = min_{P∈U(a,b)} ⟨C,P⟩ - εH(P)`. The unique solution has the form P_{ij} = u_i K_{ij} v_j (matrix scaling), solved by Sinkhorn iterations. This makes OT differentiable, GPU-parallelizable, and statistically better-behaved at the cost of approximation error O(ε).

## Frameworks Introduced

### 4.1 Entropic Regularization
**Discrete entropy**: `H(P) = -Σ_{ij} P_{ij}(log P_{ij} - 1)` (strongly concave)

**Regularized OT**:
```
L^ε_C(a,b) = min_{P∈U(a,b)} ⟨C,P⟩ - εH(P)
```
- Unique solution (ε-strongly convex objective)
- ε→0: approaches max-entropy OT solution
- ε→∞: approaches product coupling a⊗b (independence)

**KL projection interpretation**:
```
P^ε = ProjKL_{U(a,b)}(K)  where K_{ij} = e^{-C_{ij}/ε}
```

### 4.2 Sinkhorn's Algorithm
**Solution form** (Proposition 4.3): `P_{ij} = u_i K_{ij} v_j` where K = e^{-C/ε}

Written as matrix scaling: `P = diag(u) K diag(v)`

Marginal constraints give:
```
u ⊙ (Kv) = a    →   u = a ⊘ (Kv)
v ⊙ (K^T u) = b  →  v = b ⊘ (K^T u)
```

**Algorithm (primal form)**:
```
Initialize: v^(0) = 1_m
Iterate for ℓ = 0,1,...:
  u^(ℓ+1) = a ⊘ (K v^(ℓ))
  v^(ℓ+1) = b ⊘ (K^T u^(ℓ+1))
```
**Convergence**: linear rate `O((1-κ)^ℓ)` where κ is related to condition number of K.

### 4.3 Speeding Up Sinkhorn
- **Separable kernels** (grid data): cost additive over dimensions → K factorizes → complexity O(n^{1+1/d}) vs O(n²)
- **Fourier convolution**: for translation-invariant K, Kv = k⋆v computed with FFT
- **Multiscale Sinkhorn**: coarse-to-fine ε schedule with sparse grids
- **Extrapolation**: SOR-like acceleration, linear rate improves to O((1-κ)^{√ℓ})

### 4.4 Stability and Log-Domain Computations
**Dual form** (Proposition 4.4):
```
L^ε_C(a,b) = max_{f∈R^n, g∈R^m} ⟨f,a⟩ + ⟨g,b⟩ - ε⟨e^{f/ε}, K e^{g/ε}⟩
```
**Log-domain Sinkhorn** (stable for small ε):
```
f^(ℓ+1)_i = min_ε_j (C_{ij} - g^(ℓ)_j) + ε log a_i
g^(ℓ+1)_j = min_ε_i (C_{ij} - f^(ℓ+1)_i) + ε log b_j

where min_ε z = -ε log Σ_i e^{-z_i/ε}  (soft-minimum)
```
**Stabilized form**: subtract previous iterates before soft-min to prevent overflow.

### 4.5 Regularized Approximation Quality
- **Bias**: `L^ε_C(a,b) ≥ LC(a,b)`, difference O(ε log n)
- **Gradient** (Proposition 4.6): `∇L^ε_C(a,b) = (f⋆, g⋆)` (unique dual potentials)
- **Sinkhorn divergence** (debiased, Proposition 4.7):
  ```
  S^ε_C(a,b) = L^ε_C(a,b) - ½L^ε_C(a,a) - ½L^ε_C(b,b) ≥ 0
  ```

### 4.6 Generalized Sinkhorn
- **Bregman projections**: Sinkhorn = alternating KL projections onto {P: P1=a} and {P: P^T1=b}
- **Dykstra's algorithm**: handle multiple convex constraints simultaneously
- **Multimarginal Sinkhorn**: S marginals, cycle through all S normalizations

## Key Concepts
- **Gibbs kernel**: K_{ij} = e^{-C_{ij}/ε} — encodes ground cost as soft similarity
- **Scaling variables**: (u,v) ∈ R^n × R^m parameterize P via P = diag(u)K diag(v)
- **Mutual information regularizer**: entropic cost = E[c(X,Y)] + ε I(X;Y)
- **Schrödinger problem**: stochastic interpretation — find closest stochastic process to Brownian bridge

## Mental Models
- Sinkhorn = weighted Gaussian smoothing of the assignment problem
- ε controls blur: large ε = independence (no transport), small ε = exact OT
- Log-domain = work with log-probabilities to avoid numerical overflow
- Matrix scaling = iteratively normalize rows then columns of softmax matrix

## Anti-patterns
- Running Sinkhorn without log-domain when ε is small (overflow at e^{-C/ε})
- Forgetting that L^ε_C ≠ L^ε_C on the diagonal (biased — use Sinkhorn divergence)
- Using large ε for accuracy-critical applications (error grows with ε)
- Ignoring convergence criterion — always check ||u^{(ℓ+1)} - u^{(ℓ)}||/||u|| < tol

## Code Examples
```python
import numpy as np

def sinkhorn(a, b, C, eps, n_iter=500, tol=1e-9):
    """Sinkhorn algorithm (primal form). Returns P, u, v."""
    K = np.exp(-C / eps)
    v = np.ones(len(b))
    for _ in range(n_iter):
        u = a / (K @ v)
        v_new = b / (K.T @ u)
        if np.max(np.abs(v_new - v)) < tol:
            break
        v = v_new
    return np.diag(u) @ K @ np.diag(v), u, v

def sinkhorn_log(a, b, C, eps, n_iter=500):
    """Log-domain Sinkhorn (stable for small eps)."""
    n, m = C.shape
    f = np.zeros(n)
    g = np.zeros(m)
    for _ in range(n_iter):
        # f_i = softmin_j (C_ij - g_j) + eps*log(a_i)
        M = C - g[None, :]
        f = -eps * np.log(np.sum(np.exp(-M / eps), axis=1)) + eps * np.log(a)
        # g_j = softmin_i (C_ij - f_i) + eps*log(b_j)
        M2 = C - f[:, None]
        g = -eps * np.log(np.sum(np.exp(-M2 / eps), axis=0)) + eps * np.log(b)
    return f, g

def sinkhorn_divergence(a, b, C, eps):
    """Debiased Sinkhorn divergence."""
    def ot_cost(a, b, C):
        _, u, v = sinkhorn(a, b, C, eps)
        K = np.exp(-C / eps)
        P = np.diag(u) @ K @ np.diag(v)
        return np.sum(P * C)
    Wab = ot_cost(a, b, C)
    Waa = ot_cost(a, a, C)
    Wbb = ot_cost(b, b, C)
    return 2*Wab - Waa - Wbb

def sinkhorn_barycenter(distributions, weights, C, eps, n_iter=100):
    """Wasserstein barycenter via Sinkhorn (Ch 9 extension)."""
    n = C.shape[0]
    a = np.ones(n) / n  # current barycenter (uniform init)
    K = np.exp(-C / eps)
    for _ in range(n_iter):
        log_a = np.zeros(n)
        for s, (b_s, w_s) in enumerate(zip(distributions, weights)):
            v_s = b_s / (K.T @ (a / (K @ np.ones(n))))  # simplified
            log_a += w_s * np.log(K @ v_s + 1e-16)
        a = np.exp(log_a)
        a /= a.sum()
    return a
```

## Reference Tables

| Parameter | Effect on P | Effect on cost | Effect on gradient |
|---|---|---|---|
| ε → 0 | Sparse (permutation) | → LC(a,b) | Discontinuous |
| ε → ∞ | Dense (a⊗b) | → 0 | Smooth but uninformative |
| ε moderate | Dense, smoothed | Biased by ~ε log n | Smooth, useful |

## Worked Example
**3×3 uniform transport**: a = b = [1/3, 1/3, 1/3], C = identity×[0,1,2; 1,0,1; 2,1,0]

With ε = 0.1:
- K = e^{-C/0.1}: strong diagonal dominance
- Sinkhorn converges in ~20 iterations
- P ≈ (1/3)I + small off-diagonal corrections
- L^ε ≈ 0 + O(ε) (optimal coupling is identity permutation)

## Key Takeaways
1. Sinkhorn = 2 alternating matrix-vector products per iteration, fully parallelizable on GPU
2. Solution is smooth in inputs (a,b) → gradient ∇L^ε_C = (f⋆, g⋆) via autograd
3. Log-domain version essential for small ε (< 0.01 in typical applications)
4. Sinkhorn divergence (debiased) is a proper distance: ≥ 0, = 0 iff a = b
5. Barycenter computation extends naturally (generalized Sinkhorn)

## Connects To
- Ch 2: Kantorovich formulation being regularized here
- Ch 5: c-transforms in log-domain Sinkhorn = semi-discrete OT
- Ch 8: Sinkhorn divergence interpolates between OT (ε→0) and MMD (ε→∞)
- Ch 9: gradient of L^ε used for barycenter and generative model training
