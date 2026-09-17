# Chapter 20: An Example Inference Task: Clustering

## Core Idea
Clustering is Bayesian inference of labels and parameters, not a sequence of ad-hoc heuristics. Soft K-means (a limit of the Gaussian mixture EM) is the running example of Part IV: assign points to clusters with responsibilities, update means, iterate. Even this simple algorithm already shows phase transitions and the need for a proper probabilistic model.

## Frameworks Introduced
- **K-means**: assign each x to nearest mean m_k; replace m_k by the mean of its assigned points. Hard, Euclidean, assumes spherical equal-variance clusters.
- **Soft K-means**: responsibilities r_k(x) ∝ exp(−β ||x−m_k||² / 2), then m_k = sum_x r_k(x) x / sum r_k. Inverse-temperature β interpolates hard (β→∞) and uniform (β→0).
- **Generative model view**: data ~ mixture of Gaussians; clustering infers component parameters and latent labels (developed in Ch 22).

## Key Concepts
- **Responsibility** r_k(n): posterior P(cluster=k | x_n, means).
- **Lengthscale σ = β^{−1/2}**: clusters smaller than σ cannot be resolved; larger than σ split (bifurcation).
- **Pitchfork bifurcation**: with 1-D data of variance σ1², the m=0 fixed point is stable iff σ1² ≤ 1/β. When data is too spread (or β too large), two means fly apart. MacKay’s figs 20.9–20.11.
- **Initialization matters** for hard K-means; soft updates + annealing β can help.
- **K itself is a model-selection problem** (Ch 22, 28), not something K-means knows.

## Key Equations
- Hard assign: k(n) = argmin_k ||x_n − m_k||²
- Soft: r_k(n) = e^{−β d_k(n)/2} / sum_{k'} e^{−β d_{k'}(n)/2}
- Mean update: m_k = sum_n r_k(n) x_n / sum_n r_k(n)
- Stability of coincident means: σ_data² ≤ 1/β
- r_1(x) = 1 / (1 + exp(−2 β m x_1))  in the 1-D two-mean toy

## Algorithms and Techniques
**Soft K-means**
1. Choose K, β (or anneal β from small to large), init means.
2. E-like step: compute r_k(n) for all n,k.
3. M-like step: recompute m_k as weighted means.
4. Repeat until means move less than ε.
5. Optionally harden assignments at the end.

**Diagnosing K**
- If β is small, extra means collapse together (effective smaller K).
- If β is large, extra means park on outliers. Use evidence (Ch 22, 28), not training MSE.

## Mental Models
- Use hard K-means for a fast baseline when clusters are spherical, similar size, K known.
- Use soft/EM when you need responsibilities or overlapping clusters.
- Think of β as a resolution knob; there is a critical β where clusters “appear”.
- Clustering without a generative model cannot tell you K.

## Worked Example
1-D data, two means initialized at ±m, β fixed. Assignment to cluster 1:
r1(x) = 1 / (1+exp(−2β m x)).
Updated m' = σ1² β m for small m. If σ1² β < 1, m→0 (one cluster); if σ1² β > 1, m grows (two clusters). So you cannot split a clump tighter than the algorithm’s lengthscale — a feature, not a bug, if σ is a true noise scale; a bug if you just wanted K=2 always.

## Anti-patterns
- **Choosing K by looking at the plot until it “looks right”** without a penalty for extra means.
- **K-means on wildly different cluster scales / non-spherical shapes**.
- **Setting β=∞ from the start** (hard K-means) with poor init → empty clusters, bad local minima.
- **Interpreting collapsed means as “the algorithm failed”** — it may be correctly refusing to over-split.

## Key Takeaways
1. Clustering is inference of latents + parameters.
2. Soft K-means = fixed-variance Gaussian mixture EM.
3. A critical β / data-variance condition governs when clusters split.
4. K and σ are part of the model; they need Bayesian treatment later.
5. This chapter is the on-ramp to all of Part IV.

## Connects To
- **Ch 22**: true EM, covariance, ML vs Bayesian mixtures.
- **Ch 28**: choosing K by evidence.
- **Ch 31**: mean-field / Ising also has β-driven phase transitions.
- **Ch 3**: posterior widths vs point estimates, same moral.
