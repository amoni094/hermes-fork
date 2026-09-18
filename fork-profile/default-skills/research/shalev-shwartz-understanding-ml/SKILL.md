---
name: shalev-shwartz-understanding-ml
description: Use when applying online learning and PAC bounds.
category: research
tags: [machine-learning, pac-learning, online-learning, ftrl, regularization, sgd]
source: "Understanding Machine Learning by Shalev-Shwartz & Ben-David (Cambridge 2014)"
---

# Understanding Machine Learning — Shalev-Shwartz & Ben-David

Core reference for PAC learning theory, online learning, FTRL, regularization, and SGD — with direct Hermes applications for routing, calibration, and recall quality.

## Hermes Applications

| Framework | Hermes Use Case |
|-----------|----------------|
| PAC sample complexity | Required examples to trust a recall quality estimate |
| Online learning / FTRL | Adapt `memory-query-router.py` route weights over time |
| Regret bounds | Bound calibration drift across routing decisions |
| Tikhonov regularization | Stabilize calibration threshold updates |
| SGD | Incremental weight updates in routing calibration loop |

## Chapter Files

- `chapters/ch02-pac-learning.md` — PAC model, ERM, finite/infinite hypothesis classes
- `chapters/ch11-online-ftrl.md` — Online convex optimization, FTRL, regret bounds, OGD
- `cheatsheet.md` — Quick-reference formulas
- `glossary.md` — Key terms

## Quick Formulas

### PAC Sample Complexity (agnostic, VC-dimension d)
```
m >= (1/eps^2) * (d * ln(1/eps) + ln(1/delta))
```
For realizable case with finite class |H|:
```
m >= (1/eps) * (ln|H| + ln(1/delta))
```

### Online Regret (definition)
```
Regret_A(w*, T) = sum_{t=1}^T l_t(w_t) - sum_{t=1}^T l_t(w*)
```

### FTRL Update Rule
```
w_{t+1} = argmin_w [ sum_{s=1}^t l_s(w) + R(w) ]
```
where R(w) is the regularizer (e.g., 0.5*||w||^2 for L2).

### FTRL / OGD Regret Bound
With eta = B/(rho*sqrt(T)), B-bounded domain, rho-Lipschitz losses:
```
Regret_A(H, T) <= B*rho*sqrt(T)   i.e., O(sqrt(T))
```

### Tikhonov (Ridge) Regularization
```
A(S) = argmin_w [ L_S(w) + lambda*||w||^2 ]
```
Stability rate: on-average-replace-one-stable with rate `2*rho^2/(lambda*m)`

### SGD Update
```
w^{t+1} = w^t - eta * grad_f(w^t)   or   w^t - eta * v_t (stochastic)
```
Convergence: E[f(w_bar)] - f(w*) <= B*rho/sqrt(T) with eta = B/(rho*sqrt(T))

## Usage Notes

- **FTRL in Hermes**: The `_log_routing_decision()` hook in `memory-query-router.py` records (ts, route, qhash, result_count). Aggregate 50+ entries and run gradient update on route priors.
- **Regret interpretation**: If routing has high regret vs. an oracle, the route weights are miscalibrated — apply a single FTRL step.
- **Calibration drift check**: `consistency_scorer.py` runs a drift check on the last 50 calibration entries. Mean predicted confidence outside [0.3, 0.7] signals drift — apply lambda regularization to the threshold.
- **Sample complexity sanity check**: Before trusting any recall quality estimate, ensure you have m >= (1/eps^2) * (d*ln(1/eps) + ln(1/delta)) samples.