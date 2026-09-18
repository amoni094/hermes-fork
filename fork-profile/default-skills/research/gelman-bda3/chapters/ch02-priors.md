# BDA3 Chapter 2: Single-Parameter Models — Conjugate Priors & Beta-Binomial

## Source
Gelman, Carlin, Stern, Dunson, Vehtari, Rubin — *Bayesian Data Analysis*, 3rd ed., Ch. 2 (pp. 29–57).

---

## 2.1 Core Setup: Estimating a Probability from Binomial Data

**Model:** Observe y successes in n independent Bernoulli trials with unknown probability ω.

**Likelihood:**
```
p(y|ω) = C(n,y) · ω^y · (1-ω)^(n-y)
```
As a function of ω this is proportional to `ω^y · (1-ω)^(n-y)`.

**Bayes' Theorem (general form):**
```
p(ω|y) ∝ p(y|ω) · p(ω)
posterior ∝ likelihood × prior
```

---

## 2.4 Conjugate Prior: Beta-Binomial

### Key Insight
A prior is **conjugate** if the posterior is in the same family as the prior. For Binomial likelihood, the conjugate prior is the **Beta distribution**.

### Beta Prior
```
p(ω) ~ Beta(α, β)
p(ω) ∝ ω^(α-1) · (1-ω)^(β-1)
```
- α, β > 0 are *hyperparameters*
- Interpretation: α-1 prior successes, β-1 prior failures
- Special case: α=β=1 → Uniform prior (Laplace)

### Posterior Update (Beta-Binomial Conjugacy)
Given prior Beta(α, β) and data (y successes in n trials):
```
p(ω|y) ∝ ω^y · (1-ω)^(n-y) · ω^(α-1) · (1-ω)^(β-1)
        = ω^(α+y-1) · (1-ω)^(β+n-y-1)
        ~ Beta(α + y, β + n - y)
```

**Update rule** (BDA3 §2.4, p. 34-35):
```
If prior is Beta(α, β) and observe k successes in n trials:
  posterior = Beta(α + k, β + n - k)
```

### Posterior Summary Statistics
```
Posterior mean:    E[ω|y] = (α + y) / (α + β + n)
Posterior mode:    (α + y - 1) / (α + β + n - 2)   [for α+y,β+n-y > 1]
Posterior variance: (α+y)(β+n-y) / [(α+β+n)²(α+β+n+1)]
```

**Posterior mean as weighted compromise** (BDA3 §2.2):
```
E[ω|y] = (α+β)/(α+β+n) · α/(α+β)  +  n/(α+β+n) · y/n
        = prior_weight × prior_mean  +  data_weight × MLE
```
As n → ∞, posterior mean → MLE (y/n). Prior influence diminishes with data.

### Laplace's Law of Succession
With uniform prior (α=β=1) and y successes in n trials:
```
Pr(ỹ=1 | y) = E[ω|y] = (y+1)/(n+2)
```
Avoids probability-0 predictions at extremes.

---

## 2.3 Summarizing Posterior Inference

**Posterior intervals** (credible intervals): range containing 100(1-α)% of posterior probability.
- Central interval: α/2 probability in each tail
- HPD (Highest Posterior Density): smallest set containing specified probability mass

**Posterior quantiles** can be computed directly for Beta distribution from CDF.

---

## 2.8 Noninformative & Weakly Informative Priors

- **Uniform prior** (α=β=1): does not encode any prior belief; can be problematic at boundaries
- **Jeffreys prior for Binomial**: Beta(1/2, 1/2) — invariant under reparameterization
- **Weakly informative**: Beta(2,2) or Beta(2,8) — mild regularization toward plausible range

**Warning (BDA3 §2.8):** The "principle of insufficient reason" (uniform = ignorance) is not a general solution. Prior choice matters for small samples.

---

## 2.9 Sequential Updating

Bayesian updating is **sequential** — order of observations doesn't matter:
```
Observe k₁ successes in n₁, then k₂ successes in n₂:
  After batch 1: Beta(α + k₁, β + n₁ - k₁)
  After batch 2: Beta(α + k₁ + k₂, β + n₁ + n₂ - k₁ - k₂)
  = same as observing (k₁+k₂) successes in (n₁+n₂) total
```

---

## Hermes Application: Source Trust Modeling

Model each memory source's reliability as a Beta distribution:
```python
# Initial prior: Beta(2, 1) → prior mean = 2/3 ≈ 0.67 (slightly optimistic)
state[source] = {'alpha': 2.0, 'beta': 1.0}

# On successful recall (reward=1.0):
state[source]['alpha'] += 1.0

# On failed recall (reward=0.0):
state[source]['beta'] += 1.0

# Trust weight:
trust = alpha / (alpha + beta)   # posterior mean
```

**Why Beta(2,1)?**
- Prior mean = 2/3 ≈ 0.67 (reasonable starting trust)
- 3 pseudo-observations of experience → not too strong
- After 10 successes, 2 failures: Beta(12,3) → mean=0.80 ✓

**Conjugacy advantage:** No MCMC needed. O(1) update per recall event.
