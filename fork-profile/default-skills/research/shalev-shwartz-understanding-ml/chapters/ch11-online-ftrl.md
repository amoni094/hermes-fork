# Ch 21 (Book) — Online Learning, Online Convex Optimization, FTRL

> Note: The book labels this Chapter 21 ("Online Learning"). The task calls it Ch 11 per a different numbering; the content is identical.

## 21.1 Online Classification — Realizable Case

**Protocol:**
1. Learner predicts ŷ_t for x_t
2. Environment reveals y_t
3. Learner suffers loss 1[ŷ_t ≠ y_t], updates model

**Mistake bound**: SOA (Standard Optimal Algorithm) achieves at most Ldim(H) mistakes, where Ldim = Littlestone dimension.

**Key result**: A hypothesis class H is online-learnable iff Ldim(H) < ∞.

## 21.2 Unrealizable Case — Weighted Majority

**Weighted Majority algorithm**: Maintain weights w_i^(t) for each hypothesis h_i.
Predict via weighted vote, update: w_i^(t+1) = w_i^(t) · β^{1[h_i(x_t)≠y_t]}

**Regret bound (Theorem 21.11)**: For |H| = d experts with β = ½:
```
E[mistakes] - min_h mistakes(h) ≤ 2√(log(d) · T)
```

More precisely:
```
∑_t |p_t - y_t| - min_{h∈H} ∑_t |h(x_t) - y_t| ≤ 2√(log(|H|) · T)
```

## 21.3 Online Convex Optimization (OCO)

**Setup**: At each t, learner picks w^(t) ∈ H (convex). Environment reveals z_t, loss ℓ(w^(t), z_t).

**Regret** (vs. competing hypothesis w*):
```
Regret_A(w*, T) = ∑_{t=1}^T ℓ(w^(t), z_t) - ∑_{t=1}^T ℓ(w*, z_t)
```

### Online Gradient Descent (OGD)

```
Algorithm:
  w^(1) = 0
  for t = 1..T:
    predict w^(t)
    receive z_t, let f_t(·) = ℓ(·, z_t)
    choose v_t ∈ ∂f_t(w^(t))    ← subgradient
    w^(t+0.5) = w^(t) - η · v_t
    w^(t+1) = argmin_{w∈H} ‖w - w^(t+0.5)‖   ← projection
```

**Theorem 21.15** — OGD regret bound:
```
Regret_A(w*, T) ≤ ‖w*‖²/(2η) + η/2 · ∑_t ‖v_t‖²
```

With η = B/(ρ√T) (B-bounded domain, ρ-Lipschitz losses f_t):
```
Regret_A(H, T) ≤ B·ρ·√T    ← O(√T)
```

### FTRL — Follow the Regularized Leader

The FTRL update generalizes OGD. Instead of a single gradient step, it minimizes the cumulative empirical loss plus a regularizer:

```
w^{t+1} = argmin_w [ ∑_{s=1}^t ℓ_s(w) + R(w) ]
```

where R(w) is a regularizer (e.g., R(w) = λ‖w‖² for L2).

**FTRL regret bound**: With R(w) = (1/2η)‖w‖² and ρ-Lipschitz losses:
```
Regret_FTRL ≤ ‖w*‖²/(2η) + η·T·ρ²/2
```
Setting η = ‖w*‖/(ρ√T) gives Regret = O(√T).

**Compared to OGD**: FTRL and OGD achieve the same asymptotic O(√T) regret. FTRL is more amenable to sparse regularization (e.g., L1/LASSO), making it useful for feature selection in routing.

## 21.4 Online Perceptron

For halfspace classifiers H = {x ↦ sign(⟨w, x⟩) : w ∈ R^d}:

```
Algorithm:
  w^(1) = 0
  for t = 1..T:
    predict ŷ_t = sign(⟨w^(t), x_t⟩)
    receive y_t
    if ŷ_t ≠ y_t: w^(t+1) = w^(t) + y_t · x_t
    else:          w^(t+1) = w^(t)
```

**Perceptron mistake bound**: If data is γ-margin separable with ‖x_t‖ ≤ ρ:
```
mistakes ≤ (ρ/γ)²
```

## Key Takeaways for Hermes

1. **Route weight adaptation**: Each routing decision (semantic/temporal/relational/exact) is a "prediction". A calibration log with (route, outcome) pairs lets you compute regret. Apply OGD on route priors to minimize regret.

2. **O(√T) convergence**: After T routing decisions, the OGD/FTRL-adapted router is at most O(√T) worse than the best fixed route assignment — specifically, it converges to the oracle as T grows.

3. **Regularizer choice**: Use L2 regularization (Tikhonov) for stable, smooth adaptation of route weights. Use L1 for sparse updates (few route changes per batch).

4. **Projection step**: Route weights must stay in the probability simplex (sum to 1, all ≥ 0). Use the simplex projection as the projection step in OGD.
