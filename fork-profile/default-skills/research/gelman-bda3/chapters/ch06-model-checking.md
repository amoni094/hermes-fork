# BDA3 Chapters 6–7: Model Checking & Posterior Predictive Checks

## Source
Gelman et al., *Bayesian Data Analysis* 3rd ed., Ch. 6 (pp. 141–162) and Ch. 7 (pp. 163–202).

---

## Chapter 6: Model Checking

### 6.1 The Place of Model Checking

Model checking is **not** about accepting or rejecting a model — "the relevant goal is not
to answer 'Do the data come from the assumed model?' (to which the answer is almost always no),
but to quantify the discrepancies between data and model, and assess whether they could have
arisen by chance under the model's own assumptions." (BDA3 p. 151)

Three-step workflow:
1. Fit the model
2. Summarize inferences
3. **Evaluate model fit** via posterior predictive checks → if poor, revise and iterate

### 6.3 Posterior Predictive Checking

**Core idea:** If the model is good, data generated from it should look like the real data.

**Posterior predictive distribution:**
```
p(ỹ | y) = ∫ p(ỹ | θ) · p(θ | y) dθ
```
= marginalizing the likelihood over the posterior.

**Algorithm:**
1. Draw S samples θ^s from posterior p(θ|y)
2. For each θ^s, simulate ỹ^s ~ p(y | θ^s)
3. {ỹ^s} is a sample from the posterior predictive distribution

**Posterior predictive p-value:**
```
p_B = Pr(T(y_rep) ≥ T(y) | y)
    = (1/S) Σ_s I[T(ỹ^s) ≥ T(y)]
```
where T(·) is a **test quantity** (discrepancy measure).

**Interpretation:**
- p_B ≈ 0.5: model fits this aspect of the data
- p_B < 0.05 or > 0.95: model fails this aspect
- These are **posterior probabilities**, not classical p-values (not uniform under H₀)
- The distribution of p_B under a true model is more concentrated near 0.5 than Uniform(0,1)

### Test Quantities / Discrepancy Measures

A test quantity T(y, θ) can depend on both data and parameters. Examples:
- T = sample mean (checks location)
- T = sample variance (checks spread)
- T = minimum/maximum (checks tails)
- T = number of sign changes (checks time-series autocorrelation)
- T = skewness, kurtosis

For Hermes: test quantity = recall success rate over a rolling window.

### 6.4 Graphical Posterior Predictive Checks

Display observed data alongside replicated datasets:
- Direct overlay plots
- Summary statistic distributions
- Residual plots

"If we are planning to apply the model, we might be interested in those aspects of the data
that do not appear typical." (BDA3 p. 150)

### Marginal Predictive Checks
```
p_i = Pr(y_rep_i ≤ y_i | y)
```
- Values near 0.5 → data not surprising
- Values near 0 or 1 → potential outlier or model misspecification

Conditional Predictive Ordinate (CPO):
```
CPO_i = p(y_i | y_{-i})
```
Low CPO → unusual observation; useful for outlier detection.

---

## Chapter 7: Evaluating, Comparing, and Expanding Models

### 7.1 Measures of Predictive Accuracy

**Log pointwise predictive density (lppd):**
```
lppd = Σ_i log p(y_i | y)
     = Σ_i log [ (1/S) Σ_s p(y_i | θ^s) ]
```
Higher lppd = better predictive fit.

**Expected log predictive density (elpd):**
```
elpd = Σ_i E_f[log p_post(ỹ_i)]
```
where expectation is over true data-generating distribution f (unknown; must be estimated).

**Key insight:** lppd on training data *overestimates* elpd for new data (overfitting).

### 7.2 Information Criteria and Cross-Validation

Corrections for overfitting:
- **AIC:** -2 lppd + 2k (frequentist; assumes flat priors, large n)
- **DIC:** -2 lppd + 2 p_DIC (uses posterior mean; problematic for hierarchical models)
- **WAIC:** -2 lppd + 2 p_WAIC (Widely Applicable; fully Bayesian; recommended)
- **LOO-CV:** Leave-one-out cross-validation (gold standard but expensive; PSIS-LOO approximation available)

**WAIC penalty term:**
```
p_WAIC = Σ_i var_posterior[log p(y_i | θ)]
```

### 7.3 Model Comparison

- **Bayes factor:** B₁₂ = p(y|M₁) / p(y|M₂) — ratio of marginal likelihoods
- Requires proper priors; sensitive to prior specification
- Prefer LOO-CV or WAIC for practical model comparison

### 7.6 Robustness Checks

Always check sensitivity to:
1. Prior specification (prior sensitivity analysis)
2. Likelihood assumption (e.g., normal vs. t)
3. Data coding and outlier influence

---

## Hermes Applications

### Memory Recall as a Posterior Predictive Check

Each recall attempt is a "replicated observation":
```
T(y_obs) = observed recall success rate over last N attempts
T(y_rep) = expected recall rate under current Beta(α,β) posterior

p_B = Pr(T(y_rep) ≥ T(y_obs) | α, β)
```
If p_B < 0.05: source is underperforming → downweight or flag for review.

### TTL Purge as Model Revision

When a fact expires and is purged:
- This is evidence against the "fact is still valid" model
- Log as a recall-miss for downstream elpd estimation
- Accumulated recall-misses → recalibrate Beta prior for that source/fact_type

### LOO-CV for Memory Source Selection

Compare sources by LOO predictive accuracy:
```
elpd_loo = Σ_i log p(y_i | y_{-i})
```
Sources with better LOO scores should receive higher trust weights.

### Model Checking Checklist for Hermes Memory
1. ✓ Plot recall success rate over time — check for trends (seasonality, drift)
2. ✓ Check distribution of time-to-expiry vs. expected TTL
3. ✓ Compute p_B for each source: does observed miss rate match Beta posterior?
4. ✓ Flag sources with p_B < 0.05 as unreliable
5. ✓ Run posterior predictive check monthly — update priors if systematic drift detected
