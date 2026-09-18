# Cheatsheet — Computational Optimal Transport

## Core Problem

```
LC(a,b) = min_{P∈U(a,b)} ⟨C,P⟩     Kantorovich OT
L^ε_C(a,b) = min_{P∈U(a,b)} ⟨C,P⟩ - εH(P)    Entropic OT (Sinkhorn)
Wp(α,β) = LC(a,b)^{1/p}  with C_{ij} = d(x_i,y_j)^p    Wasserstein distance
```

---

## Sinkhorn Algorithm

```python
K = exp(-C / ε)           # Gibbs kernel
v = ones(m)
for i in range(n_iter):
    u = a / (K @ v)       # Row normalization
    v = b / (K.T @ u)     # Column normalization
P = diag(u) @ K @ diag(v)  # Optimal coupling
cost = sum(P * C)         # OT cost ≈ L^ε_C(a,b)
```

**Log-domain (stable)**:
```python
f, g = zeros(n), zeros(m)
for i in range(n_iter):
    # f_i = softmin_j(C_ij - g_j) + ε log a_i
    f = -ε * logsumexp((-C + g) / ε, axis=1) + ε * log(a)
    g = -ε * logsumexp((-C.T + f) / ε, axis=1) + ε * log(b)
```

---

## Wasserstein Distances Reference

| Case | Formula | Complexity |
|---|---|---|
| 1D empirical | sort + L^p | O(n log n) |
| 1D continuous | ∫|F_α^{-1}-F_β^{-1}|^p dt | Closed form |
| Gaussian W₂ | \|m_α-m_β\|² + Bures(Σ_α,Σ_β) | Closed form |
| Discrete, exact | Network simplex | O(n³) worst |
| Discrete, approx | Sinkhorn | O(n²/ε²) |
| High-d | Sliced Wasserstein | O(Kn log n) |
| Different spaces | Gromov-Wasserstein | O(n² iter) |

---

## Key Formulas

### Dual Problem
```
LC(a,b) = max_{f_i+g_j≤C_{ij}} ⟨f,a⟩ + ⟨g,b⟩
```

### Gradient of Entropic OT
```
∇_a L^ε_C(a,b) = f⋆      (optimal dual potential)
∇_b L^ε_C(a,b) = g⋆      (optimal dual potential)
```

### Sinkhorn Divergence (Debiased)
```
S^ε(a,b) = 2L^ε(a,b) - L^ε(a,a) - L^ε(b,b)  ≥ 0
```

### C-Transform
```
(f^C)_j = min_i(C_{ij} - f_i)    discrete
f^c(x) = min_j(c(x,y_j) - g_j)   continuous → Laguerre cells
```

### Sliced Wasserstein
```
SW_p(α,β) = ∫_{S^{d-1}} W_p(P_θ#α, P_θ#β) dσ(θ)
# Monte Carlo: K random projections → sort → W_p in 1D → average
```

### Wasserstein Barycenter
```
α* = argmin_α Σ_s λ_s W₂²(α, α_s)    (Fréchet mean in W₂)
# Sinkhorn barycenter: log α ← Σ_s λ_s log(u_s ⊙ (K v_s))
```

### Gromov-Wasserstein
```
GW²((a,D),(b,D')) = min_{P∈U(a,b)} Σ_{ii'jj'} |D_{ii'}-D'_{jj'}|² P_{ij}P_{i'j'}
```

### Unbalanced Sinkhorn
```
u ← (a / (Kv))^{λ/(λ+ε)}     # soft normalization (λ = KL penalty)
v ← (b / (K^T u))^{λ/(λ+ε)}
```

---

## Algorithm Complexity

| Algorithm | Time | Space | Notes |
|---|---|---|---|
| Network simplex | O(n³) | O(n²) | Exact |
| Sinkhorn | O(n²/ε²) | O(n²) | Approx; GPU-parallel |
| Log-domain Sinkhorn | O(n²/ε²) | O(n²) | Stable small ε |
| Separable Sinkhorn | O(n^{1+1/d}) | O(n) | Grid data |
| Sliced Wasserstein | O(Kn log n) | O(nd) | High-d; O(n^{-1/2}) stats |
| GW (entropic) | O(n² × iter) | O(n²) | Nonconvex |
| Sinkhorn barycenter | O(Sn²) | O(n²) | S measures |

---

## POT Library Quick Reference

```python
import ot

# Exact OT (network simplex)
T = ot.emd(a, b, C)            # plan
w = ot.emd2(a, b, C)           # cost only

# Sinkhorn
T = ot.sinkhorn(a, b, C, reg=0.1)
w = ot.sinkhorn2(a, b, C, reg=0.1)

# Sinkhorn divergence (debiased)
w = ot.bregman.empirical_sinkhorn_divergence(X, Y, 0.1)

# 1D Wasserstein
w = ot.wasserstein_1d(x, y)

# Sliced Wasserstein
w = ot.sliced_wasserstein_distance(X, Y, n_projections=100)

# Wasserstein barycenter
bar = ot.bregman.barycenter(A, C, reg=0.1, weights=lam)

# Gromov-Wasserstein
T, log = ot.gromov.gromov_wasserstein(DX, DY, a, b, 'square_loss', log=True)
T = ot.gromov.entropic_gromov_wasserstein(DX, DY, a, b, 'square_loss', eps=0.1)

# Unbalanced OT
T = ot.unbalanced.sinkhorn_unbalanced(a, b, C, reg=0.1, reg_m=1.0)

# Partial OT
T = ot.partial.partial_wasserstein(a, b, C, m=0.8)
```

---

## ε Selection Guide

| Data scale | Recommended ε | Notes |
|---|---|---|
| C entries ∈ [0,1] | 0.01–0.1 | Typical image/text |
| C entries ∈ [0,100] | 1–10 | Unnormalized distances |
| C entries ∈ [0,d] | d/100–d/10 | d-dimensional vectors |
| Need exact OT | ε → 0 | Use network simplex instead |
| Need smooth gradient | ε ≥ 0.05·median(C) | Safe for autograd |

**Rule of thumb**: `ε = 0.05 × median(C)` gives good accuracy + stability.

---

## Convergence Criteria

```python
# Sinkhorn: check marginal violation
err = ||diag(u) K diag(v) @ ones - a|| + ||diag(v) K.T diag(u) @ ones - b||
# Converged when err < tol (e.g., 1e-6)

# Alternative: check relative change in dual potentials
||(f_new - f_old)|| / max(1, ||f_old||) < tol
```

---

## Common Pitfalls Checklist

- [ ] Histograms sum to 1 (or use unbalanced OT)
- [ ] Cost matrix has correct scale for chosen ε
- [ ] Using log-domain Sinkhorn when ε < 0.01
- [ ] Debiasing Sinkhorn divergence for proper metric
- [ ] Initializing GW with reasonable coupling (not zeros)
- [ ] Checking for empty Laguerre cells in semidiscrete OT
- [ ] Using centered dual potentials when computing gradients

---

## Statistical Decision Rules

| Scenario | Method |
|---|---|
| d ≤ 2, n large | Exact W_p (network simplex) |
| d ≤ 5, gradient needed | Sinkhorn divergence |
| d > 5, comparison only | Sliced Wasserstein |
| d > 5, gradient training | Sinkhorn (geomloss) |
| Outliers present | Unbalanced OT (λ ~ 1.0) |
| Different metric spaces | Gromov-Wasserstein |
| n samples small (< 1000) | Fixed ε Sinkhorn divergence |
| Generative model | Sinkhorn loss or WGAN |
