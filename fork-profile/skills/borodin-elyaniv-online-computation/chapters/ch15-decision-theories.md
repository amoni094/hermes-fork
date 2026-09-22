# Ch 15 — Decision Theories of Online Computation

## Axiomatic foundations of competitive ratio

**Desiderata (B&E §15.1).** A good performance measure should be:
1. **Normalization**: optimal offline achieves ratio 1.
2. **Scale invariance**: ratio unchanged under cost rescaling.
3. **Consistency**: better online behavior → better ratio.
4. **Limit existence**: ratio well-defined for any input length n → ∞.

Competitive ratio satisfies all four. Absolute regret (additive) fails scale invariance.

## Loose vs strict competitiveness

**Loose (α-competitive with additive constant):** ALG(σ) ≤ c·OPT(σ) + α for fixed α ≥ 0.
**Strict (strongly c-competitive):** ALG(σ) ≤ c·OPT(σ) for all σ with OPT(σ) ≥ 0.

For most problems (paging, list update, k-server) strict and loose coincide in the limit but differ for small OPT. Loose is easier; strict is more demanding (α=0).

## Beyond pure competitive ratio

**Average-case / smoothed analysis.** Ratio on random inputs; weaker guarantee. Useful when adversary model is unrealistic (e.g. benign web crawl patterns).

**Bijective / average analysis (Angelopoulos et al.).**
- Compare ALG vs OPT on every permutation of the input.
- Eliminates "unfair" adversarial orderings; gives tighter list-update ratios.

**Diffuse adversary model.**
- Adversary is probabilistic (chooses σ from a distribution).
- Bridges competitive ratio and Bayesian regret bounds.
- Relevant for Hermes: if LLM task distribution is known to be stationary, use Bayesian (Beta-bandit); if adversarial, use EXP3 / FTRL competitive-ratio guarantees.

## Ski rental revisited (lease scheduling)

**Lease model (Lotker et al.).**
- Multiple lease durations L_1 < L_2 < … < L_k; cost of lease i = c_i.
- Decision at each step: buy a lease of some duration or continue paying per-step.
- Optimal deterministic ratio: 2 (binary rent-or-buy).
- With k > 2 lease options: opt. ratio approaches e/(e−1) ≈ 1.582 in the limit.

**Hermes application (TTL adjuster).**
- Recall-miss-ttl-adjuster manages memory TTL (lease duration) dynamically.
- MRAS gain cap = 0.10 prevents oscillation (loose analogue of rent-or-buy instability).
- Optimal TTL selection = choose L_i to minimize E[total cost] given hit-rate distribution.
- With MRAS: treat each TTL level as a "lease option"; switch conservatively (≤ 10% adjustment per step).

## Primal-dual in online settings

**Online primal-dual method (Buchbinder & Naor).**
- Maintain primal (ALG) and dual (OPT lower bound) simultaneously.
- At each step: increase primal cost Δp, increase dual Δd ≥ Δp / c (ensures ratio ≤ c).
- Used to prove LRU is k-competitive (paging primal-dual), weighted caching, online matching.

**Why it matters for Hermes.**
- Any new online script (cron scheduler, context eviction, tool auth gate) should be analyzed via primal-dual to establish a provable ratio before deployment.
- Method: write out the LP relaxation of the offline optimum; pair each ALG decision with a dual certificate; verify the dual stays feasible.
