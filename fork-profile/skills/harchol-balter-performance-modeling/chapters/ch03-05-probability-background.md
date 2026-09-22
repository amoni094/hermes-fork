# Ch 3–5 — Probability, Simulation, Averages

**Use when**: deriving E[·] by conditioning, generating r.v.s, or confusing time-average with ensemble-average.

## Must-have identities
- Law of total probability / Bayes
- E[X] = E[E[X|Y]]
- Linearity: E[∑ X_i] = ∑ E[X_i] even if dependent
- Var(X) = E[X²] − (E[X])²
- Wald: if N independent of X_i, E[∑_{i=1}^N X_i] = E[N] E[X]

## Squared coefficient of variation
```
C_X² = Var(X) / E[X]²
```
Exponential: C² = 1. Deterministic: 0. Heavy-tailed computer jobs: C² ≫ 1.

## Inverse-transform & accept-reject (Ch 4)
Simulate G via U~Unif(0,1), X=F^{-1}(U). Use for Pareto/H2 workload generators.

## Time average vs ensemble average (Ch 5)
Little's Law is a **time-average** statement. Ergodicity ⇒ time average = ensemble average. Do not average only at arrival instants unless PASTA. Strong LLN needs E[|X|]<∞; Pareto α≤1 has infinite mean — sample means misbehave.
