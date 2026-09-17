# Bandit Algorithms Cheatsheet (Lattimore & Szepesvári)

## Quick Decision Tree

```
Environment type?
├── Rewards are IID / stationary
│   ├── No context features → UCB1 or Thompson Sampling
│   └── Context features available → LinUCB
└── Rewards are adversarial / non-stationary
    ├── No structure → EXP3
    └── Linear structure → Adversarial LinBandit
```

## Formula Card

### UCB1
```
A_t = argmax_i [ μ̂_i + sqrt(2 ln(t) / n_i) ]

where:
  μ̂_i = Σ rewards from arm i / n_i    (empirical mean)
  n_i  = pulls of arm i
  t    = total rounds

Regret: R_n = O(sqrt(K·T·ln T))
```

### Thompson Sampling (Bernoulli)
```
Sample θ_i ~ Beta(S_i + 1, F_i + 1)
Pull A_t = argmax_i θ_i
Update: S_i or F_i += 1

Regret: same order as UCB1, better empirically
```

### EXP3
```
p_{t,i} = (1-γ)·w_i/Σw_j + γ/K
x̃_{t,i} = r_t/p_{t,i} · 1[A_t=i]
w_i ← w_i · exp(γ·x̃_{t,i}/K)

γ = sqrt(K ln K / T)
Regret: R_n ≤ 2·sqrt(K·T·ln K)
```

### LinUCB
```
ucb_a = θ̂_a·x_{t,a} + α·sqrt(x_{t,a}^T A_a^{-1} x_{t,a})
A_a += x x^T, b_a += r·x  (on pull)
θ̂_a = A_a^{-1} b_a

α = sqrt(ln(2T/δ)/2)
Regret: R_n = O(d·sqrt(T·ln T))
```

## UCB1 for Hermes Source Weighting

```python
_BANDIT_STATE_PATH = Path('~/.hermes/cache/recall-bandit-state.json').expanduser()

def _ucb1_weight(source, state, t):
    s = state.get(source, {'n': 0, 'reward': 0.0})
    if s['n'] == 0 or t == 0:
        return 1.5  # cold-start explore bonus
    mu = s['reward'] / s['n']
    return mu + math.sqrt(2 * math.log(max(t, 1)) / s['n'])

# Usage: rrf_contrib = _ucb1_weight('hindsight', state, t) * (1.0 / (RRF_K + rank + 1))
```

## Regret Comparison

| Algorithm | Regret | Setting |
|-----------|--------|---------|
| UCB1 | O(sqrt(KT ln T)) | Stochastic |
| Thompson | O(sqrt(KT ln T)) | Stochastic |
| EXP3 | O(sqrt(KT ln K)) | Adversarial |
| LinUCB | O(d sqrt(T ln T)) | Contextual |
| Lower bound (stochastic) | Ω(sqrt(KT)) | — |
| Lower bound (adversarial) | Ω(sqrt(KT)) | — |

## When NOT to use bandit weighting

- Cold start with < 5 queries per source: weights are meaningless; use uniform
- Reward signal is delayed by > 100 rounds: UCB1 stale; consider discounted UCB
- Sources are perfectly correlated: weighting doesn't help, just add noise
