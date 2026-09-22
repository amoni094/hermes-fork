# Ch 11 — Approximate Counting

## FPRAS (Ch 11.1)

A **fully polynomial randomised approximation scheme** for a counting function `f`: on input `x, ε, δ` outputs `Ŷ` with

`P[(1−ε) f(x) ≤ Ŷ ≤ (1+ε) f(x)] ≥ 1−δ`

in time `poly(|x|, 1/ε, log(1/δ))`.

**Estimator theorem (Thm 11.1).** If `Y_i` are i.i.d. unbiased (`E[Y]=f`) with `Var(Y)/E[Y]² ≤ ρ`, then the mean of `O(ρ ε^{-2} log(1/δ))` samples is an FPRAS. Chernoff if `Y` is bounded; Chebyshev + median-of-means otherwise.

Self-reducibility: approximate counting ⇔ almost-uniform sampling (Jerrum–Valiant–Vazirani). Mixing of an appropriate Markov chain yields the sampler (Ch 6).

## DNF counting (Ch 11.2)

Karp–Luby–Madras: a DNF formula with `m` terms over `n` variables. Naive sampling of `{0,1}^n` fails when the satisfying set is tiny. Instead sample from the union of the term-cubes with probability proportional to cube size, then unbiasedly estimate coverage. FPRAS.

## Permanent (Ch 11.3)

Permanent of a 0–1 matrix = number of perfect matchings in a bipartite graph. Jerrum–Sinclair Markov chain on matchings; rapidly mixing when the graph is dense / has a guaranteed matching expansion. (Fully polynomial approximation for general bipartite permanents came in 2001, Jerrum–Sinclair–Vigoda; Motwani covers the Markov-chain approach.)

## Volume estimation (Ch 11.4)

Volume of a convex body given by a membership oracle. Deterministic poly-time approximation is impossible to within even exponential factors in high dimension (Thm 11.14, Bárány–Füredi). Randomised: random walk (ball walk / hit-and-run) in a sandwiching sequence of bodies; Dyer–Frieze–Kannan FPRAS.

## Hermes

- Estimate a rare event (how often a cron path hits a state): do not sample the ambient space; sample from a mixture of “witness cubes” (DNF pattern) or run a mixed Markov chain.
- Sample complexity: Estimator Theorem / Chernoff, not “looks stable so stop.”
