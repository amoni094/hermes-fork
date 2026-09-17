# BDA3 Cheatsheet — Quick Reference

## Bayes' Theorem
```
p(θ|y) = p(y|θ) · p(θ) / p(y)
       ∝ p(y|θ) · p(θ)

posterior ∝ likelihood × prior
```

## Beta-Binomial Conjugate Model

| Quantity | Formula |
|----------|---------|
| Prior | Beta(α, β) |
| Likelihood | Binomial(n, θ): observe k successes |
| Posterior | Beta(α+k, β+n-k) |
| Posterior mean | (α+k) / (α+β+n) |
| Posterior mode | (α+k-1) / (α+β+n-2) |
| Posterior variance | (α+k)(β+n-k) / [(α+β+n)²(α+β+n+1)] |
| 95% credible interval | Use Beta.ppf(0.025, α+k, β+n-k) to Beta.ppf(0.975, α+k, β+n-k) |

## Common Conjugate Pairs

| Likelihood | Conjugate Prior | Posterior |
|-----------|----------------|-----------|
| Binomial(n,θ) | Beta(α,β) | Beta(α+k, β+n-k) |
| Poisson(λ) | Gamma(α,β) | Gamma(α+Σy, β+n) |
| Normal(μ,σ²known) | Normal(μ₀,τ₀²) | Normal(weighted avg) |
| Normal(μ,σ²) | Normal-InvChi² | Normal-InvChi² |
| Multinomial | Dirichlet(α) | Dirichlet(α+counts) |

## Posterior Predictive Check

```
Step 1: Draw θ^s ~ p(θ|y)  [S posterior samples]
Step 2: Draw ỹ^s ~ p(y|θ^s)  [replicated data]
Step 3: Compute T(ỹ^s) for each s
Step 4: p_B = fraction of s where T(ỹ^s) ≥ T(y_obs)

Interpretation:
  p_B ∈ [0.05, 0.95] → model fits this aspect
  p_B < 0.05 or > 0.95 → model fails
```

## Model Comparison Criteria

| Criterion | Formula | Notes |
|-----------|---------|-------|
| lppd | Σᵢ log p(yᵢ|y) | In-sample; overestimates |
| WAIC | -2·lppd + 2·Σᵢ var[log p(yᵢ|θ)] | Fully Bayesian |
| LOO-CV | Σᵢ log p(yᵢ|y₋ᵢ) | Gold standard |
| Bayes Factor | p(y|M₁)/p(y|M₂) | Sensitive to priors |

## Key Python Snippets

```python
from scipy.stats import beta as Beta

# Beta-Binomial update
def update_beta(alpha, beta_param, k, n):
    return alpha + k, beta_param + n - k

# Posterior mean
def posterior_mean(alpha, beta_param):
    return alpha / (alpha + beta_param)

# 95% credible interval
def credible_interval(alpha, beta_param, ci=0.95):
    lo = (1 - ci) / 2
    hi = 1 - lo
    return Beta.ppf(lo, alpha, beta_param), Beta.ppf(hi, alpha, beta_param)

# Posterior predictive p-value (discrete)
def ppc_pvalue(T_obs, T_rep_samples):
    return sum(t >= T_obs for t in T_rep_samples) / len(T_rep_samples)
```

## Hermes Trust Posterior (quick reference)

```python
# Initial prior: Beta(2, 1) → prior mean = 0.667
# Recall hit  → alpha += 1
# Recall miss → beta  += 1
# Trust weight = alpha / (alpha + beta)

# Example trajectory:
# Start:        Beta(2,1)   → trust=0.667
# After 5 hits: Beta(7,1)   → trust=0.875
# After 2 miss: Beta(7,3)   → trust=0.700
# After 20hits: Beta(27,3)  → trust=0.900
```

## Prior Elicitation Guide

| Belief | Prior | Mean | Concentration |
|--------|-------|------|--------------|
| No knowledge | Beta(1,1) | 0.50 | Uniform |
| Slightly optimistic | Beta(2,1) | 0.67 | Weak |
| Moderately reliable | Beta(5,2) | 0.71 | Moderate |
| Highly reliable | Beta(9,1) | 0.90 | Strong |
| Known unreliable | Beta(1,4) | 0.20 | Moderate |

## Decision Rule for Hermes

```
trust = posterior_mean(alpha, beta)
if trust >= 0.80:   use source with full weight
if trust >= 0.60:   use source with discounting
if trust < 0.60:    flag for review; use static fallback weight
```
