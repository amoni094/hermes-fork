# Cheatsheet — Borodin & El-Yaniv

## Competitive ratios at a glance

Problem                     | Algorithm          | Ratio        | Adversary  | Notes
----------------------------|--------------------|--------------|------------|---------------------------
Ski rental (buy cost B)     | Rent B-1 then buy  | 2 - 1/B      | det.       | optimal det.
Ski rental                  | Randomized         | e/(e-1)≈1.58 | OBL        | optimal rand.
List update                 | MTF                | 2            | any DET    | Sleator-Tarjan
List update                 | BIT                | 7/4          | OBL        | barely-random
List update                 | COMB               | 8/5          | OBL        | combination
Paging (cache k)            | LRU/FIFO/FWF       | k            | det.       | all conservative
Paging                      | LFD (offline)      | 1            | —          | Belady OPT
(h,k)-paging                | LRU                | k/(k-h+1)    | det.       | h < k pages preloaded
Paging randomized           | MARK               | 2 H_k        | OBL        | lower bound H_k
k-server                    | WFA                | 2k-1         | det.       | open conjecture: k
k-server on line            | Double Coverage    | k            | det.       | tight
k-server randomized         | HARMONIC (uniform) | H_k          | OBL        | optimal on unif. metric
MTS (N states)              | WFA                | 2N-1         | det.       | tight
Load balancing (m machines) | Greedy             | 2 - 1/m      | det.       | optimal
Bin packing                 | First Fit          | 1.7 asymp.   | det.       |
Experts (N)                 | Exp. Weights       | regret O(√T log N) | —   | additive
Portfolio (K assets)        | FTRL/Cover         | regret O(k log T)  | —   | log-wealth


## Adversary hierarchy

OBL (weakest) ≤ ADON ≤ ADOFF (strongest) = DET

Randomization helps:  against OBL (most), ADON (some), ADOFF (none).
Composition:          if ALG is α vs OBL and β vs ADON → α·β vs ADOFF.


## Key reductions

Regret → Ratio:    R(ALG) = 1 + R_T/OPT    (when OPT > 0)
Ratio → Regret:    regret ≤ (c-1)·OPT       (when c-competitive)
Yao lower bound:   max_dist min_DET E[cost]/OPT = R_OBL(best rand. ALG)


## When to use which model

Use competitive ratio when:
  - decisions are irreversible (evict, reject, buy)
  - adversary can be worst-case (no distributional assumption)
  - ratio vs offline OPT must be multiplicative (bounded by c·OPT)

Use regret / FTRL when:
  - loss is additive over rounds
  - OPT is a fixed offline strategy (best-fixed-action in hindsight)
  - distributional guarantee acceptable (vs OBL)

Use Bayesian (Beta-bandit) when:
  - environment is stochastic (i.i.d. rewards)
  - no adversarial assumption needed
  - Thompson sampling has O(√T·K) Bayesian regret (Russo & Van Roy)

DO NOT mix models: Beta-bandit posterior ≠ OBL-adversary guarantee.


## Hermes surface → model mapping

routing-weight-updater  →  FTRL/experts;  regret O(√T log K);  K = providers
skill-router            →  k-server;       ratio H_k (HARMONIC) or k (greedy)
context eviction        →  paging;         ratio 2H_k (MARK) or k (LRU)
cron priority           →  list update;    ratio 2 (MTF) or 8/5 (COMB)
memory TTL              →  ski rental;     ratio 2-1/B det., e/(e-1) rand.
cron bin packing        →  bin packing;    ratio 1.7 (First Fit)
tool auth gate          →  call admission; ratio O(log^2 n) rand. on expanders


## Potential function cookbook

Problem         | Potential Φ                      | Proof technique
----------------|----------------------------------|------------------
List update MTF | Σ inversions between ALG and OPT | amortized (Sleator-Tarjan)
Paging LRU      | # pages in ALG but not OPT cache | conservative algorithms thm.
k-server DC     | Σ matching dist + Σ server dists | primal-dual or potential
Ski rental      | None needed; direct analysis     | case split on OPT decision
MTS / WFA       | Work function difference         | WFA definition
