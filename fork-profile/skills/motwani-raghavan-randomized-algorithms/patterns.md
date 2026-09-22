# Patterns — Motwani & Raghavan

## 1. Foil the adversary
Treat the algorithm as a distribution over deterministic strategies. Use when a worst-case input exists for every fixed strategy (game trees, online paging, oblivious routing). Yao minimax to *prove* randomised lower bounds.

## 2. Random sampling / random reordering
A uniform sample represents the population; a random permutation destroys pathological order. RandQS, treaps, incremental geometry, LazySelect. Backward analysis: the last inserted object is uniform.

## 3. Abundance of witnesses
Search space too big to scan; fraction of witnesses is `Ω(1)` (or `1/poly`). Sample once, amplify. Primality bases, Freivalds vectors, matching isolations.

## 4. Fingerprint then compare
Hash / evaluate / multiply-by-random-vector. Collision `≤ d/|F|` or `1/2`. Never compare long objects first if a one-sided Monte Carlo test exists.

## 5. Load-balance with limited independence
2-universal / pairwise-independent hash into buckets. Variance via Chebyshev; Chernoff only if you truly have independence. Hermes routing weights: `h_{a,b}`.

## 6. Amplify
- Independent repeats: failure `p^k`. Min-cut `n²/2` trials → `1/e`.
- Expander walk: `O(k)` extra bits, exponential error drop (Ch 6.8).
- MC → LV given a verifier: geometric (Exercise 1.3).

## 7. First / second / exponential moment
| You know | Use | Pattern |
|---|---|---|
| `E[X]`, `X≥0` | Markov | timeout `t=E[T]/δ` |
| `Var(X)` or pairwise ind. | Chebyshev | two-point sampling |
| independent bounded sum | Chernoff | PAC `n∼ε⁻² log(1/δ)` |
| martingale, bounded steps | Azuma | Lipschitz certificate |

## 8. Probabilistic method → algorithm
If the random experiment is efficient, it *is* the algorithm (MAX-SAT 1/2, max-cut 1/2). If not, derandomise (pattern 9) or accept non-uniform existence.

## 9. Derandomise
- Conditional expectations / pessimistic estimator (Ch 5.6).
- Pairwise-independent seed of size `O(log n)`; enumerate if `poly(n)`.
- Isolation (random weights) when you need uniqueness, not derandomisation per se.

## 10. Randomised rounding
Solve LP/IP relaxation; interpret `x_i` as `P[include i]`. Expectation for approximation ratio; Chernoff + union bound for w.h.p. Set cover `O(log n)`, MAX-SAT `1−1/e` then `3/4` by taking the better of two algorithms.

## 11. Mix then sample then count
Build a Markov chain whose stationary distribution is (near) uniform on the objects. Bound mixing (spectral gap / canonical paths). Estimator theorem → FPRAS.

## 12. Isolate a solution
Mulmuley–Vazirani–Vazirani random weights → unique min-weight feasible set w.p. `≥ 1/2`. Parallel matching, unique shortest paths.

## 13. Online rent-vs-buy / paging
Deterministic paging ≥ `k`; Marker `2 H_k` vs oblivious. Ski rental: wait until rent = buy, then buy (ratio 2). Do not claim a randomised online algorithm beats the deterministic bound against an *adaptive offline* adversary (Thm 13.4).

## Hermes mapping
- TF-IDF similarity → pattern 2 + Chernoff (JL projection).
- Beta-bandit reliability → pattern 7 Chernoff PAC.
- Routing weights → pattern 5 pairwise hashing.
- Cron timeout → pattern 7 Markov.
