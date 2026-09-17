# Chapter 6: Techniques for Coding and Decoding

## Core Idea
Unstructured ML decoding is impossible at the block lengths where E_r(R) is useful. Linear (parity-check) structure makes encoding algebraic; convolutional structure plus threshold or sequential decoding makes decoding sequential in time. The same E_r(R) is achievable with parity-check codes on the BSC.

## Key Concepts
- Parity-check / linear code: x = u G over GF(2) (or a field). Systematic: x = (u, uP). (N, L) code has 2^L words, rate R = (L ln 2)/N nats.
- Generator matrix G (L × N); parity-check matrix H (N × (N−L) in Gallager’s orientation) with xH = 0 for code words.
- Syndrome S = yH = zH. Decoding = infer error z from S.
- Coset code: x = uG ⊕ v. Ensemble with random G, v has pairwise independent words; enough for Theorem 5.6.1.
- Hamming code: single-error-correcting, N = 2^m − 1, N − L = m.
- Cyclic codes: cyclic shift of a code word is a code word; generator polynomial g(D).
- BCH codes: cyclic codes designed via roots in an extension field to guarantee a designed minimum distance.
- Convolutional code: each block of λ source digits produces ν channel digits via a shift-register linear combination. Constraint length N = ν L (L = memory in stages). Systematic if the first λ outputs are the source digits.
- Orthogonal parity checks (Massey): linear combinations of the syndrome that involve a target noise bit in every check and every other bit in at most one check.
- Threshold decoding: majority vote on 2e orthogonal checks corrects e errors on that bit (Theorem 6.8.1).
- Sequential decoding: search a code tree with tentative hypotheses; backtrack when a path metric falls. Fano (1963) algorithm is Gallager’s focus; Wozencraft (1957) originated the idea.
- Fano metric: Γ(x_ℓ; y_ℓ) = ∑ ln[P(y_n|x_n)/ω(y_n)] − ℓν B, with bias B. On a BSC, equivalent to Hamming distance plus a drift term.
- Burst: a run of noise of length b relative to a guard space g (ones at both ends, no g consecutive zeros inside, g zeros on each side).
- Interlacing (interleaving): demux into r streams so a channel burst becomes isolated errors in each codeword.

## Frameworks and Methods
- Linear algebra over GF(2): encoding is matrix multiply; minimum distance is the minimum Hamming weight of nonzero code words (distance spectrum).
- Algebraic decoding: syndrome → error locator (Hamming, BCH iterative algorithm for σ(D)).
- Random linear codes: Theorem 6.2.1 — random coset codes meet E_r(R) on the BSC. Structure does not cost exponent if the ensemble is pairwise independent.
- Tree codes: convolutional outputs form a 2^λ-ary tree of ν-letter branches. Sequential decoding walks this tree.
- Burst design: do not model P_e (atypical bursts dominate); use burst-correcting capability b relative to guard space g, with a rate/guard upper bound.

## Key Results and Theorems
- Encoder complexity: parity-check encoding storage is O(NL), not O(N 2^L).
- Theorem 6.2.1: random (N,L) coset codes on the BSC satisfy P_{e,m} ≤ exp(−N E_r(R)). Systematic parity-check codes exist with the same bound (corollary).
- Hamming: corrects 1 error; syndrome is the binary location of the error.
- Theorem 6.8.1: 2e checks orthogonal on z_i ⇒ majority (threshold) recovers z_i if at most e of the involved noise digits are nonzero.
- Convolutional constraint length plays the role of block length for error probability, but decoding errors can propagate; feedback of corrections into the syndrome limits propagation on simple threshold decoders.
- Threshold decoding is excellent at short constraint length; Gallager states it is reasonably certain that P_e cannot be driven arbitrarily small by increasing constraint length with threshold decoding alone.
- Sequential decoding (Fano): three moves — forward, lateral, backward — on the received-value tree. Computation is typically bounded for R < R_0 and becomes unbounded above R_0.
- Burst bound: for any code of rate R (bits) and finite decoding delay, burst-correcting capability b relative to guard g cannot exceed a function of R and g (counting argument on two burst patterns, §6.10).
- Interleaving + memoryless decoder: if memory dies with time, capacity is at least that of the associated DMC.

## Algorithms and Techniques
Systematic parity-check encode:
1. Store information u of length L.
2. Compute N − L checks, each a prescribed mod-2 sum of information bits.
3. Transmit x = (u, checks).

Syndrome decode (table or algebraic):
1. S = yH.
2. If S = 0, accept y.
3. Else map S to a minimum-weight error z (table, Hamming position, BCH locator) and output y ⊕ z.

Threshold decode (convolutional, Massey):
1. Compute syndrome stream S_n from received parity vs recomputed parity.
2. Form 2e orthogonal combinations on the current information-error bit.
3. If a majority equal α, decide that error is α; else 0.
4. Feedback: remove the decided error from future syndrome bits; shift and repeat.

Fano sequential decode (outline):
1. Keep a replica encoder and a threshold T on the Fano metric Γ.
2. Try a forward move that stays above T; if several, pick the best.
3. If no forward move works, move laterally among siblings, then backward, lowering T by a step Δ when needed.
4. Raise T when the path looks good again. Output bits that have been confirmed by sufficient depth.

Burst / ARQ:
1. Cyclic code; accept iff S = 0; else request retransmission.
2. Or interleave r-way; decode each stream with a memoryless decoder.
3. Cyclic interlacing: replace g(D) by g(D^r).

## Anti-patterns
- Storing an arbitrary codebook at large N. Use linearity.
- Threshold decoding at long constraint length expecting Shannon reliability. Use sequential (or later, Viterbi — after 1967, not this book’s emphasis).
- Sequential decoding above R_0: mean computation diverges; buffers overflow.
- Ignoring error propagation in convolutional decoders. Insert sync zeros or use feedback/ARQ after detecting a burst of decoding errors.
- Designing for typical noise on burst channels. Atypical long bursts cause the outages; use b-versus-g, interleaving, or detect-and-repeat.
- Assuming algebraic minimum distance equals the random-coding exponent. BCH designed distance is a worst-case guarantee; E_r is an ensemble exponential rate.

## Key Takeaways
1. Linearity preserves the random-coding exponent on the BSC and makes encoding cheap.
2. Convolutional codes trade block diagrams for trees; threshold decoding is local majority, sequential decoding is metric-guided search.
3. R_0, not C, is the operational limit of sequential decoding computation.
4. Burst-noise coding is a combinatorial guard-space problem plus interleaving, not a DMC exponent problem.

## Connects To
- Ch 5: E_r(R) is the target; Ch 6.2 proves linear codes meet it on the BSC.
- Ch 4: H and G implement subspaces of the DMC input space.
- Ch 7–8: same sequential/ML metrics with Gaussian likelihoods.
- Historical: Gallager’s 1963 monograph Low-Density Parity-Check Codes is the origin of LDPC; this 1968 chapter develops classical linear, cyclic, BCH, convolutional, threshold, and sequential methods rather than sparse iterative decoding.

Note on OCR: Ch 6 is complete in the source. Sequential decoding, threshold decoding, convolutional codes, and burst-noise coding all live here — not as separate later chapters.
