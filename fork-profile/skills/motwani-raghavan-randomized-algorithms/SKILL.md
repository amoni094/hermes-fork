---
name: motwani-raghavan-randomized-algorithms
description: Use when bounding error probs or randomised design.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [randomized-algorithms, concentration, hashing, approximation]
    related_skills: [clrs-algorithms, lattimore-bandit-algorithms, katz-lindell-modern-cryptography, shalev-shwartz-understanding-ml, information-theory-for-agents]
---

# Randomized Algorithms (Motwani & Raghavan, 1995)
**Authors**: Rajeev Motwani, Prabhakar Raghavan | **Pages**: ~476 + appendices | **Chapters**: 14 | **Press**: Cambridge

Toolkit for bounding error probabilities, designing randomised structures, and proving approximation / competitiveness. Synthesized from Motwani & Raghavan (1995); not the book text. The source PDF is a 491-page Paper Capture scan — theorems below are reconstructed from recovered pdftotext plus canonical statements, not verbatim pages.

Load [cheatsheet.md](cheatsheet.md) for decision rules, [patterns.md](patterns.md) for algorithms, [glossary.md](glossary.md) for terms, or a `chapters/chNN-*.md` file for worked detail.

## Hermes applications (use these first)

1. **TF-IDF / skill-index similarity** — Treat skill vectors as high-d points. A random projection of dimension `k = O(ε⁻² log n)` preserves pairwise distances to factor `(1±ε)` w.h.p. (Johnson–Lindenstrauss; concentration as in Ch 4). Do not brute-force cosine over the full TF-IDF matrix when approximate nearest-skill is enough.
2. **Beta-bandit posteriors** — After `n` Bernoulli trials with mean `p`, Chernoff (Thm 4.1–4.2) gives PAC sample complexity: `n ≥ (3/ε²) ln(2/δ)` suffices for `|p̂ − p| < ε` with probability `≥ 1−δ`. Do not treat a Beta posterior as “reliable” until this `n` (or an equivalent Hoeffding/Chernoff check) holds.
3. **Routing / load balancing** — Pairwise-independent hashing (Ch 8.4, Ch 12) is enough for second-moment load bounds (Chebyshev). Stronger independence is not required for `O(√(n log n))` max-load style arguments. Use 2-universal `h(x) = (ax+b mod p) mod m` for weight buckets.
4. **Cron / timeout** — For nonnegative runtime `T`, Markov: `P(T > t) ≤ E[T]/t`. Set timeout `t = E[T]/δ` to cap overrun probability at `δ`. If variance is known, Chebyshev is tighter: `P(|T−μ| ≥ λ) ≤ σ²/λ²`. Do not use Chernoff unless trials are independent (or a martingale / Azuma applies).

## When to use

- Bounding failure of a randomised check, retry loop, or Monte Carlo estimator
- Choosing Las Vegas vs Monte Carlo, or amplifying success probability
- Hashing, skip lists, fingerprinting, random sampling
- Approximation ratios (MAX-SAT, rounding) or online competitiveness
- Derandomising via conditional expectations or pairwise independence

Don't use for: measure-theoretic probability (use billingsley / grimmett-stirzaker); bandit regret algorithms (use lattimore-bandit-algorithms); crypto reductions (use katz-lindell).

---

## Core frameworks

### Las Vegas vs Monte Carlo (Ch 1.2)

- **Las Vegas**: always correct; runtime is the random variable (RandQS). Efficient if expected time is polynomial.
- **Monte Carlo**: may err; error probability is bounded (contraction min-cut). One-sided vs two-sided error.
- Las Vegas = Monte Carlo with error 0. If a Monte Carlo algorithm with success `y(n)` has a `t(n)` verifier, convert: repeat until a solution verifies; expected time `(T(n)+t(n))/y(n)` (Exercise 1.3, geometric).
- **Amplification**: independent repeats of a Monte Carlo algorithm with failure `p` drive failure to `p^k`. Min-cut: one run succeeds with `≥ 2/n²`; `n²/2` repeats → failure `≤ 1/e`.

### Foiling an adversary

A randomised algorithm is a distribution over deterministic algorithms. An adversary that wrecks one deterministic strategy cannot wreck a random one in expectation. Direct in game-tree evaluation (Ch 2), PCP (Ch 7), online paging (Ch 13).

### Markov / Chebyshev / Chernoff (Ch 3–4)

For `X ≥ 0`, **Markov**: `P(X ≥ t) ≤ E[X]/t`. Only needs nonnegativity. Weak; first tool for timeouts and cover times.

**Chebyshev**: `P(|X−μ| ≥ t) ≤ Var(X)/t²`. Needs second moment. Pairwise independence is enough to compute variance of a sum (cross terms vanish). Use for two-point sampling and 2-universal hashing.

**Chernoff** (independent Poisson trials `X_i ∈ {0,1}`, `X=∑ X_i`, `μ=E[X]`):

- Upper: `P(X > (1+δ)μ) ≤ (e^δ / (1+δ)^{1+δ})^μ` (Thm 4.1)
- Lower: `P(X < (1−δ)μ) ≤ exp(−μ δ² / 2)` for `0<δ<1` (Thm 4.2)
- Also `P(X > (1+δ)μ) ≤ exp(−c(δ) μ δ²)` with `c(δ)=((1+δ)ln(1+δ)−δ)/δ²` (Thm 4.3)

Rule: Markov if only `E[X]`; Chebyshev if variance / pairwise independence; Chernoff if independent (or negatively associated) bounded trials. Azuma (Thm 4.16) if a martingale with bounded differences.

### Randomised Quicksort (Thm 1.1)

Pick pivot uniformly. Indicator `X_{ij}=1` iff ranks `i,j` are compared ⇔ one of them is the first pivot in `{i,…,j}`. `P_{ij}=2/(j−i+1)`. Linearity ⇒ expected comparisons `≤ 2n H_n = O(n log n)` on **every** input (not average-case over inputs).

### Contraction min-cut (Ch 1.1, Ch 10.2)

Repeatedly contract a random edge until 2 vertices remain. A fixed min-cut of size `k` survives with probability `> 2/n²`. Monte Carlo; amplify by repetition. Karger-style recursive contraction (Ch 10.2) improves the time/error tradeoff vs network flow.

### Probabilistic method (Ch 5)

1. A r.v. takes some value `≥` its expectation and some `≤` it.
2. If `P[object is good] > 0`, a good object exists.

MAX-SAT: random assignment satisfies `m/2` clauses in expectation (Thm 5.2); if every clause has `≥ k` literals, guarantee `1−2^{-k}`. LP + randomised rounding: `(1−1/e)` (Thm 5.4). Take the better of the two → `3/4` (Thm 5.5). **Set cover** (standard greedy, not a Motwani chapter): `H_n ≤ ln n + 1` approximation; randomised rounding of the LP gives `O(log n)` with Chernoff + union bound.

### Derandomisation

- **Method of conditional expectations** (Ch 5.6): walk an assignment tree, always taking a child whose conditional failure probability is no larger than the parent’s. Yields a deterministic algorithm whenever the conditional can be computed (or pessimistic estimators).
- **Pairwise independence / two-point sampling** (Ch 3.4, Ch 8.4, Ch 12): `O(log n)` bits replace full independence for variance bounds and MIS marking.

### Hashing (Ch 8.4)

Family `H` is **2-universal** if for `x ≠ y`, `P_{h∈H}[h(x)=h(y)] ≤ 1/m` (or `O(1/m)`). Construction: `h_{a,b}(x) = ((ax+b) mod p) mod m`. Strong 2-universality ≡ pairwise independence of hash values. **Perfect hashing**: injective on a static set `S`; two-level FKS gives `O(1)` worst-case lookup in `O(n)` expected space.

### Fingerprinting (Ch 7)

Map a long object to a short random fingerprint. Freivalds: verify `AB=C` for matrices by multiplying a random vector. Polynomial identity: evaluate at a random point (Schwartz–Zippel). String equality / pattern matching: compare fingerprints; collision probability `≤` length / field size. Cheaper than comparing the objects.

### Random walks (Ch 6)

2-SAT: random walk on assignments hits a satisfying assignment in expected `O(n²)` steps. Cover time of an undirected graph `≤ 2m(n−1)` (Aleliunas et al.). Electrical networks: commute time `h_{st}+h_{ts} = 2m R_{st}`. Expander walks amplify Monte Carlo success using few random bits (Ch 6.8).

### Online algorithms (Ch 13)

Paging: deterministic competitiveness `≥ k` (Thm 13.1). Against oblivious adversaries, Marker is `2 H_k`-competitive (Thm 13.3); lower bound `H_k`. Adaptive offline adversaries collapse randomised to deterministic (Thm 13.4). **Ski rental** (classic 2-competitive; book treats paging/k-server instead): rent until cumulative rent = buy cost, then buy. Randomised ski-rental approaches `e/(e−1)`.

### Sampling and estimation (Ch 9.9, Ch 11)

Estimator theorem: to get a `(1±ε)`-approximation with probability `≥ 1−δ`, take `O(σ² ε⁻² log(1/δ))` independent samples (or Chernoff if bounded). FPRAS for DNF counting (Karp–Luby–Madras). Mixing of a Markov chain → almost-uniform sample → approximate count.

---

## Chapter index

| # | Title | Key frameworks |
|---|-------|----------------|
| [ch01](chapters/ch01-introduction.md) | Introduction | RandQS, min-cut, Las Vegas/Monte Carlo, RP/BPP |
| [ch02](chapters/ch02-game-theoretic-techniques.md) | Game-theoretic techniques | Game-tree evaluation, Yao minimax |
| [ch03](chapters/ch03-moments-and-deviations.md) | Moments and deviations | Markov, Chebyshev, two-point sampling, coupon collector |
| [ch04](chapters/ch04-tail-inequalities.md) | Tail inequalities | Chernoff, routing, martingales, Azuma |
| [ch05](chapters/ch05-probabilistic-method.md) | The probabilistic method | MAX-SAT, expanders, Lovász local lemma, conditional expectations |
| [ch06](chapters/ch06-markov-chains-and-random-walks.md) | Markov chains and random walks | 2-SAT, cover times, expanders, amplification |
| [ch07](chapters/ch07-algebraic-techniques.md) | Algebraic techniques | Fingerprinting, Freivalds, Schwartz–Zippel, PCP |
| [ch08](chapters/ch08-data-structures.md) | Data structures | Treaps, skip lists, universal/perfect hashing |
| [ch09](chapters/ch09-geometric-algorithms.md) | Geometric algorithms and LP | Incremental construction, random sampling |
| [ch10](chapters/ch10-graph-algorithms.md) | Graph algorithms | APSP, min-cut, MST |
| [ch11](chapters/ch11-approximate-counting.md) | Approximate counting | FPRAS, DNF, permanent, volume |
| [ch12](chapters/ch12-parallel-and-distributed.md) | Parallel and distributed | MIS, isolating lemma, pairwise independence |
| [ch13](chapters/ch13-online-algorithms.md) | Online algorithms | Paging, adversaries, k-server, ski rental |
| [ch14](chapters/ch14-number-theory-and-algebra.md) | Number theory and algebra | RSA, primality, abundance of witnesses |

## Topic index

- **Amplification** → ch01, ch06
- **Approximation / MAX-SAT / rounding** → ch05
- **Azuma / martingales** → ch04
- **Chernoff** → ch04
- **Chebyshev / Markov** → ch03
- **Coupon collector** → ch03
- **Derandomisation** → ch05, ch12
- **Fingerprinting** → ch07
- **Hashing (universal, perfect)** → ch08
- **Las Vegas / Monte Carlo** → ch01
- **Load balancing / routing** → ch04, ch05
- **Min-cut** → ch01, ch10
- **Online / paging / ski rental** → ch13
- **Pairwise independence** → ch03, ch08, ch12
- **Primality** → ch14
- **Probabilistic method / LLL** → ch05
- **Quicksort** → ch01
- **Random walks / mixing** → ch06, ch11
- **Sampling / FPRAS** → ch09, ch11
- **Skip lists / treaps** → ch08

## Supporting files

- [glossary.md](glossary.md) — terms
- [patterns.md](patterns.md) — algorithms and techniques
- [cheatsheet.md](cheatsheet.md) — decision rules and bound table

## Scope & limits

Book content (1995). JL lemma, modern streaming sketches, and post-2000 approximation (Goemans–Williamson 0.878, etc.) are descendants — apply via Chernoff / random projection, and say so. Do not copy raw book text into prompts.
