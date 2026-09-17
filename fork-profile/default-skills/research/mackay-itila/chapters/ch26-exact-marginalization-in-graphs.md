# Chapter 26: Exact Marginalization in Graphs

## Core Idea
The sum–product algorithm computes exact marginals on trees (factor trees, Bayesian trees) by the same forward–backward logic, now with arbitrary degree. On graphs with cycles it becomes loopy belief propagation: often excellent (LDPC!), not guaranteed to converge or to be exact. Junction trees restore exactness at treewidth cost.

## Frameworks Introduced
- **Factor graph**: variables — factors. Message from factor f to variable x is the sum over other arguments of (f × incoming variable messages).
- **Sum–product (belief propagation)**
  - variable-to-factor: product of all other incoming factor messages
  - factor-to-variable: sum-out of factor × other variable messages
- **Max–product**: MAP configuration on trees.
- **Loopy BP**: iterate as if the graph were a tree; fixed points of the Bethe approximation (link to Ch 33).
- **Junction tree**: cluster cliques so the running-intersection graph is a tree; exact.

## Key Concepts
- **Tanner graph** of a code: bits ↔ parity checks. Sum–product there is LDPC decoding (Ch 47).
- **Scheduling**: flooding (all messages at once) vs residual / tree-based. On trees, leaves-in then out is enough (two passes).
- **Normalization**: beliefs ∝ product of incoming messages.
- **Damping**: on loopy graphs, mix new messages with old to reduce oscillation.
- **When exact**: singly connected graphs (no cycles). One cycle already makes BP approximate.

## Key Equations
- m_{f→x}(x) = sum_{~x} f(x, ~x) ∏_{x'∈n(f)\x} m_{x'→f}(x')
- m_{x→f}(x) = ∏_{f'∈n(x)\f} m_{f'→x}(x)
- b_x(x) ∝ ∏_{f∈n(x)} m_{f→x}(x)
- On a tree, b_x(x) = P(x | evidence) exactly (after two passes)
- Bethe free energy: stationary points ≈ loopy BP fixed points

## Algorithms and Techniques
**Sum–product on a tree**
1. Pick a root. Collect messages from leaves to root.
2. Distribute messages from root to leaves.
3. Beliefs at each variable are exact marginals.

**Loopy BP**
1. Initialize messages uniform (or random).
2. Iterate factor and variable updates for T iterations or until beliefs stabilize.
3. Read beliefs. If oscillating, damp (m ← λ m_new + (1−λ) m_old).
4. Do not trust a non-converged result as a probability.

**Junction tree (when treewidth allows)**
1. Moralize, triangulate, extract cliques.
2. Run sum–product on the clique tree (messages are over clique states).

## Mental Models
- Trees: BP is not an approximation — it *is* elimination with a good order.
- Loops: each extra path double-counts information; short cycles are the worst (hence LDPC girth matters).
- Use BP when the graph is sparse and locally tree-like (random regular graphs of large girth).

## Worked Example
Three bits x1,x2,x3 with one parity factor f=1[x1⊕x2⊕x3=0] and three independent priors P_i(xi).
- This factor graph is a tree (star).
- Message f→x1 is the convolution of P2 and P3 under XOR: P(x1=0) gets P2*P3 same-parity mass.
- Belief at x1 is the true P(x1 | parity).
- Add a second overlapping parity on the same bits → a cycle; loopy BP may still be decent but is no longer exact.

## Anti-patterns
- **Reporting loopy beliefs as calibrated posteriors** without checking on a small exact instance.
- **Tiny girth Tanner graphs** (many 4-cycles) then blaming “BP doesn’t work”.
- **Forgetting evidence factors** (channel likelihoods must be unary factors).
- **Junction tree on a 50×50 grid** (treewidth 50; clique states 2^{50}).

## Key Takeaways
1. Sum–product on trees is exact marginalization.
2. Loopy BP is the practical algorithm of modern coding and some vision/MRF tasks.
3. Cycles ≈ double-counting; design graphs with large girth when you plan to use BP.
4. Junction trees buy exactness with exponential clique cost.
5. Same messages, different semiring: sum–product vs max–product.

## Connects To
- **Ch 16, 24–25**: special cases (chain, trellis).
- **Ch 33**: variational / Bethe interpretation of loopy BP.
- **Ch 47–49**: LDPC, turbo, RA — loopy BP as decoder.
- **Ch 31**: Ising grids, where BP and mean-field compete with MCMC.
