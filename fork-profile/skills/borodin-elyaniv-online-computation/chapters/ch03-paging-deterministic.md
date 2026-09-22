# Chapter 3: Paging — Deterministic Algorithms

## Core Idea
A fast cache of `k` pages; requests are page IDs. On a miss, evict one cache page and fetch (cost 1). Offline OPT is **LFD** (Belady). Every reasonable deterministic online paging algorithm is **k-competitive**, and that is tight.

## Key Concepts
- **Hit / miss.** Cost models: *miss-only* (standard competitive paging) vs *full-access* (Ch. 3.7), which charges hits too.
- **LFD (Longest Forward Distance):** evict the cached page whose next request is farthest in the future (or never). Optimal offline.
- **LRU:** evict least recently used.
- **FIFO:** evict the oldest resident.
- **FWF (Flush-When-Full):** on a miss with a full cache, evict *all* `k` pages then load the request.
- **CLOCK:** circular scan with a reference bit; a marking approximation of LRU.
- **LIFO / LFU:** last-in-first-out / least-frequently-used. **Not competitive** (unbounded ratio).
- **(h,k)-paging:** ALG has cache `k`, OPT has cache `h ≤ k`. Ratio `k/(k−h+1)`.
- **Marking algorithm:** phases; on first request of a page in a phase it is *marked*; on a miss evict an unmarked page (arbitrary). When all are marked, unmark and start a new phase.
- **Conservative algorithm:** never more than `k` misses on any consecutive subsequence that contains ≤ `k` distinct pages.

## Frameworks and Methods
- **Phase partition (marking).** A phase ends when the (`k+1`)st distinct page of the phase arrives. OPT has ≥ 1 miss per phase; a marking ALG has ≤ `k` misses per phase → `k`-competitive.
- **Conservative ⇒ k-competitive.** LRU, FIFO, CLOCK, FWF are conservative (FWF is marking). Same bound.
- **Lower bound k.** Cruel adversary: always request a page not in ALG’s cache. OPT with `k` slots can be charged 1 miss every `k` of ALG’s misses (or use `k+1` pages total: ALG misses every time, OPT once per `k`).
- **List-accessing as paging.** MTF-style heuristics specialize; paging is MTS on a uniform metric (Ch. 9) with `k` “servers” in the cache.

## Key Results and Theorems

**Theorem (LFD).** LFD is an optimal offline paging algorithm.

**Theorem (marking / conservative).** Every marking or conservative algorithm is **k-competitive**. In particular LRU, FIFO, CLOCK, FWF are k-competitive.

**Theorem (tightness).** No deterministic online paging algorithm is better than k-competitive.

**Theorem ((h,k)-paging).** LRU (and marking) is `k/(k−h+1)`-competitive vs an h-cache OPT. Tight.

**LIFO and LFU are not competitive.** Adversary loops on a working set that LFU’s counters / LIFO’s stack treat badly.

## Key Equations
- `ALG(σ) ≤ k · OPT(σ) + k` (typical additive from the last incomplete phase).
- `(h,k)` ratio: `k / (k − h + 1)`.
- Phase miss bound: marking ALG ≤ `k` misses/phase; OPT ≥ 1.

## Worked Example
`k = 2`, pages `{a,b,c}`, `σ = a,b,c,a,b,c,…`. LRU always misses after the first two; OPT (LFD) misses every other request in a 2-cache? With 2 slots OPT still misses on every third distinct in a 3-cycle: ALG/OPT → 2 = k. Cruel adversary for general k uses `k+1` pages.

## Hermes application
Context windows, tool-result caches, and retrieved-memory slots are paging. **LRU or MARK**, never LFU/LIFO, for a worst-case k-ratio. If the “offline” baseline is allowed only `h < k` slots (smaller memory store), quote `(h,k)` not `k`.

## Anti-patterns
- **Claiming LRU is 1-competitive** because “it is optimal in practice.” Practice ≠ competitive ratio.
- **Using LFU for adversarial / nonstationary access** (user jumps working set): unbounded ratio.
- **Forgetting the additive phase term** when n is small.
- **Comparing k-cache LRU to k-cache OPT and expecting o(k).** Impossible deterministically.
