# Chapter 20: Burst-Error-Correcting Codes

## Core Idea
A burst of length b is a binary error pattern whose nonzero bits all lie inside some b consecutive positions. Cyclic Fire codes, interleaved random-error codes, and RS codes (Ch 7) are the three practical ways to correct single or phased bursts on magnetic tape, disk, and wireless fade events.

Note: this chapter is missing from the OCR merge; content follows ToC 20.1–20.5 and Lin & Costello 2nd ed.

## Key Concepts
- **Burst of length b**: first and last errors are 1, all errors inside a window of length b (zeros allowed inside).
- **Single-burst-correcting cyclic code**: corrects any burst of length ≤ b (and usually detects longer). Reiger bound: n−k ≥ 2b.
- **Fire code**: cyclic code with g(X) = (X^{2b−1} − 1) p(X), p irreducible of degree m, m ≥ b, p’s period ρ not dividing 2b−1. Length n = LCM(2b−1, ρ). Corrects bursts of length ≤ b.
- **Phased bursts**: errors confined to a known-alignment window (e.g. a symbol of an RS code, or a column of an interleaver). Easier than arbitrary-phase bursts.
- **Burst-and-random (hybrid) codes**: correct either a burst of length b or t random errors (not necessarily both at once). Product codes, RS+inner, Burton codes.
- **Interleaving** (Ch 4.8 recap): λ-depth block or convolutional interleaving turns a length-λb burst into b-length bursts in each of λ codewords, or into t-scattered errors.

## Frameworks and Methods
- **Pick a weapon**:
  - Known symbol alignment (bytes, GF(2^8)): **RS** (Ch 7). Best software story.
  - Arbitrary binary burst, cyclic hardware: **Fire** or **Burton**.
  - Mix of random + burst: **interleaved BCH/Hamming** or **product codes**.
  - Very long sparse bursts: interleave a random-error code deeply rather than build a huge Fire code.
- **Error-trapping decoder** (Ch 5) is *the* decoder for Fire/cyclic burst codes: cycle until the syndrome weight-and-span fits in the n−k window.
- **Phased-burst (Burton) codes**: g(X)=(X^ℓ−1)p(X) with extra constraints; correct bursts confined to a block of ℓ digits.

## Key Results
- Reiger bound: for a linear code correcting all bursts of length ≤ b, n−k ≥ 2b. Fire codes often meet or come close.
- Fire length n = LCM(2b−1, ρ) can be large; shortening is common.
- RS over GF(2^m): a burst of bm bits is at most b+1 symbol errors; t-symbol RS corrects bursts of length ≈ m t bits (phased to symbols, plus at most one extra).
- Interleaving a t-error-correcting code to depth λ corrects bursts of length λ t (and many random patterns).
- Product codes: a burst spanning less than d_col rows is a correctable column-error pattern if each hit row can be flagged as an erasure.

## Algorithms and Techniques
**Fire encoding**: LFSR with g(X)=(X^{2b−1}+1) p(X) (char 2). Systematic cyclic encode (Ch 5).

**Error-trapping decode of a Fire code**:
1. Compute s(X)=r(X) mod g(X).
2. For i=0…n−1:
   - If the syndrome’s 1s lie in 2b−1 consecutive positions and the p(X)-register indicates a consistent burst, trap: the 2b−1 window is the burst pattern.
   - Else shift (multiply syndrome by X mod g).
3. If nothing traps, detect-only (uncorrectable).

**Interleaver design**:
λ ≥ B_max / t. For a convolutional interleaver (Ramsey/Forney), delay is about λ(λ−1)N/2 — smaller latency than a λ×n block interleaver for the same spread.

**RS as burst code**:
Treat m-bit symbols. Decode t symbol errors. A binary burst of length m(t−1)+1 is always a ≤ t symbol error.

## Anti-patterns
- **Using a Hamming/BCH t=1 code on a fade without interleaving**: one burst = many bit errors ≫ t.
- **Fire code with m < b**: construction conditions fail; some bursts of length b share a syndrome.
- **Error-trapping without a timeout**: if you always “correct” the lowest-weight trap, you miscorrect random errors that look like bursts.
- **Shallow interleave + aggressive inner t**: still fails on industry-standard tape dropout lengths.
- **Ignoring Reiger**: promising “b=20 with 10 parity bits” is impossible for all-burst correction.

## Key Takeaways
1. Burst correction budget: at least 2b parity bits (Reiger).
2. Fire = cyclic, LFSR, error-trapping; RS = symbol-phased, algebraic; interleaving = reuse random-error codes.
3. Error-trapping is simple and complete for genuine single-burst channels.
4. Hybrid burst-and-random needs product / concatenated / interleaved designs, not a longer Fire polynomial.
5. Magnetic storage and old HF radio are the motivational channels; wireless now often uses interleaving + LDPC/turbo instead.

## Connects To
- **Ch 4**: interleaved and product codes.
- **Ch 5**: cyclic error-trapping.
- **Ch 7**: RS burst capability.
- **Ch 21**: convolutional burst codes and interleaved conv codes.
- **Ch 22**: detect (CRC) + ARQ as an alternative to correcting long bursts.
