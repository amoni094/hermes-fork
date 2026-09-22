# Ch 3 — Moments and Deviations

First- and second-moment method. Occupancy, selection, two-point sampling, stable marriage, coupon collector.

## Markov inequality (Ch 3.2)

If `X ≥ 0` and `t > 0`,

`P(X ≥ t) ≤ E[X] / t`.

Equivalently `P(X ≥ λ E[X]) ≤ 1/λ` for `λ ≥ 1`.

**Only** nonnegativity. No independence, no variance. Weak polynomial tails. First bound for cron timeouts: `P(T > t) ≤ E[T]/t`.

## Chebyshev inequality (Ch 3.2)

`P(|X − μ| ≥ t) ≤ Var(X) / t²`, `μ = E[X]`.

One-sided (Chebyshev–Cantelli): `P(X − μ ≥ t) ≤ Var(X) / (Var(X) + t²)`.

**Pairwise independence suffices** to compute `Var(∑ X_i)`: cross terms `Cov(X_i,X_j) = 0` for `i ≠ j`. Full independence is not required.

## Occupancy (Ch 3.1)

`m` balls independently into `n` bins. Empty-bin count `Z` has `E[Z] = n(1−1/n)^m ≈ n e^{−m/n}`. Chebyshev / later Chernoff (Thm 4.18) bound deviations. Birthday / collision regime: `m = Θ(√n)` yields constant collision probability.

## Randomised selection (Ch 3.3)

LazySelect-style: sample `n^{3/4}` elements, sort the sample, pick two order-statistics that bracket the target rank with high probability, recurse on a small interval. Expected linear time; concentration via Chebyshev on the sample.

## Two-point sampling (Ch 3.4)

Need `n` pairwise-independent bits (or field elements) from `O(log n)` random bits.

**Construction.** Prime `p`. Draw `a,b ∈ F_p` uniformly. Set `Y_i = a·i + b (mod p)`. Then `{Y_i}` are pairwise independent and uniform. Hashing analogue: 2-universal family `h_{a,b}`.

**Use.** Repeat a Monte Carlo test on pairwise-independent seeds; Chebyshev still applies to the average. Randomness `O(log n)` instead of `O(n)`.

## Stable marriage (Ch 3.5)

Randomised Proposal (Gale–Shapley with random preference lists). Principle of **deferred decisions**: do not fix all random choices up front. Amnesiac variant (re-propose uniformly, including past rejects) stochastically dominates the true proposal count; reduce to coupon collector.

**Theorem 3.6.** For `m = n ln n + c n`, `lim P[T_A > m] = 1 − e^{−e^{−c}}`.

## Coupon collector (Ch 3.6)

`n` coupon types, uniform independent draws. `X` = time to collect all.

Phases: `X = ∑_{i=0}^{n−1} X_i` where `X_i ~ Geometric((n−i)/n)`, so

`E[X] = n H_n ≈ n ln n + γ n`.

`Var(X) = Θ(n²)`.

**Theorem 3.8.** For `m = n ln n + c n`, `lim P[X > m] = 1 − e^{−e^{−c}}` (double-exponential concentration around `n ln n`).

## Hermes

- Timeout with only a mean: Markov.
- Timeout with a variance (or pairwise-independent retries): Chebyshev.
- “How many random samples until every skill/bin is hit”: coupon collector, `n ln n + c n`.
- Bandit / routing seeds: two-point sampling, not full independence.
