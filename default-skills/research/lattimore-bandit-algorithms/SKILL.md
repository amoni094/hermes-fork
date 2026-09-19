---
name: lattimore-bandit-algorithms
description: Use when applying bandit algorithms for adaptive routing.
category: research
tags: [bandits, ucb1, thompson-sampling, exp3, linucb, exploration, exploitation, regret]
---

# Lattimore & Szepesvári — Bandit Algorithms

Knowledge base from *Bandit Algorithms* (Lattimore & Szepesvári, 2020). Use when implementing adaptive source weighting, exploration/exploitation trade-offs, or any multi-armed bandit decision problem.


## Model Routing

Algorithm derivation / regret analysis: magistral-small-latest (mistral). Implementation + test (UCB1, Thompson Sampling, EXP3, LinUCB in Python): grok-4.6 workers via delegate_task — these tasks always have a coding tail.


## Decision Tree: Which Algorithm?

```
Q: Is the reward distribution stationary?
├─ YES → Stochastic setting
│    Q: Do you have context/features per round?
│    ├─ NO  → UCB1 or Thompson Sampling
│    └─ YES → LinUCB (linear reward) or ε-greedy
└─ NO  → Adversarial / non-stationary setting
     Q: Do you have linear structure?
     ├─ NO  → EXP3 (finite arms)
     └─ YES → Adversarial LinBandit (EXP3 + OLS)
```

## Algorithm Reference

### UCB1 (Stochastic, finite arms)

**Formula:** `A_t = argmax_i [ μ̂_i + sqrt(2 ln(t) / n_i) ]`

- `μ̂_i` = empirical mean reward of arm i  
- `n_i` = number of times arm i was pulled  
- `t` = total rounds elapsed  
- Exploration bonus: `sqrt(2 ln(t) / n_i)` — shrinks as n_i grows

**Regret bound:** `R_n = O(sqrt(K · T · ln T))`  
**Instance-dependent:** `R_n ≤ Σ_{i: Δ_i > 0} (8 ln n / Δ_i + (1 + π²/3) Δ_i)`  
where `Δ_i = μ* - μ_i` is the gap of suboptimal arm i.

**When to use:** stationary rewards, finite known arms, no side information.

**Cold-start rule:** Pull each arm once before applying UCB1 formula (n_i=0 causes division by zero; return ∞ or a large explore bonus like 1.5 × max observed reward).

**Hermes application:** Weight memory sources (hindsight / graphiti / l1) by UCB1 score. State: `{source: {n, reward}}`. After each query log the reward signal (e.g. user thumbs-up, downstream task success). See `_load_bandit_state()` / `_ucb1_weight()` / `_update_bandit_state()` in `unified-recall.py`.

---

### Thompson Sampling (Stochastic, Bayesian)

**Algorithm (Bernoulli rewards):**
```
Prior: θ_i ~ Beta(1, 1) (uniform)
Each round t:
  Sample θ_i ~ Beta(S_i + 1, F_i + 1) for each arm i
  Pull A_t = argmax_i θ_i
  Observe reward X_t ∈ {0, 1}
  Update: S_{A_t} += X_t, F_{A_t} += 1 - X_t
```
- `S_i` = successes, `F_i` = failures
- Posterior concentrates around true mean as data grows

**Regret bound:** matches UCB1 asymptotically; often better empirically.  
**When to use:** binary/Bernoulli rewards, Bayesian prior available, want natural uncertainty calibration.  
**Advantage over UCB1:** more exploratory early, adapts naturally to reward variance.

---

### EXP3 (Adversarial, finite arms)

**Algorithm:**
```
Init: w_i = 1 for all i ∈ [K]
Each round t:
  p_i = (1 - γ) · w_i / Σ_j w_j  +  γ/K    (mixed: γ uniform exploration)
  Pull A_t ~ Categorical(p)
  Observe X_{A_t} ∈ [0,1]
  Importance-weighted estimate: x̃_i = X_{A_t}/p_{A_t} · 1[A_t = i]  (0 for others)
  Update: w_i ← w_i · exp(γ · x̃_i / K)
```
- `γ = sqrt(K ln K / T)` (tuned to horizon T)

**Regret bound:** `R_n ≤ 2 sqrt(K · T · ln K)` (worst-case adversarial).  
**When to use:** adversarial/non-stationary environment, adversary can see your algorithm.  
**Key insight:** randomised strategy prevents adversary from exploiting deterministic choices.

---

### LinUCB (Contextual / Linear bandits)

**Setting:** each round t, arm a has feature vector `x_{t,a} ∈ ℝ^d`. Reward `r_{t,a} = θ* · x_{t,a} + noise`.

**Algorithm (Disjoint LinUCB):**
```
For each arm a, maintain: A_a = I_d, b_a = 0
Each round t:
  θ̂_a = A_a^{-1} b_a
  UCB_a = θ̂_a · x_{t,a} + α · sqrt(x_{t,a}^T A_a^{-1} x_{t,a})
  Pull A_t = argmax_a UCB_a
  Update: A_{A_t} += x_{t,A_t} x_{t,A_t}^T, b_{A_t} += r_t · x_{t,A_t}
```
- `α = sqrt(ln(2T/δ)/2)` for δ-confidence
- Uncertainty term `x^T A^{-1} x` = information-geometric exploration bonus

**Regret bound:** `R_n = O(d · sqrt(T · ln T))`.  
**When to use:** context/feature vector available per round, reward linear in features, large/structured action set.

---

## Lower Bounds

**Minimax lower bound (stochastic, K arms):** `R_n ≥ Ω(sqrt(K · T))`  
**Instance-dependent lower bound (stochastic):** `R_n ≥ Σ_{i: Δ_i>0} (ln n / Δ_i) · (1 - o(1))` for any consistent policy.  
**Adversarial lower bound:** `R_n ≥ Ω(sqrt(K · T · ln K))` — EXP3 is nearly optimal.

Key insight: UCB1's `O(sqrt(KT ln T))` matches the minimax lower bound up to a `sqrt(ln T)` factor. The instance-dependent `ln n / Δ_i` term is tight by information-theoretic argument (Pinsker's inequality on KL-divergence between reward distributions).

---

## Stochastic vs Adversarial: Regime Detection

| Criterion | Stochastic | Adversarial |
|-----------|-----------|-------------|
| Reward stability | IID across rounds | Can change arbitrarily |
| Best algorithm | UCB1 / Thompson | EXP3 |
| Regret form | Instance-dep + minimax | Minimax only |
| Prior knowledge | None needed | Need K, T for γ |
| Computational | O(K) per round | O(K) per round |

**Hybrid:** BCB (Best of Both Worlds) algorithms achieve `O(sqrt(T))` adversarial AND `O(ln T / Δ_min)` stochastic — but more complex. See Ch 31 of Lattimore & Szepesvári.

---

## Key Concepts (Glossary)

- **Regret:** `R_n = n · μ* - Σ_t μ_{A_t}` — cumulative gap vs always pulling best arm
- **Pseudo-regret:** expectation of regret; most bounds are on pseudo-regret
- **Gap Δ_i:** `μ* - μ_i` — suboptimality of arm i
- **Exploration vs exploitation:** explore = gather info on uncertain arms; exploit = pull known-best arm
- **UCB (Upper Confidence Bound):** optimism in the face of uncertainty — act as if each arm is as good as its confidence interval allows
- **Importance weighting:** EXP3 trick: divide observed reward by selection probability to get unbiased estimate for all arms
- **Bandit feedback:** only observe reward for chosen arm (vs full-information where all rewards revealed)
- **Context:** side information `x_t` available before choosing arm; enables generalisation across arms

---

## Linked Files

- `chapters/ch01-stochastic-ucb1.md` — UCB1 derivation and analysis
- `chapters/ch02-adversarial-exp3.md` — EXP3 and adversarial setting
- `chapters/ch03-contextual-linucb.md` — Contextual and linear bandits
- `cheatsheet.md` — Quick reference card
- `glossary.md` — Full glossary
