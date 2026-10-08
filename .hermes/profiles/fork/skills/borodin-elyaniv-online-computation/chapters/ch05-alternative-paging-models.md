# Chapter 5: Alternative Paging Models — Beyond Pure Competitive Analysis

## Core Idea
Pure competitive paging is pessimistic: the cruel `k+1`-page loop makes every DET algorithm k-competitive and no better. Access-graph and distributional models restrict `σ` so algorithms can adapt to locality that real systems actually have.

## Key Concepts
- **Access graph G.** Pages = vertices; a request may only be a neighbor of the previous request (or in a neighborhood). Models program locality / call graphs.
- **FAR / graph-theoretic paging.** Online algorithms that evict the resident page farthest from the current vertex in G. Uniformly optimal in the access-graph model (proof in Appendix D).
- **Dynamic access graphs.** G can change; experimental studies compare LRU vs theoretically motivated rules when locality is real but not a fixed G.
- **Distributional / Markov paging.** Requests ~ Markov chain (or i.i.d.). Optimal policies via dynamic programming / known-chain OPT; competitive ratio is the wrong figure of merit — use expected cost.
- **Loose competitiveness / diffuse adversaries.** Later refinements (Young et al.) not fully developed here; the book’s point is: change the *input class*, not the ratio definition, to escape the k-barrier.

## Frameworks and Methods
- **Restrict the adversary’s request set** instead of weakening to average-case blindly.
- **Compare algorithms on the same G.** An algorithm that is k-competitive on all sequences can still dominate LRU on every access graph.
- **FAR construction.** Maintain a tree/forest of paths in G; evict the page whose connecting path is longest (farthest).
- **Markov paging.** If the chain is known, compute occupancy probabilities; if unknown, estimate. This is closer to Lattimore stochastic bandits than to Ch. 4.

## Key Results and Theorems

**Access-graph model.** There exist online algorithms whose competitive ratio on G depends on the *diameter / separators* of G, not just k, and can be o(k) on sparse locality graphs.

**FAR is uniformly optimal** among online paging algorithms in the (static) access-graph model (Theorem 5.11; Lemmas 5.4–5.5 proved in Appendix D).

**Distributional paging.** LRU is often near-optimal under typical locality distributions even though it is k-competitive in the worst case. That experimental fact does **not** improve the worst-case ratio.

## Key Equations
- Competitive ratio *on G*: `R_G(ALG) = sup_{σ valid on G} ALG(σ) / OPT(σ)`.
- Markov expected cost: `E_μ[ALG]` vs `E_μ[OPT]`, ratio of expectations ≠ competitive ratio.

## Worked Example
Linear access graph (pages on a line, requests only move to neighbors): an algorithm that keeps a contiguous window of k pages behaves like k-server on a line (Double Coverage, Ch. 10) and can beat cruel-loop LRU behavior.

## Hermes application
User queries have **access-graph locality** (a skill family is a connected subgraph). Skill-router paging should prefer FAR-like “evict the skill farthest in the skill-graph from the current query,” not cruel-adversary LRU. Fall back to MARK/LRU when the graph is unknown. Distributional (Beta) updates are valid only when rewards are approximately stochastic, not adversarial.

## Anti-patterns
- **Declaring LRU “optimal” from one locality trace.** That is distributional evidence, not a competitive theorem.
- **Using access-graph FAR on a complete graph.** Then G forbids nothing and you are back to ordinary paging.
- **Mixing E_μ[ALG]/E_μ[OPT] with ess-sup ALG/OPT.** Different objects.
