# Ch 12 — Parallel and Distributed Algorithms

## PRAM sorting (Ch 12.1–12.2)

**Theorem 12.2 (BoxSort).** With probability `≥ 1 − exp(−log^b n)`, randomised PRAM sort finishes in `O(log n)` time.

## Maximal independent set (Ch 12.3)

Luby’s algorithm: each vertex `v` marks itself with probability `1/(2 d(v))`; a marked vertex joins `S` if no higher-priority (or lower-id / higher-degree) marked neighbour exists; delete `S ∪ N(S)`; repeat.

**Good vertices** (Def 12.3): at least `d(v)/3` neighbours of degree `≤ d(v)`. A constant fraction of edges are good (Lemma 12.6). Each iteration deletes a constant fraction of good edges in expectation ⇒ `O(log n)` iterations (Thm 1.3 geometric).

**Theorem 12.7.** EREW PRAM MIS in expected `O(log² n)` time with `O(n+m)` processors.

**Pairwise independence:** the only step needing full independence is the marking (Lemma 12.3). A slightly weaker Lemma 12.5 holds with pairwise-independent marks, so `O(log n)` random bits suffice; the seed can be enumerated for NC derandomisation.

## Perfect matchings (Ch 12.4)

**Tutte’s theorem (Thm 12.8).** The Tutte matrix is singular (as a polynomial) iff no perfect matching.

**Isolating Lemma (Lemma 12.10, Mulmuley–Vazirani–Vazirani).** Set system `(X,F)`, `|X|=m`. Assign each element a random weight in `{1,…,2m}`. Then `P[unique minimum-weight set in F] ≥ 1/2`.

Use: isolate a unique min-weight perfect matching; then algebraic NC inversion recovers its edges (Thm 12.13, success `≥ 1/2`).

## Choice coordination and Byzantine agreement (Ch 12.5–12.6)

Randomisation breaks symmetry among processors without a shared coin of unbounded quality.

**Theorem 12.14.** ASYNCH-CCP: total cost `> c` with probability `≤ 2^{-Ω(c)}`.

**Theorem 12.15.** ByzGen reaches agreement in expected `O(1)` rounds (constant in `n`, for the randomised protocol).

## Hermes

- Load-balance / mark tasks independently: pairwise-independent hashes, `O(log n)` bits (user application 3).
- Need a unique winner among many feasible configs: Isolating Lemma (random weights), not an arbitrary tie-break.
