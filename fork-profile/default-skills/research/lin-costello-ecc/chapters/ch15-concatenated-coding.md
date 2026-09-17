# Chapter 15: Concatenated Coding, Code Decomposition, and Multistage Decoding

## Core Idea
Concatenation (Forney) stacks an inner code (often convolutional/Viterbi or short algebraic) and an outer code (often RS) with an interleaver, multiplying distances and splitting complexity. Multilevel concatenation and code decomposition (Imai–Hirakawa, squaring) enable *multistage* decoding: decode a cheap inner/low level first, pass decisions (or soft information) to the next level.

## Key Concepts
- **Single-level (serial) concatenation**: outer (N,K,D) over GF(2^k) (typically RS) → inner (n,k,d) binary. Overall distance ≥ D d; overall rate (K/N)(k/n).
- **Interleaver between outer and inner**: a burst of inner decoder errors becomes scattered symbol errors the outer RS can correct.
- **NASA standard**: RS(255,223) outer + R=1/2, ν=6 (171,133) inner convolutional, Viterbi decoded; ~2–2.5 dB from the then-practical limit; later turbo/LDPC inner.
- **Multilevel concatenated codes**: several outer codes protect different partition levels of an inner code or signal set (bridge to BCM, Ch 19).
- **Soft-decision multistage decoding**: each stage is a SISO; pass LLRs, not hard symbols (much better than hard multistage).
- **Code decomposition**: write a code as a union of cosets of a subcode (e.g. RM(r,m) / RM(r−1,m)). Decode subcode, then the coset representative.
- **Iterative multistage MLD**: revisit earlier stages with later-stage decisions (reduces error propagation).
- **Convolutional inner concatenation**: the classical Forney scheme; inner Viterbi produces a bursty error process, hence symbol interleaving into RS.
- **Binary concatenation**: both levels binary (e.g. inner convolutional + outer BCH, or turbo product codes).

## Frameworks and Methods
- **Design procedure (serial)**:
  1. Pick inner code/decoder for the channel (AWGN → conv+Viterbi or LDPC; burst → RS or inner with interleaving).
  2. Measure inner decoder’s output error *burst statistics* (not just BER).
  3. Size outer RS t so that P(burst longer than t symbols) meets the WER target.
  4. Interleaver depth ≥ typical inner burst length in outer symbols.
- **Hard vs soft outer**:
  - Hard: inner outputs symbols; outer algebraic (cheap, standard CCSDS).
  - Soft / iterative: inner SOVA/BCJR LLRs, outer SISO (turbo concatenation, product codes) — more gain, more delay.
- **Multistage (two-level)**:
  1. Decode the more powerful (lower-rate) component on its partition.
  2. Subtract / re-encode and decode the weaker component on the refined metric.
  3. Optional: iterate.
  Error propagation from stage 1 to 2 is the main loss vs true MLD.

## Key Results
- Forney: concatenated codes achieve exponentially small Pe at rates below capacity with *polynomial* complexity in the overall length (the original constructive path to Shannon).
- Overall d_min ≥ d_inner × d_outer for serial concatenation with a trivial (row-column) interleaver; random interleavers give better typical distance spectra (turbo).
- RS+Viterbi concatenation: inner BER 10^{-3}–10^{-4} is enough for outer RS t=16 to drive WER to 10^{-10} (space links).
- Multistage loss vs MLD is small if the first-level distance is large enough that stage-1 errors are rare at operating SNR.
- Decomposition of RM via squaring is both a construction (Ch 4, 9) and a decoder architecture (this chapter).

## Algorithms and Techniques
**Classic NASA decode**:
1. Inner Viterbi on the convolutional stream (soft symbols in).
2. Deinterleave 8-bit symbols into RS(255,223) words (or 5× interleaved).
3. Algebraic RS decode (Ch 7), t=16.
4. Optional: if RS fails, some systems request retransmission (Ch 22) or use erasure flags from a Viterbi quality metric.

**Soft multistage (schematic)**:
Stage i uses a trellis/algebraic SISO on component C_i with channel LLRs plus extrinsic from other stages; subtract the decoded contribution from the received vector (in the partition metric) before stage i+1.

**Iterative multistage MLD**:
After a full pass of stages 1…L, re-run stage 1 with later decisions frozen or as a priori; stop when codeword metric stabilizes or a max-iteration count.

**Product-code view**:
Row-column product (Ch 4.7) is concatenation with a block interleaver; Pyndiah turbo-product decoding is iterative SISO on rows then columns — the iterative version of this chapter’s multistage idea.

## Anti-patterns
- **No interleaver between inner Viterbi and outer RS**: Viterbi errors come in bursts of length ~ traceback; one burst wipes t RS symbols in a row.
- **Sizing outer t from inner BER assuming i.i.d. errors**: use burst length histograms.
- **Hard multistage on AWGN at high rate**: error propagation dominates; use soft or iterate.
- **Matching two weak codes**: concatenation needs at least one component with serious distance;  d=3 inner + d=3 outer is still weak.
- **Ignoring latency**: N=255 RS + deep interleave + ν=6 Viterbi is fine for space, not for voice HARQ.

## Key Takeaways
1. Concatenation multiplies distance and splits decoder complexity — Forney’s route to reliability.
2. RS outer + convolutional/Viterbi inner is the classical space/CCSDS workhorse.
3. Interleaving is not optional; it is the interface that makes the distance product real.
4. Multistage decoding of decomposed/multilevel codes is MLD-like only if stage-1 is reliable or stages iterate.
5. Turbo (Ch 16) and LDPC (Ch 17) are “concatenated with a random interleaver + iterative SISO,” the 1990s upgrade of this chapter.

## Connects To
- **Ch 4**: product and interleaved codes as block concatenation.
- **Ch 7**: RS outer decoder.
- **Ch 12**: inner Viterbi / SOVA.
- **Ch 16–17**: iterative parallel/serial concatenation.
- **Ch 19**: multilevel BCM is concatenation in the signal space.
