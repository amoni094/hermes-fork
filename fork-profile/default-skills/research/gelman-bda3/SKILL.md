---
name: gelman-bda3
description: Use when applying Bayesian inference and calibration.
triggers:
  - bayesian inference
  - beta-binomial
  - conjugate prior
  - posterior predictive check
  - model checking
  - trust calibration
  - source reliability
  - BDA3
  - Gelman
tags: [bayesian, statistics, inference, calibration, priors, model-checking]
---

# Gelman BDA3 — Bayesian Data Analysis (3rd ed.)

**Source:** Gelman, Carlin, Stern, Dunson, Vehtari, Rubin (2013/2025 corrected)
**Focus chapters ingested:** Ch. 1–2 (fundamentals, single-parameter models), Ch. 6–7 (model checking, predictive accuracy)

## When to Load
- Updating beliefs from observations (any domain)
- Choosing or calibrating a prior distribution
- Checking whether a model fits observed data
- Computing source/signal trust weights from recall outcomes
- Comparing models via predictive accuracy (WAIC, LOO-CV)

## Core Principle

```
p(θ|y) ∝ p(y|θ) · p(θ)
posterior ∝ likelihood × prior
```

## Beta-Binomial Conjugate Update (Ch. 2)

**Setup:** Model a probability θ ∈ [0,1] (e.g., source reliability, recall hit rate).

```
Prior:     θ ~ Beta(α, β)
Observe:   k successes in n trials
Posterior: θ|data ~ Beta(α + k, β + n - k)

Posterior mean = (α + k) / (α + β + n)
```

**Update rule — one-liner:**
```python
# hit=1 (success), hit=0 (failure)
alpha += hit
beta  += (1 - hit)
trust  = alpha / (alpha + beta)   # posterior mean
```

**Standard Hermes starting prior:** Beta(2, 1) → initial trust = 0.67

## Posterior Predictive Check (Ch. 6)

```
Algorithm:
1. Draw θ^s ~ p(θ|y)           [S posterior samples]
2. Draw ỹ^s ~ p(y|θ^s)         [simulated replicate]
3. Compute T(ỹ^s) for each s
4. p_B = fraction(T(ỹ^s) ≥ T(y_obs))

Interpretation:
  p_B ∈ [0.05, 0.95] → model fits this aspect
  p_B < 0.05 or > 0.95 → model misspecified for this aspect
```

## Model Comparison (Ch. 7)

| Criterion | Use Case |
|-----------|----------|
| lppd | Quick in-sample fit (biased) |
| WAIC | Recommended: fully Bayesian, no MCMC |
| LOO-CV (PSIS) | Gold standard; use Vehtari et al. 2017 approximation |
| Bayes Factor | Sensitive to priors; avoid unless priors are well-calibrated |

## Hermes Applications

### 1. Source Trust (memory-provenance.py)
Model each memory source as Beta(α, β). Update after each recall:
```python
from memory_provenance import update_trust_posterior, get_trust_weight

update_trust_posterior('internal', reward=1.0)   # successful recall
update_trust_posterior('external', reward=0.0)   # failed/stale recall
trust = get_trust_weight('internal')              # posterior mean
```
State persists in `~/.hermes/cache/trust-posterior.json`.

### 2. Recall-Miss Logging (memory-ttl-purge.py)
Every TTL-purged fact is logged to `~/.hermes/cache/recall-misses.jsonl`.
These events contribute beta increments to the trust posterior.

### 3. Posterior Predictive Check on Recall
```python
# Is observed miss rate consistent with current Beta posterior?
import numpy as np
from scipy.stats import beta as BetaDist

alpha, beta_p = 7.0, 3.0   # current posterior
T_obs = 0.30               # observed miss rate in last 20 recalls
# Sample from posterior, compute expected miss rate
thetas = BetaDist.rvs(alpha, beta_p, size=10000)
miss_rates = 1.0 - thetas
p_B = np.mean(miss_rates >= T_obs)
# p_B < 0.05 → source is performing worse than model expects
```

## Linked Files

- `chapters/ch02-priors.md` — Beta-Binomial derivation, conjugacy, sequential updating
- `chapters/ch06-model-checking.md` — PPC algorithm, p-values, marginal checks, LOO-CV
- `cheatsheet.md` — Quick formulas, Python snippets, prior elicitation guide
- `glossary.md` — Definitions for all key terms

## Key References

- BDA3 §2.4 (p. 34-35): Beta-Binomial conjugacy derivation
- BDA3 §6.3 (p. 143-151): Posterior predictive checks, p-values
- BDA3 §7.1-7.2 (p. 165-175): lppd, WAIC, LOO-CV
- Vehtari, Gelman, Gabry (2017): Practical Bayesian model evaluation using LOO-CV
