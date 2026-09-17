# BDA3 Glossary

## Core Terms

**Bayesian inference**: The process of updating a prior distribution P(θ) with observed data y
via Bayes' theorem to get a posterior distribution P(θ|y).

**Prior distribution** p(θ): Probability distribution encoding beliefs about parameter θ
*before* observing data. Can be:
- *Informative*: encodes substantive domain knowledge
- *Weakly informative*: mild regularization, broad support
- *Noninformative/reference*: minimal assumptions (e.g., Jeffreys prior)
- *Conjugate*: chosen so posterior is in same family

**Likelihood** p(y|θ): Probability of observed data as a function of parameter θ.
"The likelihood is not a probability distribution over θ — it does not integrate to 1 over θ."

**Posterior distribution** p(θ|y): Updated belief about θ after observing y.
```
p(θ|y) ∝ p(y|θ) · p(θ)
```

**Posterior predictive distribution** p(ỹ|y):
```
p(ỹ|y) = ∫ p(ỹ|θ) p(θ|y) dθ
```
Prediction for new data ỹ, averaging over posterior uncertainty in θ.

**Conjugate prior**: Prior from a family F such that if p(θ) ∈ F, then p(θ|y) ∈ F.
Closed-form posterior update; no numerical integration needed.

**Hyperparameters**: Parameters of the prior distribution (e.g., α, β in Beta(α,β)).
Distinguished from model parameters θ.

---

## Beta Distribution

**Beta(α, β)**: Distribution on [0,1] for probabilities/rates.
```
p(x) ∝ x^(α-1) · (1-x)^(β-1)
Mean = α/(α+β)
Mode = (α-1)/(α+β-2)   [for α,β > 1]
Var  = αβ / [(α+β)²(α+β+1)]
Concentration = α+β (larger → more concentrated)
```

**Effective sample size of Beta prior** ≈ α+β pseudo-observations.

---

## Posterior Predictive Checks

**Test quantity** T(y, θ): A scalar function measuring some aspect of data (possibly also
depending on θ). Examples: mean, variance, skewness, number of zero counts.

**Replicated data** y_rep: Data simulated from the model using posterior draws.
Different from "future data" — replicated under the same experimental conditions.

**Posterior predictive p-value**:
```
p_B = Pr(T(y_rep, θ) ≥ T(y_obs, θ) | y)
```
A posterior probability, not a classical p-value. Values near 0 or 1 indicate model misfit.

**Conservative p-values**: BDA3 notes that under a true model, p_B tends to be more
concentrated near 0.5 than U(0,1). This means: even p_B = 0.05 is meaningful evidence
of misfit, but do not expect 5% false-positive rate.

---

## Model Comparison

**lppd** (log pointwise predictive density): In-sample fit measure.
```
lppd = Σᵢ log p(yᵢ|y)  [overestimates out-of-sample fit]
```

**WAIC** (Widely Applicable Information Criterion): Bias-corrected estimate of elpd.
Preferred over DIC for hierarchical models.

**LOO-CV** (Leave-One-Out Cross-Validation): Gold standard predictive accuracy estimate.
Computationally expensive; PSIS-LOO approximation (Vehtari et al. 2017) is efficient.

**Bayes Factor**: Ratio of marginal likelihoods p(y|M₁)/p(y|M₂).
Sensitive to prior specification; use with care.

---

## Hermes-Specific Terms

**Recall hit**: A memory retrieval that returned a valid, non-stale fact. → alpha += 1

**Recall miss**: A memory retrieval that returned nothing, a stale fact, or purged entry. → beta += 1

**Trust posterior**: Beta(alpha, beta) maintained per source in trust-posterior.json.
Updated online after each recall event.

**Source**: Classification of memory origin: 'internal' (Hermes DB), 'cron' (scheduled),
'external' (web/API). Each gets its own Beta posterior.

**Recall-miss log**: JSONL file recording each purged/expired/missed fact with timestamp,
fact label, TTL reason, and fact_type. Used for offline calibration and elpd estimation.
