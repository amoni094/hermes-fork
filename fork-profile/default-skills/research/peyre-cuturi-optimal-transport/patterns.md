# Design Patterns — Computational Optimal Transport

Practical patterns for applying OT techniques to real problems.

---

## Pattern 1: Distribution Comparison (Choosing Your Metric)

**Context**: You need to measure similarity/distance between two distributions.

**Decision tree**:
```
Are distributions on the same metric space?
├── YES: Is dimension high (d > 5)?
│   ├── YES: Use Sliced Wasserstein (O(Kn log n))
│   │         or Sinkhorn divergence (fast, differentiable)
│   └── NO: 
│       Is exact OT needed?
│       ├── YES, d ≤ 2: Use network simplex (exact, fast)
│       └── NO: Use Sinkhorn divergence (smooth, scalable)
└── NO (different spaces): Use Gromov-Wasserstein
```

**Choosing ε (entropic regularization)**:
- ε ≈ median(C) / 10: good balance (approximates OT, stable gradients)
- ε → 0.001 × median(C): closer to exact OT but slower convergence
- Use log-domain Sinkhorn for ε < 0.01

---

## Pattern 2: Distributional Averaging (Wasserstein Barycenter)

**Context**: Average over a collection of distributions (histograms, images, word distributions).

**When to use**: Interpolating styles, averaging feature distributions, clustering prototypes.

**Algorithm selection**:
- Fixed support (same grid): Sinkhorn barycenter (fast, parallel)
- Free support (unknown locations): Alternating optimization over positions + weights
- High dimension: Sliced Wasserstein barycenter (1D projections + reconstruction)

**Template**:
```python
from ot.bregman import barycenter
bar = barycenter(A, C, reg=0.1, weights=lambda_weights)
```

---

## Pattern 3: Training with OT Loss (Generative Models)

**Context**: Train a model that produces samples from a target distribution.

**Choice of loss**:
- **WGAN**: Approximate W₁ with Lipschitz-constrained discriminator
  - Stable training, but requires gradient penalty or spectral norm
- **Sinkhorn loss**: Directly compute L^ε between generated and real batches
  - Differentiable via autograd; sensitive to ε choice
- **Sliced Wasserstein loss**: More stable for high-d; no discriminator needed

**Gradient computation**:
```python
# Sinkhorn autograd (PyTorch)
from geomloss import SamplesLoss
loss_fn = SamplesLoss("sinkhorn", p=2, blur=0.05)
loss = loss_fn(gen_samples, real_samples)
loss.backward()
```

---

## Pattern 4: Domain Adaptation via OT Transport Plan

**Context**: Transfer a model trained on source distribution to target distribution.

**Algorithm**:
1. Compute OT plan P between source samples X_s and target samples X_t
2. Apply Monge map (or barycentric projection): `T(x) = Σ_j P_{ij} x_j / P_i`
3. Train on transported features

**Code**:
```python
P = ot.emd(a, b, C)  # or ot.sinkhorn for regularized version
# Barycentric projection (soft assignment)
Xnew = (P @ Xt) / P.sum(axis=1, keepdims=True)
```

---

## Pattern 5: OT for Document/Text Comparison

**Context**: Compare documents represented as word frequency histograms.

**Word Mover's Distance (WMD)**:
- Histograms = normalized word frequency vectors
- Cost matrix = pairwise word embedding distances
- `WMD(d1, d2) = LC(bow1, bow2)` with `C_{ij} = ||emb_i - emb_j||`

**Scalable approximation**:
- Relaxed WMD: replace ground distance with cheaper approximation
- Sinkhorn WMD: regularized version, O(n²) but parallelizable

---

## Pattern 6: Sample Complexity-Aware OT

**Context**: You have limited samples (n small relative to dimension d).

**Rules**:
- If d ≥ 5 and n < 10000: exact W_p has O(n^{-2/d}) convergence → use Sinkhorn/sliced
- If n > 50000 and d moderate: mini-batch Sinkhorn with batch size B (biased but fast)
- **Debiasing**: always use Sinkhorn divergence (not raw L^ε) for unbiased estimates

**Mini-batch trick**:
```python
def minibatch_sinkhorn_loss(X, Y, batch_size=128, eps=0.1):
    idx_x = np.random.choice(len(X), batch_size)
    idx_y = np.random.choice(len(Y), batch_size)
    return sinkhorn_divergence(X[idx_x], Y[idx_y], eps)
```

---

## Pattern 7: Structural Comparison (Gromov-Wasserstein)

**Context**: Compare distributions on incompatible or different-dimensional spaces.

**Use cases**:
- Cross-lingual word embedding alignment
- Shape matching (meshes, point clouds) without registration
- Graph comparison
- Multi-omics biological data integration

**Practical notes**:
- Always use entropic GW (much faster)
- Initialize with uniform coupling (or heuristic like spectral matching)
- Check convergence with GW objective value
- For large n: use subsampling + refinement

---

## Pattern 8: Robust OT (Outlier Handling)

**Context**: One or both distributions contain outliers.

**Solutions**:
1. **Unbalanced OT**: KL marginal penalty λ controls outlier tolerance
   - Small λ: mass freely created/destroyed (tolerant)
   - Large λ: approaches standard OT (strict)
2. **Partial OT**: Transport only fraction m < 1 of mass
   - `PartialOT(a,b,C,m)`: minimize transport of m units

```python
# Unbalanced OT via POT
T = ot.unbalanced.sinkhorn_unbalanced(a, b, C, reg=0.1, reg_m=0.5)

# Partial OT
T = ot.partial.partial_wasserstein(a, b, C, m=0.7)
```

---

## Pattern 9: Gradient Flow / Sampling

**Context**: Generate samples from a distribution by gradient flow.

**Applications**: MCMC sampling, Langevin dynamics, particle-based VI.

**JKO stepping**:
```python
def jko_sampling_step(particles, target_log_prob, step_size, eps):
    """One JKO step for Langevin MCMC."""
    a = np.ones(len(particles)) / len(particles)
    # Compute OT to target-weighted version of particles
    log_weights = target_log_prob(particles)
    b = softmax(log_weights)
    C = pairwise_sq_dist(particles, particles)
    P = sinkhorn(a, b, C, eps)
    # Move particles toward weighted barycenter
    new_particles = (P / a[:, None]) @ particles * step_size + \
                    particles * (1 - step_size)
    return new_particles
```

---

## Anti-Pattern Catalog

| Anti-pattern | Problem | Fix |
|---|---|---|
| Naive Sinkhorn for small ε | Numerical overflow | Log-domain Sinkhorn |
| Using L^ε_C(a,b) as loss | Biased (L^ε(a,a)≠0) | Use Sinkhorn divergence |
| OT in R^d without approximation | O(n^{-1/d}) convergence | Sliced or entropic OT |
| KL when supports differ | KL = ∞ | Use W_p or MMD |
| WGAN without Lipschitz constraint | Training instability | Gradient penalty or SN |
| Ignoring mass normalization | OT undefined | Normalize, or use unbalanced OT |
| GW on aligned spaces | Unnecessary; slow | Use standard OT or Sinkhorn |
| Exact OT for gradient computation | Not differentiable | Entropic OT (ε > 0) |
