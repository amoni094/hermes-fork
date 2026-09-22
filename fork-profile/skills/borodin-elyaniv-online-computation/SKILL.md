---
name: borodin-elyaniv-online-computation
description: "Use when analysing competitive ratio or FTRL/regret."
---

# Borodin & El-Yaniv — Online Computation and Competitive Analysis (Cambridge 1998/2005)

Graduate reference for **worst-case online algorithms**. Measure ALG against an offline OPT that sees the whole request sequence. Source PDF at `~/Downloads/Online Computation and Competitive Analysis.pdf` is an I.R.I.S. image scan (217 pages, no text layer); TOC and Ch.1/4/7 were OCR-checked; remaining statements reconstructed from the same edition. Verify theorem numbers against the chapter file before citing.

Related: [lattimore-bandit-algorithms](../research/lattimore-bandit-algorithms/SKILL.md) (EXP3 / adversarial bandits), [puterman-mdp](../research/puterman-mdp/SKILL.md) (offline sequential decisions).


## Model Routing

Competitive-ratio / adversary / WFA derivation: magistral-small-latest (mistral). Hermes routing/FTRL implementation: grok-4.6 workers via delegate_task.


## Core framework

**Online vs offline.** ALG sees requests `r_1,…,r_t` one at a time and must answer `a_t` before `r_{t+1}`. OPT sees the whole `σ = (r_1,…,r_n)`.

**Competitive ratio (deterministic).** ALG is *c-competitive* if ∃ additive `α` such that for every `σ`:

```
ALG(σ) ≤ c · OPT(σ) + α
```

Strictly *c-competitive* if `α = 0`. Infimum such *c* is `R(ALG)`. For profit-maximization invert (`ALG ≥ OPT/c − α`).

**Randomized.** `E[ALG(σ)] ≤ c · ADV(σ) + α`, expectation over ALG’s coins. `ADV(σ)` depends on the adversary (Ch. 4, 7):

| Adversary | Request generation | Servicing | Power |
|-----------|-------------------|-----------|-------|
| **Oblivious (OBL)** | Whole `σ` fixed in advance; no coins of ALG | OPT offline | Weakest |
| **Adaptive-online (ADON)** | Next `r_t` may depend on `a_1,…,a_{t-1}` | Adversary serves *online* | Middle |
| **Adaptive-offline (ADOFF)** | Next `r_t` may depend on past answers | OPT offline on realized `σ` | Strongest |

`R_OBL ≤ R_ADON ≤ R_ADOFF`. Randomization does **not** help against ADOFF (`R_ADOFF = R_DET`). If ALG is `α` vs OBL and `β` vs ADON, it is `αβ` vs ADOFF (Ch. 7).

**Regret vs ratio.** Regret is additive: `ALG − OPT ≤ R_T`. Competitive ratio is multiplicative. FTRL with regret `R_T` is `1 + R_T/OPT`-competitive when OPT > 0; use ratio when OPT can be small or the guarantee vs hindsight must be multiplicative (ski rental, paging, portfolios).


## Hermes map (load the matching chapter)

| Hermes surface | Online problem | Chapter |
|----------------|----------------|---------|
| FTRL routing-weight updater | Experts / weighted portfolio: ratio bounds regret vs offline-optimal routing | 14, 15 |
| Skill router | *k*-server: skills = servers, queries = requests on a relatedness metric | 10, 11 |
| Cron / skill-cache | List update: MTF-cache frequently used scripts | 1, 2 |
| Paging of context / tools | LRU / MARK / (h,k)-paging | 3, 4, 5 |
| beta-bandit / EXP3 | Adversarial bandit = online learning vs OBL; not stochastic Beta | 4, 7, 8 |
| Config-space search | Metrical task systems + work function | 9 |


## Decision table: which tool?

```
Need a worst-case guarantee vs hindsight OPT?
├─ multiplicative (paging, ski, k-server, MTS) → competitive ratio; name the adversary
├─ additive (experts, FTRL, bandits with bounded loss) → regret; convert to ratio if OPT ≫ R_T
└─ distributional (Markov paging, i.i.d. bandits) → Ch. 5 / Lattimore; do not call it competitive

Need a lower bound?
├─ deterministic → cruel / adaptive adversary construction (Ch. 1.5, 3, 10.3)
└─ randomized vs OBL → Yao: hard distribution over σ, lower-bound every DET (Ch. 8.3)
```


## Landmark ratios (memorize)

| Problem | Algorithm | Ratio | Notes |
|---------|-----------|-------|-------|
| Ski rental (buy = *B*) | rent *B*−1 then buy | `2 − 1/B` | det. optimal |
| Ski rental | randomized | `e/(e−1)` | vs OBL |
| List update | MTF | 2 | Sleator–Tarjan; TRANS not competitive |
| List update | BIT / COMB | 7/4 / 8/5 | vs OBL |
| Paging, cache *k* | LRU, FIFO, FWF, CLOCK | *k* | conservative / marking; LFU/LIFO not competitive |
| Paging | LFD | 1 (offline) | Belady: evict farthest next use |
| (*h,k*)-paging | LRU | `k/(k−h+1)` | |
| Paging randomized | MARK | `2 H_k` | vs OBL; lower bound `H_k` |
| MTS, *N* states | Traversal / WFA | `8(N−1)` / `2N−1` | LB `2N−1` |
| *k*-server | WFA | `2k−1` | conjecture: *k*; det. LB *k* |
| *k*-server on a line | Double Coverage | *k* | |


## Chapter index

| Ch | Title | Use when |
|----|--------|----------|
| 1 | List accessing, deterministic | MTF, TRANS, FC, potential, det. LB |
| 2 | List accessing, randomized | BIT, RMTF, COMB, barely-random |
| 3 | Paging, deterministic | LRU/FIFO/FWF, LFD, marking, conservative |
| 4 | Paging, randomized | OBL/ADON/ADOFF, RANDOM, MARK, `H_k` |
| 5 | Beyond pure competitive paging | access graphs, Markov paging |
| 6 | Game-theoretic foundations | mixed / behavioral / extensive form |
| 7 | Request–answer games | adversary relations, formal ALG |
| 8 | Zero-sum games and Yao | minimax, Yao lower bounds |
| 9 | Metrical task systems | traversal, WFA, cruel adversary |
| 10 | *k*-server | DC, balancing, WFA, conjecture |
| 11 | Randomized *k*-server | Harmonic, cat-and-rat, resistive |
| 12 | Load balancing / bin packing | makespan, first-fit |
| 13 | Call admission / routing | disjoint paths, circuit routing |
| 14 | Search, trading, portfolios | one-way trading, universal portfolio → FTRL |
| 15 | Decision theory | ski/lease, axioms of the ratio |


## How to use this skill

- **Grab a ratio or adversary definition** → [cheatsheet.md](cheatsheet.md)
- **Look up a term** → [glossary.md](glossary.md)
- **Apply to Hermes** → [patterns.md](patterns.md)
- **Proof structure** → chapter “Frameworks” + “Key Results”
- **Do not** treat a stochastic-bandit Beta posterior as an oblivious-adversary guarantee; that is a different model (Ch. 4 vs Lattimore).


## Chapter files

- [ch01-list-accessing-deterministic.md](chapters/ch01-list-accessing-deterministic.md)
- [ch02-list-accessing-randomized.md](chapters/ch02-list-accessing-randomized.md)
- [ch03-paging-deterministic.md](chapters/ch03-paging-deterministic.md)
- [ch04-paging-randomized.md](chapters/ch04-paging-randomized.md)
- [ch05-alternative-paging-models.md](chapters/ch05-alternative-paging-models.md)
- [ch06-game-theoretic-foundations.md](chapters/ch06-game-theoretic-foundations.md)
- [ch07-request-answer-games.md](chapters/ch07-request-answer-games.md)
- [ch08-zero-sum-games-yao.md](chapters/ch08-zero-sum-games-yao.md)
- [ch09-metrical-task-systems.md](chapters/ch09-metrical-task-systems.md)
- [ch10-k-server.md](chapters/ch10-k-server.md)
- [ch11-randomized-k-server.md](chapters/ch11-randomized-k-server.md)
- [ch12-load-balancing.md](chapters/ch12-load-balancing.md)
- [ch13-call-admission-routing.md](chapters/ch13-call-admission-routing.md)
- [ch14-search-trading-portfolios.md](chapters/ch14-search-trading-portfolios.md)
- [ch15-decision-theories.md](chapters/ch15-decision-theories.md)
