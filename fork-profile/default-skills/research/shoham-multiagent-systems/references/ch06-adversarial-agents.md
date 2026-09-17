# Chapter 6 — Richer Representations, Adversarial Agents & Learning (Ch 7)

Source: Shoham & Leyton-Brown, Multiagent Systems, Ch 6 + Ch 7.

---

## 6.1 Repeated games

### Finitely repeated games
- Unique stage NE → unique subgame-perfect equilibrium: play stage NE every round.
- Cooperation cannot be sustained in finitely repeated Prisoner's Dilemma.

### Folk Theorem (infinitely repeated games)
- With discount factor δ ∈ (0,1), as δ → 1: any feasible, individually-rational payoff can be a SPE payoff.
- Key strategies: **grim trigger** (cooperate until deviation, then punish forever), **Tit-for-Tat**.
- **Hermes**: long-horizon cron agent relationships can sustain cooperative norms that single-shot reasoning cannot.

## 6.2 Stochastic games

- State transitions: P(s'|s,a); payoffs R(s,a).
- **Minimax-Q** (Littman): optimal in two-player zero-sum stochastic games.
- General-sum: Nash-Q converges only in special cases.

## 6.3 Bayesian games

- Private types θᵢ drawn from common prior.
- **Bayes-Nash equilibrium**: sᵢ(θᵢ) best-responds given beliefs about others' types.
- Auctions are Bayesian games (see Ch 11).

## 6.4 Congestion games

- Payoff depends on number of agents sharing each resource.
- Every congestion game is a potential game → pure NE always exists.
- **Price of anarchy (PoA)**: ≤ 4/3 for linear latency (Roughgarden & Tardos).

## 6.5 Compact representations

- **Graphical games**: utility depends on direct neighbours; exponential savings for sparse graphs.
- **Action-graph games (AGG)**: nodes = actions; exploit anonymity (aggregate action counts).
- **MAID**: graphical + extensive-form; exploits strategic relevance for efficient equilibrium computation.

---

## Inspection Game

**Two players**: Inspector (I) and Inspectee (E).

|  | Comply | Violate |
|---|---|---|
| **Inspect** | (-c, 0) | (-c+p, -p+b) |
| **No Inspect** | (0, 0) | (0, b) |

c = audit cost, b = violation benefit, p = penalty.

**Unique mixed-strategy NE**:
```
p* = b / (b + c)       # inspector's audit probability
q* = (p - c) / p       # inspectee violation probability (when p > c)
```

**Key properties**:
- Higher c → lower p* (expensive auditing → audit less often).
- Higher b → higher p* (higher stakes → audit more).
- At NE, each player is indifferent between their actions.
- **Hermes tool-auth**: set p* per tool class with b = tool_risk_score, c = auth_latency_cost.

---

## Chapter 7 — Multi-Agent Learning

### Fictitious play (7.2)
- Best-respond to empirical frequency of opponents' past play.
- Converges: two-player zero-sum, identical-interest. Does NOT converge in general.

### Rational learning (7.3)
- Bayesian update on opponent's strategy; converges if opponent plays stationary strategy.
- Computationally expensive for large strategy spaces.

### Reinforcement learning in MAS (7.4)
- **Independent Q-learning (IQL)**: fast; no convergence guarantee in general MAS.
- **JAL (Joint Action Learner)**: converges under strong assumptions; exponential in agent count.
- **Minimax-Q**: optimal for two-player zero-sum stochastic games.
- **Nash-Q**: NE at each state; convergence only in special cases.

### No-regret learning / Hannan consistency (7.5)
- No-regret: lim_{T→∞} Regret_T / T ≤ 0, where Regret_T = max_a Σ_t u(a, others_t) − Σ_t u(s_t, others_t).
- **Regret-matching**: achieves no regret; converges to correlated equilibrium in self-play.
- **Hermes**: skill routing as no-regret problem — track regret per skill, route proportionally.

### Targeted learning / teaching (7.6)
- **Stackelberg leader**: commits to strategy to induce follower's best response.
- Short-term sacrifice for long-term gain; requires repeated interaction.

### Evolutionary learning (7.7)
- **Replicator dynamic**: ṗ(s) = p(s) · [u(s, p) − ū(p)].
- Fixed points = Nash equilibria; not all NE are stable under replicator dynamic.
- **ESS**: stricter than NE; robust to invasion by small fraction of mutants.

## Pitfalls

- IQL is not convergence-guaranteed even in simple 2×2 games.
- Folk theorem requires infinite horizon + patient players (high δ).
- Inspection game p* assumes risk neutrality; adjust for risk-averse agents.
- Fictitious play can cycle; combine with empirical convergence check.
