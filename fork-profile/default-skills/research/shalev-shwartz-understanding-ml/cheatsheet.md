# Cheatsheet — Understanding Machine Learning (Shalev-Shwartz & Ben-David)

## PAC Learning

| Bound | Formula |
|-------|---------|
| Finite H, realizable | m ≥ (1/ε)(ln\|H\| + ln(1/δ)) |
| Agnostic, finite H | m ≥ (1/(2ε²))·ln(2\|H\|/δ) |
| Agnostic, VC dim d | m ≥ (1/ε²)·(d·ln(1/ε) + ln(1/δ)) |
| VC dim halfspaces R^d | VCdim = d+1 |
| VC dim threshold R | VCdim = 1 |

## Online Learning

| Concept | Formula |
|---------|---------|
| Regret definition | R_A(w*,T) = Σℓ_t(w_t) - Σℓ_t(w*) |
| Weighted Majority bound | E[mistakes] - best_h ≤ 2√(log\|H\|·T) |
| OGD regret bound (Lipschitz ρ, B-bounded) | R ≤ B·ρ·√T = O(√T) |
| OGD step size | η = B/(ρ·√T) |
| FTRL update | w_{t+1} = argmin_w [Σℓ_s(w) + R(w)] |
| FTRL regret (L2 reg, η fixed) | R ≤ \|\|w*\|\|²/(2η) + η·T·ρ²/2 |
| Perceptron mistake bound | mistakes ≤ (ρ/γ)² |

## Regularization & Stability (Ch 13)

| Concept | Formula |
|---------|---------|
| RLM rule | A(S) = argmin_w [L_S(w) + λ‖w‖²] |
| Stability rate (Lipschitz loss ρ, reg λ) | E[L_D - L_S] ≤ 2ρ²/(λm) |
| Strong convexity | f(αu+(1-α)v) ≤ αf(u)+(1-α)f(v) - (μ/2)α(1-α)‖u-v‖² |
| f(w) = ‖w‖² is 2-strongly convex | By Lemma 13.5 |
| Fitting-stability tradeoff | Small λ → fits well, less stable; large λ → more stable, less fitting |

## SGD (Ch 14)

| Concept | Formula |
|---------|---------|
| GD update | w^{t+1} = w^t - η·∇f(w^t) |
| SGD update | w^{t+1} = w^t - η·v_t, where E[v_t\|w^t] ∈ ∂f(w^t) |
| SGD convergence (convex-Lipschitz-bounded) | E[f(w̄)] - f(w*) ≤ B·ρ/√T |
| Optimal step size | η = B/(ρ√T) |
| Projection step | w^{t+1} = argmin_{u∈H} ‖u - (w^t - η·v_t)‖ |

## Hermes FTRL Calibration Loop

```python
# Pseudo-code: FTRL routing weight update
# After T routing decisions logged to routing-calibration.jsonl:

import json, math
from pathlib import Path

log = Path('~/.hermes/cache/routing-calibration.jsonl').expanduser()
entries = [json.loads(l) for l in log.read_text().splitlines()[-50:]]
routes = ['semantic', 'temporal', 'relational', 'exact']

# Count outcomes
hits = {r: sum(1 for e in entries if e['route']==r and e['result_count']>0) for r in routes}
counts = {r: sum(1 for e in entries if e['route']==r) for r in routes}

# FTRL: minimize negative log-likelihood + L2 regularizer on route priors
# Simplified: just use empirical hit rate as gradient signal
eta = 1.0 / math.sqrt(len(entries))  # OGD step: O(1/√T)
priors = {r: hits[r]/max(counts[r],1) for r in routes}
# Normalize to simplex
total = sum(priors.values())
priors = {r: v/total for r, v in priors.items()}
```
