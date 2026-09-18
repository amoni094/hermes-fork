# Section 9: The Fundamental Theorem for a Noiseless Channel

## Core Idea
Entropy H is justified as the rate of generating information by proving it is exactly the channel capacity required under most efficient coding: one can transmit at average rate C/H source symbols per second, and no faster.

## Key Concepts
- **Source**: entropy H bits per symbol.
- **Channel**: capacity C bits per second (Sec 1 definition).
- **Ideal rate**: C/H source symbols per second.
- **Two constructive methods**: (1) typical-set block coding with a special start/stop sequence for the atypical set; (2) Shannon–Fano style coding by binary expansion of cumulative probabilities (independently found by R. M. Fano, RLE Technical Report 65, March 17, 1949).

## Key Results
**Theorem 9 (source coding / noiseless coding theorem).** Let a source have entropy H (bits per symbol) and a channel have capacity C (bits per second). Then it is possible to encode the output of the source in such a way as to transmit at the average rate (C/H − ε) symbols per second over the channel where ε is arbitrarily small. It is not possible to transmit at an average rate greater than C/H.

**Converse.** The transmitter must be non-singular, so input entropy per second equals source entropy H'. This cannot exceed channel capacity: H' ≤ C, so symbols/second = H'/H ≤ C/H.

**Direct part, method 1 (typical sets).** For large N, sequences split into a high-probability group of fewer than 2^{(H+η)N} members and a remainder of fewer than 2^{RN} members (R = log of alphabet size) with total probability < γ. Channel signals of duration T number more than 2^{(C−θ)T}. Choose T = (H/C + δ) N. Encode the typical set 1–1 into channel sequences; encode atypicals by longer sequences framed by an unused start/stop signal, taking time T1 = (R/C + δ') N. Mean rate → C/H as N → ∞.

**Direct part, method 2 (Shannon coding).** Order N-blocks by decreasing probability p1 ≥ p2 ≥ …; let P_s = ∑_{i=1}^{s−1} p_i. Encode message s by the binary expansion of P_s to m_s places, where

log2(1/p_s) ≤ m_s < 1 + log2(1/p_s)

High-probability messages get short codes. Codes are prefix-distinct because remaining Pi are at least 2^{−m_s} larger, so they differ in the first m_s bits. Average binary digits per original symbol H' satisfies GN ≤ H' < GN + 1/N → H. Excess time over ideal < GN/H + 1/(HN) − 1.

**Fano’s method.** Split the ordered list into two groups of as nearly equal probability as possible; first bit 0 or 1; recurse. “Apart from minor differences (generally in the last digit) this amounts to the same thing as the arithmetic process described above.”

## Key Equations
- max symbol rate = C/H
- log2(1/p_s) ≤ m_s < 1 + log2(1/p_s)
- GN ≤ H' < GN + 1/N
- inefficiency bound: GN/H + 1/(HN) − 1

## Significance
This is the noiseless source coding theorem: entropy is operationally the number of bits per symbol needed. Method 2 is Shannon–Fano coding (Huffman later improves the finite-N optimum). The typical-set argument is the template for Theorem 11.

## Connects To
- Sec 1: C as log-growth of allowed signals.
- Sec 7: typical set size 2^{HN}.
- Sec 8: non-singularity ⇒ entropy preservation (converse).
- Sec 10: matching analogy; worked codes.
- Sec 13: Theorem 11 is the noisy analogue.
