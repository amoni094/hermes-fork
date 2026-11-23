# Ch 13 — Call Admission and Routing

## Call admission (circuit switching)

**Problem.** Requests for unit-capacity paths arrive online in a graph G. Accept or reject; maximize accepted calls (each yields profit 1). Rejected calls lost forever.

**Key result (Awerbuch et al.).**
- On a general graph: no online algorithm is competitive (ratio Ω(√m) where m = edges).
- On trees: O(1) competitive with randomization.
- On rings: Θ(log n) competitive.

**Greedy admission.** Accept if a path exists; reject otherwise. Not competitive in general (adversary fills bottleneck links).

## Disjoint paths

**Edge-disjoint paths.** Each accepted call uses ≤ 1 unit on each edge. OPT = maximum matching in a flow network.
**Deterministic lower bound.** Ω(√m) on general graphs.
**Randomized vs OBL.** O(log^2 n) on bounded-degree expanders.

## Online routing

**Non-clairvoyant shortest path.** Requests = (src, dst) pairs; edges have unknown congestion. Route to minimize total delay.
- Experts: treat each path as an expert; exponential weights (Arora et al.); regret O(√T log P) where P = number of paths.
- Connection to FTRL: routing-weight-updater uses EMA on path-level success rates; regret ≤ O(√T) by standard online-to-batch conversion.

## Hermes application
API provider routing (LLM backend selection) as online routing:
- Edges = providers (Anthropic, OpenAI, Mistral, Grok).
- Edge cost = failure rate + latency.
- FTRL weight updater plays the role of exponential-weights router.
- Competitive guarantee: E[cost_FTRL] ≤ OPT_offline + O(√T · log K) where K = number of providers.
- Practical: weight decay (EMA_DECAY=0.9) implements forgetting for non-stationary costs.
