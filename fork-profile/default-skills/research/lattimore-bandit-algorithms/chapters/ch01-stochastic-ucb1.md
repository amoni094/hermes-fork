# Chapter: Stochastic Bandits with Finitely Many Arms (Lattimore & Szepesvári, Part II)

## Setting

- **K** arms, each arm i has reward distribution with mean μ_i
- Each round t: pull arm A_t, observe X_t ~ P_{A_t} (iid)
- **Goal:** minimise pseudo-regret R_n = n·μ* - Σ_t μ_{A_t}

Keywords: **finite**, **unstructured** (no arm shares info), **stochastic** (iid rewards).

## UCB1 Algorithm

```
Init: pull each arm once (n_i = 1, μ̂_i = first reward)
For t = K+1, K+2, ..., T:
  A_t = argmax_i [ μ̂_i + sqrt(2 ln t / n_i) ]
  Observe X_t; update μ̂_{A_t}, n_{A_t}
```

### Exploration Bonus Derivation

By Hoeffding's inequality, for bounded rewards in [0,1]:
```
P(μ_i > μ̂_i + ε) ≤ exp(-2 n_i ε²)
```
Setting δ = exp(-2 n_i ε²) and solving: ε = sqrt(ln(1/δ) / (2 n_i)).

Choosing δ = 1/t² (union-bounding over T rounds) gives exploration bonus sqrt(2 ln t / n_i).

The UCB index = μ̂_i + sqrt(2 ln t / n_i) is an upper confidence bound on μ_i with high probability.

### Regret Analysis

**Instance-dependent bound:**
```
E[R_n] ≤ Σ_{i: Δ_i > 0} [ 8 ln n / Δ_i + (1 + π²/3) Δ_i ]
```
- First term: logarithmic cost of learning which arm is best
- Second term: constant "burn-in" cost

**Minimax bound:** E[R_n] = O(sqrt(K·T·ln T))

### Gap-Dependent Interpretation

Arms with small gap Δ_i are hardest to distinguish — UCB1 explores them O(ln n / Δ_i²) times.
Arms with large gap are quickly identified as suboptimal and rarely pulled.

## Thompson Sampling (Bayesian Alternative)

```
Prior: S_i = F_i = 0 for all i
Each round t:
  Sample θ_i ~ Beta(S_i + 1, F_i + 1) for all i
  Pull A_t = argmax_i θ_i
  If X_t = 1: S_{A_t} += 1, else F_{A_t} += 1
```

- Posterior Beta(S_i+1, F_i+1) concentrates around μ_i = S_i/(S_i+F_i)
- Regret matches UCB1 asymptotically; often better empirically
- Extension to Gaussian rewards: Thompson Sampling with Normal-Normal conjugate

## Key Insight: Optimism Under Uncertainty

Both UCB1 and Thompson Sampling implement the same core principle:
**"Optimism in the face of uncertainty"** — act as if each arm is as good as its
uncertainty allows, so that pulling an uncertain arm is never a pure waste.

## Applications to Hermes Recall

**Source = arm, reward = retrieval quality signal:**

- n_i: number of times source i was queried
- reward: binary (user accepted result) or continuous (downstream task success)
- UCB1 weight: μ̂_i + sqrt(2 ln t / n_i) → replace fixed RRF weight with adaptive weight
- Cold start (n_i = 0): return large explore bonus (e.g. 1.5) to force at least one query per source

State file: `~/.hermes/cache/recall-bandit-state.json`
```json
{
  "hindsight": {"n": 12, "reward": 8.5},
  "graphiti": {"n": 12, "reward": 6.2},
  "l1": {"n": 3, "reward": 2.1}
}
```
