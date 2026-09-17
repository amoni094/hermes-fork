# Chapter 9 — Variational Wasserstein Problems

## Core Idea
Use Wasserstein distances as loss functions for optimization problems over probability distributions. Three main applications: (1) Wasserstein barycenters (averaging distributions), (2) gradient flows in Wasserstein space (continuous-time optimization), (3) minimum Kantorovich estimators (fitting generative models). The entropic regularization makes all these differentiable.

## Frameworks Introduced

### 9.1 Differentiating the Wasserstein Loss
**Problem**: min_θ E(θ) = Lc(α_θ, β)

**Proposition 9.1** (Eulerian): `∇L^ε_C(a,b) = (f⋆, g⋆)` — dual potentials from Sinkhorn.

**Eulerian discretization** (fixed grid locations, optimize weights):
```
∇E_E(θ) = [∂a(θ)]^T f    where f = dual potential from Sinkhorn
```

**Lagrangian discretization** (fixed uniform weights, optimize positions):
```
∇E_L(θ) = n^{-1} Σ_i ∂T_θ(z_i)^T ∇₁c(T_θ(z_i), y_j*)
```
where j* = assigned target of sample i.

### 9.2 Wasserstein Barycenters

**Definition**: `min_α Σ_s λ_s W₂²(α, α_s)` (Fréchet mean in W₂ geometry)

**Algorithm (Sinkhorn barycenters)**:
```
Initialize: α (uniform)
Iterate:
  For each s: compute Sinkhorn plan P_s between α and α_s
  Update: log α ← Σ_s λ_s log(v_s) + const
    where v_s are Sinkhorn scalings
```

**Free-support barycenters** (Lagrangian): optimize positions of support points.

**Dictionary learning**: represent measures as barycenters of K atoms `α_θ = Σ_k θ_k α_k`.

**Applications**:
- Color palette interpolation
- Shape morphing
- Topic model averaging
- Distribution clustering (K-Wasserstein-means)

### 9.3 Gradient Flows
**Wasserstein gradient flow**: continuous-time optimization where each step = OT to "natural direction":
```
∂αₜ/∂t = -∇_W E(αₜ)
```
**JKO scheme** (Jordan-Kinderlehrer-Otto):
```
α_{k+1} = argmin_α [E(α) + W₂²(α, α_k) / (2τ)]
```
- Each step = proximal point in W₂ metric
- τ → 0 limit gives continuous gradient flow
- Applications: Langevin dynamics, KL divergence minimization, sampling

### 9.4 Minimum Kantorovich Estimators
**Problem**: fit generative model h_θ: Z → X (push-forward of noise) to target β:
```
min_θ Lc(h_{θ,#}ζ, β)
```
**Key**: generative model → samples, but not densities — W_p can handle this!

**Gradient** (primal coupling form):
```
∇E(θ) = n^{-1} Σ_i [∂h_θ(z_i)]^T ∇₁c(h_θ(z_i), x_{j*(i)})
```
where j*(i) = OT-assigned target for sample i.

**Connection to GANs**:
- WGAN: discriminator approximates W₁ dual (Lipschitz-1 witness)
- WAE: encoder push-forward + decoder reconstruction
- Sinkhorn GAN: use Sinkhorn divergence as generator loss

## Key Concepts
- **Eulerian vs Lagrangian**: optimize weights on fixed grid vs optimize support point positions
- **Wasserstein gradient**: natural gradient respecting transport geometry (not L²)
- **JKO scheme**: implicit Euler time stepping in Wasserstein space
- **Free support**: barycenter with unknown support positions (harder but more expressive)
- **WGAN**: uses W₁ dual as adversarial loss (more stable than f-GAN with KL)

## Mental Models
- Barycenter = "average shape" of a collection of distributions
- Wasserstein gradient flow = steepest descent path in the space of probability measures
- MKE = maximum likelihood estimation where model outputs samples, not densities
- WGAN discriminator = dual potential estimator trained to approximate OT

## Anti-patterns
- Using exact (non-regularized) OT for gradient computation (not differentiable)
- Forgetting mass conservation in Eulerian gradient: use zero-mean centered potentials
- Training WGAN without Lipschitz constraint (gradient explodes)
- Using Wasserstein loss for very high-dimensional data without slicing (see Ch 10)

## Code Examples
```python
import numpy as np
import ot  # POT library

# Wasserstein barycenter (discrete, Sinkhorn)
def wasserstein_barycenter(distributions, weights, C, eps=0.1, n_iter=100):
    """Compute Wasserstein barycenter of a set of distributions.
    
    Args:
        distributions: list of histograms [(a_s, n_s), ...]  (same n)
        weights: λ_s ≥ 0, Σλ_s = 1
        C: n×n cost matrix (shared support)
    """
    n = len(distributions[0])
    # Use POT's fixed-point barycenter
    A = np.column_stack(distributions)  # n × S
    return ot.bregman.barycenter(A, C, eps, weights=weights, numItermax=n_iter)

# JKO step for KL gradient flow
def jko_kl_step(alpha, log_target, C, eps, tau, n_iter=50):
    """One JKO step: proximal of KL divergence in W₂."""
    n = len(alpha)
    # Solve: min_β KL(β || π) + W₂²(β, α) / (2τ)
    # Sinkhorn barycenter of [α, π] with weights [1/(2τ), 1] normalized
    target = np.exp(log_target)
    target /= target.sum()
    return wasserstein_barycenter(
        [alpha, target],
        weights=[1.0 / (1 + 2*tau), 2*tau / (1 + 2*tau)],
        C=C, eps=eps
    )

# Sinkhorn loss gradient (for generative model training)
def sinkhorn_loss_gradient(gen_samples, target_samples, eps=0.1):
    """Gradient of Sinkhorn loss w.r.t. generated sample positions."""
    n = len(gen_samples)
    m = len(target_samples)
    a = np.ones(n) / n
    b = np.ones(m) / m
    C = np.sum((gen_samples[:, None] - target_samples[None])**2, axis=-1)
    
    # Run Sinkhorn, get dual potentials
    f, g, log = ot.sinkhorn(a, b, C, eps, log=True)
    
    # Gradient: ∂L/∂x_i = (2/n) Σ_j P_{ij} (x_i - y_j)
    K = np.exp((f[:, None] + g[None, :] - C) / eps) * (a[:, None] * b[None, :])
    K /= K.sum()
    grad = 2 * np.sum(K[:, :, None] * (gen_samples[:, None] - target_samples[None]), axis=1)
    return grad

# K-Wasserstein means clustering
def wasserstein_k_means(distributions, K, C, eps=0.1, n_iter=20):
    """Cluster distributions using Wasserstein distance."""
    n_dist = len(distributions)
    # Initialize with random centroids
    centroids = [distributions[i] for i in np.random.choice(n_dist, K, replace=False)]
    
    for _ in range(n_iter):
        # Assign each distribution to nearest centroid
        W = np.array([[ot.sinkhorn2(d, c, C, eps) 
                       for c in centroids] 
                      for d in distributions])
        assignments = np.argmin(W, axis=1)
        
        # Update centroids as barycenters
        for k in range(K):
            cluster = [distributions[i] for i in np.where(assignments == k)[0]]
            if cluster:
                weights = np.ones(len(cluster)) / len(cluster)
                centroids[k] = wasserstein_barycenter(cluster, weights, C, eps)
    
    return centroids, assignments
```

## Reference Tables

| Problem | Loss | Algorithm | Gradient |
|---|---|---|---|
| Barycenter | Σλ_s W²(α,α_s) | Fixed-point Sinkhorn | v_s scalings |
| Generative fit | W²(h_θ#ζ, β) | Sinkhorn + autograd | OT coupling gradient |
| Gradient flow | E(α) | JKO (proximal) | Natural gradient |
| Clustering | Σ_i W²(α_i, c_{k(i)}) | W-k-means | As above |

## Worked Example
**Barycenter of 2 Gaussians** (1D, continuous):
- α₁ = N(0,1), α₂ = N(4,1), λ = [0.5, 0.5]
- W₂ barycenter = N(2, 1) (midpoint of means, same variance)
- Verification: W₂²(N(2,1), N(0,1)) = 4 = W₂²(N(2,1), N(4,1)) ✓

## Key Takeaways
1. Gradient of entropic OT = dual potentials (f,g) from Sinkhorn — plug directly into autograd
2. Barycenters generalize Euclidean averages to distribution space (Fréchet mean in W₂)
3. JKO = natural "proximal gradient" stepping for distributions evolving in Wasserstein space
4. Minimum Kantorovich estimators work for generative models without density access
5. WGAN = discriminative MKE: train discriminator as dual potential approximation

## Connects To
- Ch 4: entropic OT provides the differentiable loss used throughout this chapter
- Ch 5: semidiscrete OT for continuous generative model fitting
- Ch 8: comparison of loss functions; Sinkhorn divergence preferred for high-d
- Ch 10: sliced Wasserstein for practical high-dimensional barycenter computation
