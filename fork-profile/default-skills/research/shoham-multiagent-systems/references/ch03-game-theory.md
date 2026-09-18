# Chapter 3 — Introduction to Noncooperative Game Theory: Games in Normal Form

Source: Shoham & Leyton-Brown, Multiagent Systems, Ch 3.

---

## 3.1 Self-interested agents

- Agents have **preferences** over outcomes, represented by a **utility function** u: O → R.
- Utility functions are unique up to positive affine transformations (von Neumann-Morgenstern).
- Expected utility: u(lottery) = Σ p(o) · u(o).

## 3.2 Normal-form games

A **normal-form game** is a tuple (N, A, u) where:
- N = {1,...,n} is the set of players.
- A = A₁ × ... × Aₙ is the set of action profiles.
- u = (u₁,...,uₙ) is the utility function profile.

Key examples:
- **Prisoner's Dilemma**: Defect dominates Cooperate; NE is Pareto-suboptimal.
- **Matching Pennies**: zero-sum; unique NE is fully mixed (1/2, 1/2).
- **Battle of the Sexes**: two pure NE + one mixed NE.
- **Coordination game**: two pure NE; requires communication or convention.

### Mixed strategies
- A **mixed strategy** sᵢ ∈ Δ(Aᵢ) is a probability distribution over actions.
- The **support** of sᵢ: {aᵢ | sᵢ(aᵢ) > 0}.
- In a mixed NE, every action in the support yields the same expected payoff (indifference condition).

## 3.3 Solution concepts

### Pareto optimality
- s **Pareto dominates** s' if ∀i uᵢ(s) ≥ uᵢ(s') and ∃j uⱼ(s) > uⱼ(s').
- s is **Pareto optimal** if no profile Pareto dominates it.

### Nash equilibrium
- s = (s₁,...,sₙ) is a **Nash equilibrium** if ∀i, sᵢ is a best response to s₋ᵢ.
- **Nash's theorem (1951)**: every finite game has ≥1 Nash equilibrium.
  - Proof: Brouwer's fixed-point theorem via Sperner's lemma on simplotopes.
- Strict NE: each player's strategy is the unique best response.
- Weak NE: at least one player has a tie (all mixed NE are weak).

### Computing NE (Ch 4)
- Two-player zero-sum: linear programming (minimax formulation).
- Two-player general-sum: Lemke-Howson algorithm (LCP) or support enumeration.
- n-player: PPAD-complete (Daskalakis, Goldberg, Papadimitriou 2006).

## 3.4 Further solution concepts

### Maxmin and minmax
- **Maxmin value** for player i: max_{sᵢ} min_{s₋ᵢ} uᵢ(sᵢ, s₋ᵢ) = security level.
- **Minimax theorem (von Neumann, 1928)**: in two-player zero-sum games:
  max_{s₁} min_{s₂} u₁(s₁,s₂) = min_{s₂} max_{s₁} u₁(s₁,s₂) = value of the game.
- In two-player zero-sum: maxmin strategies = NE strategies.

### Dominance
- sᵢ **strictly dominates** s'ᵢ if ∀s₋ᵢ: uᵢ(sᵢ, s₋ᵢ) > uᵢ(s'ᵢ, s₋ᵢ).
- **Iterated elimination of strictly dominated strategies (IESDS)**: order-independent; survivors = rationalizable strategies.
- Weak dominance elimination is order-dependent; use carefully.

### Correlated equilibrium
- A distribution σ over A: following the recommended action is a best response for all players.
- Every NE induces a CE; set of CE is a convex polytope computable via LP.

### Trembling-hand perfect equilibrium
- NE robust to small trembles (perturbations) in strategies.
- Rules out NE sustained by non-credible threats.

### ε-Nash equilibrium
- Strategy profile where no player can gain more than ε by deviating.
- Useful for approximate / computational settings.

## Pitfalls for Hermes

- A game can have multiple NE; coordination mechanism needed to select among them.
- Mixed NE payoffs can be Pareto-dominated by pure NE (Battle of the Sexes).
- Nash equilibrium says nothing about how equilibrium is reached (no dynamics specified).
- IESDS with weak dominance is order-dependent.
