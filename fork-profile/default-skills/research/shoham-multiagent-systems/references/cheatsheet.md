# Shoham & Leyton-Brown — Quick Cheatsheet

## Game Theory Formulas

| Concept | Formula |
|---------|--------|
| Nash equilibrium | sᵢ = BR(s₋ᵢ) for all i |
| Mixed NE indifference | uᵢ(a, s₋ᵢ) = const for all a in support(sᵢ) |
| Maxmin value | max_{sᵢ} min_{s₋ᵢ} uᵢ(sᵢ, s₋ᵢ) |
| Minimax (zero-sum) | max_{s₁} min_{s₂} u₁ = min_{s₂} max_{s₁} u₁ |
| Expected utility | uᵢ(s) = Σ_a [∏ⱼ sⱼ(aⱼ)] uᵢ(a) |

## Inspection Game

```
p* = b / (b + c)     # optimal inspection probability
q* = (p - c) / p     # inspectee violation probability
```

b = violation benefit, c = audit cost, p = penalty.
**Hermes**: use for tool-auth-shim.py audit rate per tool class.

## Groves / VCG

```
x* = arg max_x  Σᵢ vᵢ(x)                             # efficient choice
VCG paymentᵢ = Σ_{j≠i} v̂ⱼ(x*₋ᵢ) − Σ_{j≠i} v̂ⱼ(x*)  # agent's externality
```

## Revelation Principle

> Any BNE-implementable mechanism = a truthful direct mechanism.

Design agents so truth-telling is a dominant strategy.

## Replicator Dynamic

```
ṗ(s) = p(s) · [u(s, p) − ū(p)]
```

Fixed points = Nash equilibria. ESS is stricter than NE.

## No-Regret

```
RegretT = max_a Σ_t u(a, others_t) − Σ_t u(s_t, others_t)
```

No-regret: lim_{T→∞} RegretT / T ≤ 0. Converges to correlated equilibrium in self-play.

## Folk Theorem (Informal)

With patient enough players (δ → 1), any feasible individually-rational payoff can be a SPE payoff in infinitely repeated game.

## Key Impossibilities

| Result | Statement |
|--------|----------|
| Arrow (1951) | No PE + IIA + non-dictatorial SWF with ≥3 outcomes |
| Muller-Satterthwaite (1977) | No wPE + monotonic + non-dictatorial SCF with ≥3 outcomes |
| Gibbard-Satterthwaite | No DS-implementable SCF is non-dictatorial with ≥3 outcomes (no transfers) |
| Nash complexity | Computing a sample NE is PPAD-complete |

## Learning Rule Convergence

| Algorithm | Convergence guarantee |
|-----------|----------------------|
| Fictitious play | Zero-sum + identical-interest only |
| Regret-matching | Correlated equilibrium (self-play) |
| Minimax-Q | Two-player zero-sum stochastic games |
| IQL / Nash-Q | No general guarantee |
| Replicator dynamic | NE fixed points (stability varies) |
