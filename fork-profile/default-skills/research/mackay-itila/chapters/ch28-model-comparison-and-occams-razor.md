# Chapter 28: Model Comparison and Occam’s Razor

## Core Idea
Bayesian evidence P(D|H) automatically penalizes models that could have explained too many other datasets. The Occam factor is the ratio of the posterior volume to the prior volume. More parameters are allowed only when they pay for themselves in likelihood. This is MacKay’s distinctive pedagogical flag.

## Frameworks Introduced
- **Two-level inference**
  - Level 1: P(θ|D,H) ∝ P(D|θ,H) P(θ|H)
  - Level 2: P(H|D) ∝ P(D|H) P(H),  P(D|H)=∫ P(D|θ,H)P(θ|H)dθ
- **Occam factor**: P(D|H) ≈ P(D|θ̂,H) × (Δθ_posterior / Δθ_prior)
- **Evidence framework** for choosing: K in clustering, hidden units, regularization constants α (Ch 41), kernel hyperparameters (Ch 45).
- **Visual**: a simple model’s P(D|H) is a high, narrow distribution over datasets; a complex model’s is a low, wide one. Observed D in the overlapping region may favour the simple model.

## Key Concepts
- **Overfitting as wasted prior mass**: the complex model assigned probability to wild datasets that did not occur.
- **BIC** (crude Laplace): log P(D|H) ≈ ℓ(θ̂) − (k/2) log N. Use as a cheap check, not as Bayes.
- **Nested models**: if H0 ⊂ H1, evidence still can prefer H0; likelihood never does.
- **Hyperpriors**: even “the prior width α” is a model parameter with its own evidence (type-II ML / empirical Bayes — MacKay uses this heavily for neural nets).
- **Proper priors required**: otherwise P(D|H) is defined only up to an arbitrary constant and model comparison is meaningless.

## Key Equations
- P(D|H) = ∫ P(D|θ,H) P(θ|H) dθ
- Laplace: log P(D|H) ≈ log P(D|θ̂) + log P(θ̂) + (k/2) log 2π − ½ log det A
- Occam factor ≈ (2π)^{k/2} (det A)^{−1/2} / prior-volume
- BIC: ℓ − (k/2) log N
- Bayes factor B_{12} = P(D|H1)/P(D|H2)

## Algorithms and Techniques
**Compare two parametric models**
1. Put proper priors on both (same units; be honest about plausibility).
2. Find modes, Hessians, Laplace evidences (or MCMC harmonic mean *carefully*, or annealed importance sampling).
3. Report log Bayes factor and sensitivity to prior widths.
4. If H is discrete and small (K=1..6 clusters), compute all and plot log evidence vs K — typically a peak.

**Choose a regularization constant α**
1. Treat α as a hyperparameter.
2. Maximize P(D|α) ≈ Laplace evidence as a function of α (MacKay evidence iteration).
3. That α is not “CV’s twin” always, but often close.

## Mental Models
- A model is a *predictive distribution over datasets*, not a story about parameters.
- Use evidence to choose K, architecture, kernel, α — not training error, not ML.
- Think of the bent coin (Ch 3): H_fair vs H_bent, evidence 2^{−N} vs 1/(N+1).

## Worked Example
Polynomials of degree k fitting N noisy points.
- Degree 0: high Occam factor (tiny parameter volume used), poor ℓ.
- Degree N−1: interpolates, ℓ huge, Occam factor tiny (k≈N well-determined coefficients each eating 1/√N volumes… actually worse).
- Evidence peaks at the degree matching the true smoothness. Training RMSE keeps decreasing — do not use it.

Mixtures: log evidence vs K usually rises then falls; ML ℓ never falls (Ch 22).

## Anti-patterns
- **Comparing MAP likelihoods of different k**.
- **Improper priors** (“flat on ℝ^k”) in Bayes factors.
- **Ignoring prior sensitivity**: a 10× wider prior on extra parameters changes the Occam factor by 10^k.
- **Using BIC as if it were the evidence** for small N or non-iid models.
- **Harmonic-mean MCMC estimator** of evidence (notoriously unstable) without diagnostics.

## Key Takeaways
1. Evidence = best-fit likelihood × Occam factor.
2. Occam factor = posterior volume / prior volume.
3. More data shrinks posterior volume and can justify more parameters.
4. Model comparison needs proper priors and the integral, not the peak.
5. This chapter is the Bayesian answer to “how many clusters / hidden units / coefficients?”.

## Connects To
- **Ch 3**: first Occam example.
- **Ch 22**: ML cannot choose K.
- **Ch 27**: the integral’s Gaussian approximation.
- **Ch 41, 45**: evidence for neural nets and GP hyperparameters.
- **Ch 6**: compression length ≈ −log P(D|H) (MDL kinship).
