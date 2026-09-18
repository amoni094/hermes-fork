# Chapter: Adversarial Bandits with Finitely Many Arms (Lattimore & Szepesvári, Part III)

## Setting

- **K** arms; rewards x_{t,i} ∈ [0,1] chosen by an adversary (possibly after seeing algorithm code)
- Adversary is **adaptive** — can set rewards based on algorithm's randomisation
- **Only stochastic element:** learner's own randomised choices

Key difference from stochastic: arm means are **not constant** — adversary can make any arm the best one at any round.

## Why Stochastic Algorithms Fail

Deterministic strategies are exploitable: adversary sees your code → always makes your chosen arm bad.
Randomisation is **necessary**: with probability p=1/2 on each arm (2-arm case), adversary cannot do better than R ≤ n/2, matching a lower bound argument.

## EXP3 Algorithm (Exponential Weights for Exploration and Exploitation)

```
Init: w_i = 1 for all i ∈ [K]; choose γ ∈ (0, 1]
Each round t:
  Compute: p_{t,i} = (1-γ) · w_i / Σ_j w_j  +  γ/K
  Sample A_t ~ Categorical(p_t)
  Observe X_{A_t} ∈ [0, 1]
  Importance-weighted estimate: x̃_{t,i} = X_{A_t}/p_{t,A_t} · 1[A_t = i]  (else 0)
  Update: w_i ← w_i · exp(γ · x̃_{t,i} / K)
```

**Parameter choice:** γ = sqrt(K ln K / T) (requires knowing T in advance)

### Why Importance Weighting?

x̃_{t,i} is an unbiased estimate of X_{t,i}: E[x̃_{t,i}] = X_{t,i}.
This lets us compute pseudo-loss for ALL arms even though we only observe one.

### Regret Bound

```
E[R_n] ≤ 2 · sqrt(K · T · ln K)
```
- Worst-case over ALL adversarial strategies
- Matches minimax lower bound Ω(sqrt(K·T)) up to sqrt(ln K) factor
- Per-round expected regret: O(sqrt(K ln K / T))

## Adversarial vs Stochastic

| | Stochastic | Adversarial |
|--|-----------|-------------|
| Reward model | IID, fixed means | Arbitrary, adaptive |
| Best algorithm | UCB1/Thompson | EXP3 |
| Regret | O(sqrt(KT ln T)) | O(sqrt(KT ln K)) |
| Key trick | Confidence bounds | Importance weighting |
| Requires T? | No (anytime UCB) | Yes (for γ tuning) |

## EXP3.P (High-Probability Variant)

Modified with explicit exploration bonus in the exponent to achieve high-probability (not just expected) regret bounds. Rarely needed in practice; EXP3 suffices for most applications.

## When to Use Adversarial Algorithms in Hermes

Use EXP3 instead of UCB1 for source weighting when:
- The relevance of sources shifts based on query patterns (non-stationary environment)
- External factors (e.g., index updates, API changes) cause sudden source quality changes
- You suspect the query distribution is adversarially structured (e.g., benchmark gaming)

Practical note: in practice, stochastic algorithms (UCB1) often outperform EXP3 even in mildly non-stationary settings, because stochastic regularity exists and EXP3's uniform exploration is expensive.

## Bibliographic Remarks

- Earliest adversarial bandit work: Auer et al. [1995]
- EXP3 named for: Exponential weights + 3 properties (Auer et al. [2002])
- Connection to game theory: Hannan [1957], Blackwell [1954] (approachability)
- Full-information version: Hedge algorithm (Freund & Schapire [1997])
