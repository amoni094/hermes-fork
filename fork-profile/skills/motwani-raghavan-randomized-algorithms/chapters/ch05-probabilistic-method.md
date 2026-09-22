# Ch 5 — The Probabilistic Method

Prove existence by showing a random object is good with positive probability. Sometimes the proof *is* an efficient randomised algorithm; sometimes it is non-constructive.

Two recurrent ideas:

1. A r.v. takes some value `≥ E[X]` and some `≤ E[X]`.
2. If `P[property] > 0`, an object with the property exists.

## MAX-SAT / MAX-3SAT (Ch 5.2)

**Theorem 5.1 (max-cut).** Any undirected graph with `m` edges has a cut of size `≥ m/2`. Proof: random bipartition; each edge crosses with probability `1/2`. The experiment is an efficient randomised algorithm (expectation; or amplify).

**Theorem 5.2.** Any `m` clauses have a truth assignment satisfying `≥ m/2` clauses. Random assignment; `Z_j = 1` if clause `j` is satisfied; `E[∑ Z_j] ≥ m/2`. If every clause has `≥ k` literals, guarantee `1 − 2^{−k}` (so MAX-3SAT gets `7/8` from this alone).

**Randomised rounding of the MAX-SAT LP.** Let `z_j` be the LP value of clause `j`.

**Lemma 5.3.** A clause with `k` literals is satisfied with probability `≥ p_k z_j` where `p_k = 1 − (1 − 1/k)^k ≥ 1 − 1/e`.

**Theorem 5.4.** LP + independent randomised rounding satisfies `≥ (1 − 1/e)` times OPT in expectation.

**Theorem 5.5.** Take the better of (uniform random assignment, LP rounding): `max{n1, n2} ≥ (3/4) ∑ z_j`. Hence a randomised **3/4-approximation**.

**Set cover** (standard, not a Motwani chapter). Greedy: `H_n ≤ ln n + 1` approximation. LP rounding: include set `i` independently with probability `x_i`; `O(log n)` rounds + Chernoff/union bound cover all elements w.h.p. with `O(log n)` approximation.

## Expanding graphs (Ch 5.3)

**Theorem 5.6.** For large `n`, an `(n, 18, 1/3, 2)` OR-concentrator exists (probabilistic method on random bipartite graphs).

**Theorem 5.7.** There is a bipartite `G(L,R,E)`, `|L|=n`, `|R|=2 log n`, such that every `n/2`-subset of `L` has `≥ 2 log n − n` neighbors in `R`, and max degree on `R` is `O(log n)`. Used for **probability amplification with few random bits**: `log n` bits, failure `≤ n / 2^{log n}` scale.

Existence ≠ uniform construction. Non-uniform algorithms may assume the expander as advice.

## Oblivious routing, few random bits (Ch 5.4)

**Theorem 5.8.** A randomised oblivious hypercube routing algorithm using `k` random bits has expected time `Ω(2^{−k} √N / n)`.

**Theorem 5.10.** There *exists* a scheme using `3n` random bits and expected time `≤ 15n` (non-uniform; the good set of deterministic algorithms is not efficiently constructible in the book).

## Lovász local lemma (Ch 5.5)

**Symmetric LLL.** Events `E_i` with `P(E_i) ≤ p`, each depending on at most `D` others. If `e p (D+1) ≤ 1`, then `P(∩ E_i^c) > 0`.

Algorithmic LLL is later (Moser–Tardos); Motwani treats the existential form and notes limited algorithmic applications as of 1995.

## Method of conditional probabilities (Ch 5.6) — derandomisation

Computation tree of random bits / assignment variables. At a node `a`, some child has conditional failure probability `≤` that of `a`. Always step to such a child. If the root has failure `< 1`, the path ends at a **good** leaf.

**Theorem 5.15.** When conditionals (or a **pessimistic estimator** dominating the failure probability, multiplicative along the tree) are efficiently computable, this yields a deterministic polynomial algorithm.

Set-balancing, MAX-SAT, RandAuto (Exercise) derandomise this way.

**Pairwise independence** is the other derandomisation axis: replace a large independent sample by an `O(log n)`-bit pairwise-independent sample, then enumerate the seed space if it is polynomial.

## Hermes

- Skill-index MAX-SAT style: random assignment / rounding for “satisfy most constraints”.
- Derandomise a randomised policy when the conditional expectation of the objective is computable (exact or pessimistic).
- Need expanders for amplification with few bits: Ch 5.3 + Ch 6.8.
