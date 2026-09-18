# Chapter: Contextual and Linear Bandits (Lattimore & Szepesvári, Part V)

## Motivation

- **Finite-armed bandits** fail when: K is large/infinite, OR context (side information) is available
- **Context** x_t per round: user features, query features, document embeddings
- **Generalisation**: pulling arm a gives info about similar arms (via shared θ*)
- Solution: assume reward is a **linear function** of feature vectors

## Contextual Bandit Setting

- Each round t: context x_t ∈ ℝ^d arrives
- Learner chooses arm A_t ∈ {1, ..., K}
- Reward: r_t = f(x_{t,A_t}) + ε_t  where ε_t is noise, f is unknown
- Linear assumption: f(x) = θ*·x  (dot product with unknown θ* ∈ ℝ^d)

## LinUCB (Linear Upper Confidence Bound)

### Disjoint Model (separate θ* per arm)

Each arm a has its own parameter θ_a*. Actions feature vectors are arm-specific.

```python
# Init: for each arm a
A_a = np.eye(d)    # d×d regularised gram matrix
b_a = np.zeros(d)  # cumulative reward-weighted features

# Each round t, for each arm a:
theta_hat_a = np.linalg.solve(A_a, b_a)
ucb_a = theta_hat_a @ x_ta + alpha * np.sqrt(x_ta @ np.linalg.solve(A_a, x_ta))

# Pull A_t = argmax_a ucb_a
# After observing r_t:
A_{A_t} += np.outer(x_{t,A_t}, x_{t,A_t})
b_{A_t} += r_t * x_{t,A_t}
```

- α = sqrt(ln(2T/δ)/2) controls confidence width
- Uncertainty term x^T A^{-1} x = "information gain" from pulling this arm

### Hybrid Model (shared + arm-specific parameters)

When some features are arm-independent (e.g. user context), use shared β + arm-specific θ_a:
```
E[r_{t,a}] = z_t · β + x_{t,a} · θ_a
```
More complex update but better generalisation when arms share structure.

## Regret Bound (LinUCB, Disjoint)

```
R_n = O(d · sqrt(T · ln T))
```
- Linear in dimension d: higher-dimensional features → harder problem
- Optimal up to log factors (matching lower bound O(d·sqrt(T)))

## Key Geometric Insight

The exploration bonus `sqrt(x^T A^{-1} x)`:
- Large when x points in direction not yet well-explored (A sparse in that direction)
- Small when x is in span of previously pulled arms' features (A dense)
- A = Σ_t x_t x_t^T + I  ←  information matrix; A^{-1} is the covariance of θ̂

This is exactly the elliptical confidence set from OLS regression:
`||θ̂ - θ*||_{A} ≤ sqrt(...)` with high probability.

## Stochastic vs Adversarial Linear Bandits

**Stochastic LinUCB:** θ* fixed, noise iid → O(d√T) regret.
**Adversarial LinBandit:** θ* changes each round (adversary) → need EXP3 + importance weighting.
Both covered in Lattimore & Szepesvári Parts V–VI.

## Practical Notes

### When to use LinUCB over UCB1
- Arms have feature vectors (embeddings, metadata)
- K >> 1 or K = ∞ (continuous action space sampled via features)
- You want generalisation: pulling arm a updates beliefs about similar arms

### Hermes Recall Application (Future Extension)
If memory sources are characterised by query-type feature vectors:
- x_{t,a} = [query_is_structural, query_is_episodic, query_len_norm, ...]
- θ_a* learned per source (hindsight, graphiti, l1)
- UCB1 is degenerate LinUCB with d=1, x=1 (no context)
- LinUCB extension: weight sources differently per query type

## References

- Li et al. [2010] — original LinUCB / contextual bandits for news recommendation
- Abbasi-Yadkori et al. [2011] — improved confidence sets for LinUCB
- Chu et al. [2011] — LinUCB with disjoint and hybrid models
- Lattimore & Szepesvári, Chapters 19-22 (Part V)
