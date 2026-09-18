# Chapter 16: Message Passing

## Core Idea
Global functions on graphs (counts, shortest paths, marginal probabilities) can be computed by local messages between neighbours. The soldiers-in-the-mist parable is the whole book’s computational philosophy: cheap local hardware, iterated, replaces one omniscient commander. This is the algorithm pattern behind Viterbi, BCJR, sum–product, and LDPC decoding.

## Frameworks Introduced
- **Message passing on a line (soldiers)**
  - Rule set A: front soldier says “1” backward; each adds one and forwards. Rear learns N. Reverse pass tells everyone N and their index.
  - Complexity: O(N) additions, O(1) memory per soldier, no broadcast.
- **Path counting on a DAG / trellis**: forward messages = number of ways to reach a node; backward = ways to the end; product = through-count.
- **Lowest-cost path**: replace (sum, product) by (min, +) — the Viterbi / dynamic-programming semiring.
- **Semiring view** (implicit): the same schedule computes different queries by changing the algebra.

## Key Concepts
- **Local memory, local communication**: each node talks only to neighbours.
- **Forward–backward**: two sweeps on a chain compute every prefix and suffix quantity.
- **Trellis**: time-unrolled state graph of a chain-structured process (convolutional codes, HMMs).
- **When it is exact**: trees and chains. Loops require iteration and become approximate (Ch 26, 47).
- **Distributed counting vs shouting**: global broadcast is the expensive, brittle solution.

## Key Equations
- Forward: α_{t+1}(s') = sum_s α_t(s) ψ_t(s,s')
- Backward: β_t(s) = sum_{s'} ψ_t(s,s') β_{t+1}(s')
- Occupancy: γ_t(s) ∝ α_t(s) β_t(s)
- Shortest path: replace sum by min, product by +
- Soldier count: m_back(i) = 1 + m_back(i−1), m_fwd analogously

## Algorithms and Techniques
**Count the soldiers (chain)**
1. End node sends 1.
2. Each interior node sends 1 + received toward the other end.
3. Optional second pass: broadcast the total so each node learns its index and N.

**K lowest-cost paths / Viterbi**
1. Each node stores best cost to arrive (and a back-pointer).
2. Update: cost(s') = min_s [cost(s) + edge(s,s')].
3. At the end, traceback pointers.

**Path counting**
1. Same schedule with + on incoming path counts.
2. Number of paths through an edge = (paths-to-tail)×(paths-from-head).

## Mental Models
- If the graph is a tree, one can compute globally exact answers with two passes.
- If you change the semiring, you change the question (count, probability, max, min).
- LDPC decoding *is* this chapter on a loopy Tanner graph.
- Use message passing before reaching for global linear algebra on huge state spaces.

## Worked Example
Five soldiers in a line. Front sends 1; next sends 2; … rear receives 5. Rear now sends 1 forward; the original front learns there are 5 behind+self after the return? MacKay’s two-rule sets: one computes the total at one end; a second pass informs everyone of the total and of how many are in front/behind. Each soldier only ever adds 1.

Trellis with 2 states over T=3: forward path counts α give the number of sequences ending in each state; times backward β, you get how many full paths touch that state — the same pattern as HMM smoothing.

## Anti-patterns
- **Broadcast-and-centralize** when a chain/tree would do.
- **Running loopy message passing once and trusting it as exact**.
- **Mixing semirings** (adding costs to probabilities).
- **Storing global tables at every node** — that destroys the point.

## Key Takeaways
1. Local messages compute global functions on trees.
2. Forward–backward is the master algorithm for chains.
3. Changing (+,×) into (min,+) or (max,+) switches count → shortest/Viterbi.
4. This is the decoder architecture for Parts V–VI.
5. Hardware/people with tiny IQ and tiny radios can still compute N.

## Connects To
- **Ch 24–26**: exact marginalization, trellises, graphs (sum–product).
- **Ch 25**: Viterbi and BCJR named.
- **Ch 47–49**: iterative decoding of sparse-graph codes.
- **Ch 42–43**: Hopfield / Boltzmann as other local-update systems.
