# Ch 13 — Online Algorithms

Request sequence revealed one-by-one. **Competitive ratio** `C_A`: there is `b` such that for every sequence `σ`,

`cost_A(σ) ≤ C_A · cost_OPT(σ) + b`.

## Paging (Ch 13.1)

Cache of size `k`. Miss costs 1.

**Theorem 13.1.** Every deterministic online paging algorithm has `C_A ≥ k`. LRU and FIFO meet `k`.

## Adversary models (Ch 13.2)

- **Oblivious:** sequence fixed before seeing the algorithm’s coins.
- **Adaptive online:** adversary sees coins, serves with its own online cache.
- **Adaptive offline:** adversary sees coins and pays OPT on the resulting sequence.

## Paging vs oblivious adversary (Ch 13.3)

**Theorem 13.2.** Every randomised paging algorithm has `C_R ≥ H_k` against oblivious adversaries.

**Marker algorithm.** Phases; mark requested items; on miss, evict a uniform unmarked line. At phase end, unmark all.

**Theorem 13.3.** Marker is `2 H_k`-competitive against oblivious adversaries.

## Relating adversaries (Ch 13.4)

**Theorem 13.4.** A randomised algorithm that is `c`-competitive against *every* adaptive offline adversary implies a `c`-competitive *deterministic* algorithm. Hence randomised paging cannot beat `k` against adaptive offline.

**Theorem 13.5.** `c`-competitive vs adaptive online, and `ρ`-competitive vs oblivious ⇒ `cρ`-competitive vs adaptive offline.

## Weighted paging / Reciprocal (Ch 13.5)

**Theorem 13.6.** Reciprocal is `k`-competitive against adaptive online adversaries. RANDOM (evict uniform) inherits `k` vs adaptive online and `k H_k` vs adaptive offline — tightness of Thm 13.5.

## k-server (Ch 13.6)

`k` servers on a metric space; request a point, move a server there. Paging = k-server on a uniform metric.

**Theorem 13.7.** Every randomised k-server algorithm has competitive ratio `≥ k` in some metrics (adaptive). Reciprocal is optimal for weighted paging.

The deterministic k-server conjecture (`k`-competitive for every metric) was open in 1995 (now known to be `O(log² k)` randomised, still open deterministically in general).

## Ski rental (classic; book analogue is paging)

Rent costs 1 per day; buy costs `B`. Deterministic: rent until day `B`, then buy → **2-competitive**, and 2 is tight. Randomised: geometric / decaying distribution over buy-day yields `e/(e−1) ≈ 1.582`.

Use ski rental as the template for **rent-vs-buy** resource decisions (keep a process alive vs restart; cache a model vs reload). Motwani’s theorems are paging/k-server; quote ski rental as the 2-competitive sibling, not as a numbered Motwani theorem.

## Hermes

- Cache of `k` skill embeddings / tools: Marker vs LRU depending on adversary. If the request sequence is independent of your coins, `H_k` is the right target, not `k`.
- Cron keep-alive vs cold start: ski rental, ratio 2 (deterministic) or `e/(e−1)` (randomised).
