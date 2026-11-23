# Chapter 8: Competitive Analysis and Zero-Sum Games

## Core Idea
The competitive ratio is the value of a zero-sum game. **Yao’s principle** turns a distributional lower bound on deterministic algorithms into a lower bound on randomized algorithms vs OBL.

## Key Concepts
- **Two-person zero-sum game.** Players: ALG (minimizes cost ratio or cost) and ADV (maximizes). Payoff `M(D, σ) = D(σ) / OPT(σ)` (or cost, then normalize).
- **Minimax theorem (von Neumann).** For finite matrix games,
  `max_q min_p p^T M q = min_p max_q p^T M q = v`.
- **Infinite games.** Request sequences are unbounded; minimax may fail. §8.2: generalizations (Fan, etc.) under compactness / semicontinuity. Use finite-n truncations then let n→∞ with care.
- **Yao’s principle (Yao 1977).** For randomized ALG vs OBL:
  ```
  inf_{randomized ALG} sup_σ E[ALG(σ)] / OPT(σ)
    ≥ inf_{DET D} E_{σ~q}[ D(σ) / OPT(σ) ]
  ```
  for every distribution `q` on inputs. So: pick a hard `q`, prove every deterministic D is bad in expectation, conclude every randomized ALG is at least that bad vs OBL.
- **Paging revisited (§8.4).** The `H_k` lower bound is the Yao application: a suitable distribution over sequences of k+1 pages.

## Frameworks and Methods
- **Lower-bound recipe (randomized, OBL).**
  1. Choose a distribution `q` on `σ` (often i.i.d. on a small universe).
  2. Compute OPT(`σ`) (or a lower bound) in expectation.
  3. For an arbitrary DET D, lower-bound `E_q[D(σ)]` (often by symmetry: all DET look the same).
  4. Ratio of those expectations (or E[D/OPT]) is the LB.
- **Do not use Yao against ADON/ADOFF.** Yao is an OBL (input distribution independent of coins) tool. Adaptive adversaries need game-tree arguments (Ch. 7, 11.2).
- **Cruel adversary** is the DET special case: a Dirac `q` on one bad `σ`, or an adaptive construction of `σ`.

## Key Results and Theorems

**Minimax (finite).** Value exists; optimal mixed strategies exist for both players.

**Yao.** The expected cost of the best DET algorithm under a worst input distribution lower-bounds the randomized OBL competitive ratio.

**Paging.** Randomized OBL ratio ≥ `H_k` (matches MARK up to a factor 2).

**List update.** Yao yields the 1.5 randomized LB (Ch. 2).

## Key Equations
- Finite matrix: `v = max_q min_i (M q)_i = min_p max_j (p^T M)_j`.
- Yao (cost form): `inf_p sup_σ E_p[ALG] ≥ sup_q inf_D E_q[D]`.
- Harmonic: `H_k = ∑_{i=1}^k 1/i`.

## Worked Example (paging sketch)
Universe of k+1 pages, requests i.i.d. uniform. Any DET cache of k pages misses with probability 1/(k+1) each step in the limit, but a more careful *phase* distribution gives the harmonic: each new distinct page in a k-set is missed by DET with probability proportional to remaining unmarked slots → `H_k` expected misses per OPT miss.

## Hermes application
To claim “no router can beat ratio c vs an oblivious query log,” run Yao: exhibit a distribution over query sequences such that every deterministic skill-router has expected cost ≥ c · OPT. Do not sample an adaptive user and call it Yao.

## Anti-patterns
- **Yao with an adaptive distribution** (`q` that depends on ALG’s previous answers). That is not Yao; that is ADON.
- **Using min_D E_q[D/OPT] as an *upper* bound.** Yao only lower-bounds the randomized ratio.
- **Forgetting OPT in the denominator** when OPT is itself random under `q`.
