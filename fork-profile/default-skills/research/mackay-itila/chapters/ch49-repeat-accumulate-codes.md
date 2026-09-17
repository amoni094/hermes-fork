# Chapter 49: Repeat–Accumulate Codes

## Core Idea
Repeat–accumulate (RA) codes are almost as simple as repetition, and they work. Encoder: repeat each of K source bits (typically 3 times), permute, then accumulate (running mod-2 sum). Decode by sum–product on a tiny factor graph (equality nodes + a trellis for the accumulator). Empirical performance rivals other sparse-graph codes; decoding time has a power-law tail.

## Key Concepts
- **Encoder steps**: s ∈ {0,1}^K → repeat q times (N=qK) → fixed random π → u=π(repeat(s)) → t_n = t_{n−1} + u_n (mod 2). Rate 1/q (1/3 in the figures).
- **Accumulator**: a rate-1 recursive convolutional encoder with tap 1/(1+D).
- **Factor graph**: equality constraints on the q copies of each s_k; intermediate bits; parity checks of the accumulator; transmitted t (channel likelihoods).
- **Decoding split**: (1) forward–backward on the accumulator trellis using incoming u-likelihoods and channel on t; (2) equality-node products sending new messages to the trellis.
- **Detected vs undetected errors**: stop-when-done (as LDPC/turbo). Error floor ~10^{-4} block error in MacKay’s plots if you care; waterfall is excellent.
- **Generalized parity-check matrices**: RA as a sparse H with a dual-diagonal accumulator block.

## Frameworks and Methods
- **Turbo-like simplicity for theory**: Divsalar et al. wanted something analyzable; practice turned out competitive with turbo/LDPC (cf. MacKay figure 47.17).
- **Same iterative decoder family**: sum–product, no algebra.
- **Power-law decoding times**: P(τ) ∝ τ^{−p} for large iterations τ; p shrinks (heavier tail) as SNR drops. Seen in RA *and* Gallager codes. Practical implication: mean iterations hide rare very long runs; use a cap.
- **Irregular RA / IRA**: later generalizations (not all in this short chapter) vary repeat degrees.

## Key Equations
- Repeat: ũ = (s_1,s_1,s_1, …, s_K,s_K,s_K)  (q=3)
- u = π(ũ)
- t_n = t_{n−1} ⊕ u_n    (t_0=0)
- Rate R = K/N = 1/q
- Equality factor: [x_1=x_2=x_3]
- Parity factor: [t_n ⊕ t_{n−1} ⊕ u_n = 0]
- Decoding-time tail: P(τ) ∝ τ^{−p(SNR)}

## Algorithms and Techniques
**Encode**
1. Repeat each bit q times.
2. Apply the frozen random permutation.
3. Accumulate XOR; send t (and optionally puncture for higher rate).

**Decode (one iteration)**
1. Accumulator trellis: take messages from equality nodes as transition likelihoods; run forward–backward with channel on t; emit bit messages for the u-nodes.
2. Equality nodes: multiply the q incoming messages (and any prior); send extrinsic back.
3. Hard-decide s from equality nodes; optionally check consistency with t. Repeat until done or cap.

## Anti-patterns
- **Random permutation per codeword** — π is part of the code, fixed.
- **Ignoring the error floor** if your application needs 10^{-10} (need longer N, irregular degrees, or a different graph).
- **Uncapped iteration** near the threshold — power-law waits.
- **Comparing to repetition without noticing N=3K is still cheap relative to Shannon**.

## Key Takeaways
1. Repeat, permute, accumulate: a capacity-approaching practical code.
2. Decoder = BCJR on a chain + equality nodes.
3. Detected failures vs low-weight undetected errors — plot both.
4. Iteration counts are heavy-tailed; budget a max τ.
5. Sparse-graph codes need not be messy to be good.

## Connects To
- **Ch 1**: repetition code as the naive ancestor.
- **Ch 25, 48**: accumulator trellis and turbo.
- **Ch 47**: Gallager performance comparison; same power-law times.
- **Ch 26**: factor graphs, equality and parity nodes.
