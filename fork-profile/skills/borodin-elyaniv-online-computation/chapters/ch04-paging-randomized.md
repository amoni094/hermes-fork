# Chapter 4: Paging — Randomized Algorithms

## Core Idea
Against an **oblivious** adversary, randomization improves paging from `k` to `Θ(H_k)` (`H_k = ∑_{i=1}^k 1/i ~ ln k`). Against **adaptive-offline**, randomization does not help. This chapter introduces the three adversaries used for the rest of the book.

## Key Concepts
- **OBL (oblivious):** `σ` fixed in advance. `E[ALG(σ)] ≤ c · OPT(σ) + α`. `OPT(σ)` deterministic.
- **ADON (adaptive-online):** next request may depend on ALG’s previous answers; the adversary must **serve online**. Both `ALG(σ)` and `ADON(σ)` are random (they depend on coins).
- **ADOFF (adaptive-offline):** next request may depend on previous answers; servicing is **offline OPT** on the realized `σ`. Strongest.
- **RANDOM:** on a miss, evict a uniformly random resident page.
- **MARK:** randomized marking — on a miss, evict a uniformly random *unmarked* page. (Deterministic marking left the unmarked choice arbitrary; here it is random.)
- **H_k:** kth harmonic number. Randomized paging lower bound `H_k`; MARK is `2 H_k`.

## Frameworks and Methods
- **Adversary game tree.** OBL chooses `σ` then ALG’s coins fire. ADON interleaves request and both players’ answers. ADOFF interleaves request with ALG’s answer, then OPT is computed at the end.
- **Phase analysis for MARK.** In a phase with `k` distinct pages, expected misses of MARK are `H_k` plus a term for “clean” vs “stale” pages, totaling ≤ `2 H_k` times OPT’s phase cost.
- **Yao for the H_k lower bound** (detailed in Ch. 8.4): a distribution over sequences such that every deterministic paging ALG has expected cost ≥ `H_k · OPT`.

## Key Results and Theorems

**Definition 4.1 (randomized c-competitive vs ADV).**
```
E[ALG(σ)] ≤ c · ADV(σ) + α
```
with the expectation over ALG’s coins; for ADON/ADOFF the right-hand side may be an expectation too (Ch. 7 makes this precise).

**RANDOM** is k-competitive (no improvement over DET in the worst case for this naive rule against adaptive; vs OBL it is still Θ(k) in the book’s analysis). Use MARK, not RANDOM, for the logarithmic improvement.

**Theorem (MARK).** MARK is **2 H_k-competitive** against an oblivious adversary.

**Theorem (randomized paging LB).** Every randomized paging algorithm has competitive ratio ≥ **H_k** vs OBL.

**Power of adversaries.** `R_OBL ≤ R_ADON ≤ R_ADOFF = R_DET = k` for paging. MARK’s `2 H_k` is an OBL number; do not quote it vs a user who adapts to your evictions.

## Key Equations
- `H_k = 1 + 1/2 + … + 1/k ≤ ln k + 1`.
- MARK: `E[misses in a phase] ≤ H_k + H_k` (stale + new) = `2 H_k` vs ≥ 1 OPT miss.
- Cruel k+1-page loop: DET ratio k; a random eviction on that instance still has expected miss rate 1 on each request after fill.

## Worked Example
`k = 2`, `H_2 = 1.5`, `2 H_2 = 3` (still < 2 only when k large: already for k=2, DET is 2 and 2 H_2 = 3, so MARK’s OBL bound is *worse* than DET’s k at k=2; the gain appears for large k, e.g. k=16, H_16≈3.38, 2H≈6.8 ≪ 16).

## Hermes application
- **beta-bandit as adversarial bandit:** the right analogue of paging-vs-OBL is EXP3 / FTRL, not a Beta-Bernoulli posterior. Beta assumes i.i.d. rewards (Ch. 5 distributional). If routing losses are chosen by an adversary (or a shifting user), use OBL randomized-online guarantees.
- **Tool/context eviction:** MARK (random among unmarked / not-in-current-working-set) rather than RANDOM.

## Anti-patterns
- **Quoting 2 H_k against ADON.** Invalid.
- **Equating RANDOM with MARK.** MARK’s marks encode phase/working-set structure.
- **Using Thompson/Beta and calling it competitive analysis.** Different model.
