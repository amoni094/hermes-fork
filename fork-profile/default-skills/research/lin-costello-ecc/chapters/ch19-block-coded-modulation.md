# Chapter 19: Block Coded Modulation

## Core Idea
Block-coded modulation (BCM) is multilevel coding on a partitioned constellation: each partition level is protected by a binary block code of a different strength (Imai–Hirakawa). Distance is a mix of Hamming distances and intraset Euclidean distances. Multistage decoding (Ch 15) is the natural decoder; hybrid partitions trade UEP profiles.

## Key Concepts
- **MSE distance / coded-modulation distance**: at level i, δ_i^2 = d_i · Δ_i^2 where d_i = d_min of the binary component code and Δ_i is the intraset Euclidean distance of partition i. The overall product-distance analogue is min_i δ_i^2.
- **Multilevel block modulation code**: L binary codes C_1,…,C_L, length n, encode L bit arrays that together label n constellation points (e.g. 8-PSK, 16-QAM, 64-QAM).
- **Ungerboeck partition vs block partition**:
  - Ungerboeck: increasing Δ_i, good for equal error protection.
  - Block partition: Δ_i stays small/equal at several levels, enabling independent decoding and UEP.
- **Multistage decoding of BCM**: decode C_1 (most protected / coarsest partition) first, then C_2 given Ĉ_1, etc. Soft or hard; error propagation is the issue.
- **Concatenated coded modulation**: outer RS or block code over BCM inner symbols.
- **Product coded modulation**: 2-D product of component codes on a constellation array.
- **Unequal error protection (UEP)**: assign strong codes (large d_i Δ_i^2) to MSB / header bits, weak codes to LSB. Example in the OCR: 6-level 64-QAM with mixed extended-BCH components, 12 dB gain on the most-protected levels vs uncoded 16-QAM at BER 10^{-5}.

## Frameworks and Methods
- **Imai–Hirakawa construction**:
  1. Partition the constellation L levels (L = log2 M).
  2. Choose binary (n, k_i, d_i) codes. Rate R = (Σ k_i)/n bits/symbol.
  3. Encode each bit plane with C_i; map the L-tuple at time t to a constellation point.
- **Distance design**: set min_i d_i Δ_i^2 as large as possible under a rate budget. Typically C_1 is a strong code (small k, large d) because Δ_1 is the smallest.
- **Multistage decode**:
  1. For each symbol, compute subset metrics at level 1; decode C_1 (trellis/Chase/algebraic).
  2. Given Ĉ_1, restrict each symbol to a subset; decode C_2; …
  3. Soft multistage uses LLRs of the chosen subset rather than hard Ĉ_i.
- **Hybrid partition** (OCR §19.6): block-partition the first one or two levels (independent decoding, smaller error coefficients) then Ungerboeck-partition the rest (grow Δ). Example 8-PSK hybrid: Δ0=Δ1=0.586, Δ2=2; third-level MSE distance jumps from 1.172 to 4, +4.4 dB at that level, −2.3 dB at level 2 — a UEP trade.

## Key Results
- If the partition distances are Δ_i and component distances d_i, a designed squared Euclidean distance of min_i d_i Δ_i^2 is guaranteed (analogous to the BCH designed distance).
- Spectral efficiency of the OCR 6-level 64-QAM UEP example: ≈ 4.013 bits/symbol with component extended BCH (64,24,16)×2, (64,45,8), (64,51,6), (64,57,4)×2; four UEP classes; 12 dB gain on levels 1–2 vs uncoded 16-QAM at 10^{-5}.
- Multistage loss vs ML is small when stage-1 SNR is high (strong C_1).
- BCM vs TCM: BCM uses off-the-shelf block codes and gives natural UEP; TCM usually better equal-error performance per state-complexity at short constraint length.

## Algorithms and Techniques
**Hard multistage 8-PSK BCM**:
Let C1, C2, C3 be binary codes of length n.
1. For t=1…n, compute metrics of the two QPSK-cosets of 8-PSK (level-1 bit). Decode C1.
2. Freeze that bit; for each t compute metrics of the two BPSK-cosets inside the chosen QPSK. Decode C2.
3. Freeze; slice the remaining BPSK bit with C3 as a binary code on AWGN.

**Soft/Chase multistage**:
Replace each algebraic step by Chase or block-trellis SISO (Ch 10, 14); pass extrinsic LLRs down (and optionally back up — iterative multistage).

**UEP assignment**:
Put headers / control in levels with large d_i Δ_i^2; put enhancement-layer media in weak levels. Hybrid partition if a weak Ungerboeck tail would otherwise under-protect the last level (as in Fig. 19.24 vs 19.29).

## Anti-patterns
- **Equal-strength component codes on Ungerboeck 8-PSK**: level 1 (tiny Δ) will dominate errors; C_1 must be much stronger than C_3.
- **Hard stage-1 at low SNR**: error propagation wipes later stages; the third-level code never gets a chance (OCR: third level worse than uncoded QPSK under pure block partition).
- **Ignoring error coefficients**: even with large min d_i Δ_i^2, huge multiplicity at a level (block partition) can ruin BER.
- **Using BCM where a single LDPC+Gray BICM would do**: post-2004 practice for equal protection on AWGN/fading is often BICM-ID or LDPC; BCM remains relevant for UEP and short-block coded modulation.

## Key Takeaways
1. BCM = multilevel block codes on a partitioned constellation (Imai–Hirakawa).
2. Design metric is min d_i Δ_i^2, not Hamming d_min alone.
3. Multistage decoding is the practical ML approximation; iterate/soften to cut error propagation.
4. Block vs Ungerboeck vs hybrid partitions are UEP knobs.
5. Extended BCH components of length 32–64 are the book’s workhorse BCM ingredients.

## Connects To
- **Ch 4, 6**: Hamming/BCH component codes.
- **Ch 15**: multistage and concatenated decoding.
- **Ch 18**: TCM is the convolutional sibling; same partitions, trellis instead of block codes.
- **Ch 10, 14**: soft component decoders inside multistage BCM.
