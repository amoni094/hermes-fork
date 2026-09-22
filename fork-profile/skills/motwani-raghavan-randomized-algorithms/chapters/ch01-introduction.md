# Ch 1 — Introduction

Paradigms: **foiling an adversary**, **random sampling**, **abundance of witnesses**, **fingerprinting/hashing**, **random reordering**, **load balancing**, **rapidly mixing walks**, **isolation / symmetry breaking**, **probabilistic existence**.

## RandQS (randomised Quicksort)

**Algorithm.** Input set `S` of `n` numbers.

1. Choose pivot `y` uniformly from `S`.
2. Partition into `S1 = {x < y}`, `S2 = {x > y}`.
3. Recurse; output sorted `S1`, then `y`, then sorted `S2`.

**Analysis.** Let `S_{(i)}` be the rank-`i` element. Indicator `X_{ij} = 1` iff `S_{(i)}` and `S_{(j)}` are compared. Comparisons occur only against the current pivot; equivalently, `i` and `j` are compared iff one of them is the first element of `{i,…,j}` chosen as a pivot.

Any of those `j−i+1` ranks is equally likely to appear first, so

`P_{ij} = 2 / (j − i + 1)`.

Linearity of expectation (no independence needed):

`E[∑_{i<j} X_{ij}] = ∑_{i<j} P_{ij} ≤ 2 n H_n`.

**Theorem 1.1.** Expected comparisons in RandQS `≤ 2n H_n = O(n log n)`.

This holds for **every** input; randomness is only over pivot choices. Las Vegas: always correct, random runtime.

## Contraction min-cut (Ch 1.1)

`G`: connected undirected multigraph, `n` vertices. A **cut** is an edge set whose deletion disconnects `G`; **min-cut** has minimum cardinality `k`.

**Algorithm.** While `> 2` vertices remain: pick a uniform random edge and **contract** it (merge endpoints, drop self-loops, keep parallel edges). Output the multiedge bundle between the last two vertices.

Contraction never decreases min-cut size: every intermediate cut is a cut of the original graph.

**Success probability.** Fix a min-cut `C` with `k` edges. `G` has `≥ kn/2` edges (min degree `≥ k`). Probability of never contracting an edge of `C`:

`∏_{i=0}^{n-3} (1 − 2/(n−i)) = 2 / (n(n−1)) > 2/n²`.

Monte Carlo: may output a non-min cut. Repeat `n²/2` independent times → failure probability `≤ (1 − 2/n²)^{n²/2} < 1/e`.

**Do not** contract random *vertex pairs* instead of random edges: Exercise 1.2 — some inputs have exponentially small success.

## Las Vegas vs Monte Carlo (Ch 1.2)

| | Correctness | Runtime |
|---|---|---|
| **Las Vegas** | always correct | random (study its distribution) |
| **Monte Carlo** | may err; bound `P[error]` | typically polynomial (worst-case or expected) |

Monte Carlo decision algorithms: **one-sided error** (never errs on at least one of YES/NO) vs **two-sided error**.

**Exercise 1.3 (MC → LV).** Monte Carlo `A` with expected time `T(n)`, success probability `y(n)`, plus a `t(n)` verifier → Las Vegas with expected time `(T(n)+t(n))/y(n)` (geometric number of trials).

**Amplification (Exercise 1.4).** Independent repeats reduce error from `ε1` to `ε2 < ε1` at a `Θ(log(1/ε2)/log(1/ε1))` blow-up.

**Complexity.** Efficient Las Vegas ⊆ **ZPP**. Efficient one-sided Monte Carlo ⊆ **RP** / **co-RP**. Two-sided ⊆ **BPP**.

## Other Ch 1 notes

- **Binary planar partitions** (autopartitions of segments): random permutation of cut order; expected size `O(n log n)` (Thm 1.2) — existence of a small partition via the probabilistic method.
- **Probabilistic recurrences** for randomised divide-and-conquer (when split sizes are random).
- Computation model: unit-cost random bits; complexity classes RP, BPP, ZPP.

## Hermes

Retry-until-verified loops are Exercise 1.3. Independent retries of a flaky check are min-cut amplification: `k` repeats send failure `p → p^k`.
