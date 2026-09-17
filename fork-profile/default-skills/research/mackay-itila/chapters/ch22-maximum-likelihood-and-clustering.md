# Chapter 22: Maximum Likelihood and Clustering

## Core Idea
Maximum-likelihood fitting of a mixture is the EM algorithm: soft K-means with learned weights and covariances. ML *overfits* — extra clusters always raise likelihood — so ML cannot choose K. MacKay uses this as the cautionary midpoint between ad-hoc K-means and Bayesian evidence.

## Frameworks Introduced
- **Gaussian mixture model (GMM)**
  P(x|θ) = sum_{k=1}^K π_k Normal(x; m_k, Σ_k)
- **EM for mixtures**
  - E: r_k(n) = P(k|x_n,θ)
  - M: π_k, m_k, Σ_k = weighted frequency, mean, covariance
- **Incomplete data likelihood**: observed-data log-likelihood ℓ(θ)=sum_n log sum_k π_k N(x_n;m_k,Σ_k). Latent labels z_n make it “complete”.
- **Why EM works**: Jensen’s inequality / Gibbs (Ch 2) — the free-energy bound on ℓ increases each step.

## Key Concepts
- **Identifiability / label switching**: permuting cluster indices does not change P(x).
- **Singularities of ML**: a component with Σ→0 parked on one point sends ℓ→∞. ML is ill-posed without constraints or priors.
- **K cannot be chosen by ML**: ℓ is nondecreasing in K.
- **Soft K-means recovered**: if π_k=1/K and Σ_k=σ² I fixed, EM = Ch 20.
- **Responsibilities** as posterior label probabilities, not “fuzzy memberships” from nowhere.

## Key Equations
- r_k(n) = π_k N(x_n; m_k, Σ_k) / sum_{k'} π_{k'} N(x_n; m_{k'}, Σ_{k'})
- π_k ← N_k / N,  N_k = sum_n r_k(n)
- m_k ← sum_n r_k(n) x_n / N_k
- Σ_k ← sum_n r_k(n) (x_n−m_k)(x_n−m_k)^T / N_k
- ℓ(θ) = sum_n log sum_k π_k N(x_n;…)
- Each EM step: ℓ(θ^{new}) ≥ ℓ(θ^{old})

## Algorithms and Techniques
**EM for GMMs**
1. Init π, m, Σ (e.g. from a few K-means steps).
2. Repeat E and M until ℓ plateaus.
3. Constrain Σ (shared covariance, min eigenvalue, or a prior) to avoid collapse.
4. Multiple random restarts; take the highest ℓ (still not a reason to pick large K).

**Free-energy derivation (preview of Ch 33)**
1. Introduce q(z) over labels.
2. ℓ = F(q,θ) + DKL(q || p(z|x,θ)), F = E_q[log p(x,z|θ)] + H(q).
3. E-step: q ← p(z|x,θ) makes DKL=0.
4. M-step: maximize F w.r.t. θ, equivalent to complete-data ML with weights r.

## Mental Models
- EM is coordinate ascent on a lower bound of ℓ, not magic.
- Use ML-EM to *fit* a mixture when K is known and you regularize Σ.
- Never use ℓ to choose K; use evidence / cross-validation / BIC as cheap proxies (Ch 28).
- A collapsing component is ML telling you it found a Dirac that explains one point perfectly — the prior should have forbidden it.

## Worked Example
Two well-separated 2-D blobs, K=2: EM recovers means and π≈0.5, ℓ high. Fit K=20: several Σ_k → 0 on single points, ℓ larger than the K=2 fit, predictive density *worse* on held-out data. That plot is the whole argument for Bayesian model comparison.

Soft K-means: freeze Σ=I/β and equal π; EM’s M-step is exactly the Ch 20 mean update.

## Anti-patterns
- **Choosing K to maximize training likelihood**.
- **Unconstrained per-cluster full Σ in high-D** (p>>N_k).
- **One EM run from a bad init** (local maxima).
- **Interpreting a tiny cluster on an outlier as a “discovery”**.

## Key Takeaways
1. Mixture ML = EM with responsibilities.
2. Likelihood always wants more clusters and thinner Gaussians.
3. Regularize or go Bayesian.
4. EM monotonically increases ℓ; it does not find the global max.
5. Soft K-means is EM with tied isotropic variances.

## Connects To
- **Ch 2.7 / 33**: Jensen / variational free energy is EM’s proof.
- **Ch 20**: the algorithm without covariances.
- **Ch 23**: Dirichlet priors on π, Wishart on Σ.
- **Ch 28**: evidence for K.
- **Ch 34**: ICA as a different latent-variable model.
