# Chapter 7: Request–Answer Games

## Core Idea
A uniform abstraction of online problems: requests from a set `R`, answers from sets `A_i`, cost `cost_n(σ, a)`. Adversaries are pairs `(Q, S)` — a requesting component and a servicing component. This is the formal home of OBL / ADON / ADOFF and of the αβ theorem.

## Key Concepts
- **Request–answer system:** request set `R`; finite nonempty answer sets `A_1, A_2, …`; cost functions `cost_i`.
- **Deterministic online ALG:** functions `g_i : R^i → A_i`. Answer sequence `ALG[σ] = (a_1,…,a_n)` with `a_j = g_j(r_1,…,r_j)`. Cost `ALG(σ) = cost_n(σ, ALG[σ])`.
- **Randomized online ALG:** a **mixed strategy** — a distribution over deterministic online algorithms. Then `ALG[σ]` and `ALG(σ)` are random variables.
- **Adversary = (Q, S).** `Q` builds `σ`; `S` answers it.
- **OBL:** `Q` picks `σ` without ALG’s coins; `S` = offline OPT.
- **ADON:** `Q` may depend on past answers; `S` answers **online** (the adversary is itself an online algorithm, possibly randomized).
- **ADOFF:** `Q` may depend on past answers; `S` = offline OPT on the realized `σ`.
- **Finite answer sets** (Remark 7.1): needed so mixed strategies and compactness arguments work; paging, list update, k-server discretizations fit.

## Frameworks and Methods
- **Game tree (adaptive).** At step t: Q picks `r_t` (possibly using past `a_<t`); ALG (and, if ADON, S) pick answers; cost accumulates.
- **Relating adversaries (§7.3).** Simulate a stronger adversary by composing weaker ones; the product of ratios appears.
- **Derandomization vs ADOFF.** An ADOFF-competitive randomized ALG yields a DET algorithm with the same ratio (the mixture cannot beat the best pure strategy against an adversary that sees the coins after the fact).

## Key Results and Theorems

**Adversary chain.**
```
R_OBL(ALG) ≤ R_ADON(ALG) ≤ R_ADOFF(ALG)
```
and `inf_ALG R_ADOFF(ALG) = inf_DET R(DET)`.

**Randomization vs ADOFF.** If a randomized ALG is c-competitive against ADOFF, there exists a deterministic c-competitive algorithm.

**Product theorem (Ben-David–Borodin–Karp–Tardos–Wigderson).** If ALG is `α`-competitive vs OBL and `β`-competitive vs ADON, then it is `αβ`-competitive vs ADOFF.

**Paging corollary.** Randomized paging cannot beat k against ADOFF; MARK’s `2 H_k` is an OBL theorem.

## Key Equations
- `a_j = g_j(r_1,…,r_j)` (causal; no look-ahead).
- `E[ALG(σ)] ≤ α OPT(σ) + a` (OBL).
- `E[ALG] ≤ β E[ADON] + b` (ADON; both random).
- ADOFF: `E[ALG(σ)] ≤ γ OPT(σ) + c` with `σ` itself random.

## Worked Example (Example 7.1, paging)
`R` = page IDs; `A_i` = which page to evict (or “none” on hit). OBL fixes the page sequence. ADON may request a page that just got evicted. ADOFF does the same *and* pays Belady on the final sequence — the k lower bound applies.

## Hermes application
Name the adversary when you quote a ratio for routing:
- **Logged replay of past queries** = OBL (FTRL regret vs that log is an OBL statement).
- **User adapts to the skill you just loaded** = ADON.
- **Offline eval on the realized transcript with hindsight OPT** after an adaptive user = ADOFF, so DET ratios apply; randomization will not improve the published number.

## Anti-patterns
- **Using OBL ratios in an interactive loop** without saying so.
- **Treating ADON’s servicing as OPT.** ADON pays an *online* servicing cost, which can be larger than OPT; that is why ADON is weaker than ADOFF.
- **Infinite / continuous answer sets** (raw softmax over R^d) without discretization — the request–answer theorems assume finite `A_i`.
