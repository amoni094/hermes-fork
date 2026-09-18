# Chapter 10: Reliability-Based Soft-Decision Decoding Algorithms for Linear Block Codes

## Core Idea
Soft-decision MLD for block codes is nearest-neighbor search in Euclidean space. When the trellis is too big, *reliability-based* algorithms sort symbols by |r_i|, decode the most reliable basis algebraically, then reprocess the least reliable positions (Chase, GMD, ordered-statistics / Fossorier–Lin) until a sufficient optimality test fires.

## Key Concepts
- **BPSK mapping**: 0 → −1, 1 → +1 (book uses c_i = 2v_i − 1). Squared Euclidean distance d_E^2(v_i, v_j) = 4 d_H(v_i, v_j); so d_E,min^2 = 4 d_min.
- **Equivalent MLD metrics** (AWGN): maximize log-likelihood ⇔ minimize Euclidean distance ⇔ maximize correlation m(r,c)=Σ r_i c_i ⇔ minimize correlation discrepancy λ(r,c) = Σ_{sign mismatch} |r_i|.
- **Reliability of position i**: |r_i| (or |LLR|). Large |r_i| ⇒ hard bit is trustworthy.
- **MRP / LRP**: most / least reliable positions after sorting |r_i|.
- **Chase algorithms**: make a list of test error patterns on the p least reliable positions; algebraically decode each; pick the candidate with best soft metric.
- **GMD (Forney generalized minimum distance)**: successively erase the j = 0,2,…,d_min−1 most unreliable symbols and errors-and-erasures decode; accept if a GMD sufficient condition holds.
- **Ordered-statistics decoding (OSD) / most reliable basis reprocessing**: Gaussian-eliminate G on the k most reliable *independent* positions; encode that information set; reprocess by adding low-weight error patterns on that basis (order-w OSD).
- **Sufficient optimality tests**: if the discrepancy of a candidate is less than a function of d_min and the sorted |r_i|, no better codeword exists — stop early (often after one Chase/OSD trial).
- **Weighted MLG**: replace hard majority (Ch 8) by reliability-weighted votes; iterate on one-step MLG codes.

## Frameworks and Methods
- **When to use which**:
  - Chase-II with p=⌊d_min/2⌋: near-MLD for small d_min (Hamming, Golay, BCH t≤4).
  - GMD: e+ν decoder already available (RS/BCH); complexity ~ d_min algebraic decodes, slightly more loss than Chase.
  - OSD order-w: high-rate long BCH/RM where 2^w C(k,w) encodings beat 2^{n−k} syndromes.
  - Trellis Viterbi (Ch 9,14): when s_max is small.
- **Union bound on block error, soft MLD**:
  P_e ≤ Σ_i A_i Q(√(2 i R Eb/N0)), A_i = number of weight-i codewords.
- **Asymptotic gain** (Ch 1): 10 log10(R d_min) dB.

## Key Results
- Soft MLD is optimal on AWGN among decoders that output a codeword; reliability algorithms approximate it with a list whose size is exponential in a *small* parameter (p or w), not in k.
- Chase-II with all 2^{⌊d_min/2⌋} patterns on the LRP is practically ML for many small codes (Fossorier–Lin tests).
- OSD-w corrects (w+1)d_min/2 − 1 errors in the MRP information set in the worst case; order-1 or 2 is already close to MLD at moderate SNR for high-rate BCH.
- Early-stop sufficient conditions (e.g. Taipale–Pursley, Fossorier–Lin) make average complexity drop with SNR: at high SNR, usually the hard-decision algebraic decode already passes the test.
- Weighted MLG iteration on EG/PG codes approaches APP bit-flip, still far from MLD if J is small.

## Algorithms and Techniques
**Soft MLD (brute force, reference)**:
For every codeword v, compute λ(r,c) or Σ r_i c_i; take the minimizer/maximizer.

**Chase-II**:
1. Hard-decide r → z. Sort positions by increasing |r_i|.
2. Generate test patterns t covering all errors of weight ≤ q in the p LRPs (classic: p=⌊d_min/2⌋, all 2^p patterns).
3. For each t, algebraically decode z+t to a codeword ĉ (or fail).
4. Among successful ĉ, pick the one maximizing correlation with r.

**OSD-0 / OSD-w (MRIP reprocessing)**:
1. Sort coordinates by |r_i| descending.
2. Find the first k linearly independent columns of G (most reliable basis); permute to [I_k | P'].
3. OSD-0: re-encode the hard decisions on that basis → candidate c^{(0)}.
4. OSD-w: flip all combinations of 1…w bits in the basis, re-encode, keep the best metric.
5. Apply optimality test; stop if met.

**GMD**:
For j = 0, 2, …, 2t: erase the j least reliable symbols, run errors-and-erasures decode, collect candidates, pick best correlation. Forney’s theorem: if a candidate satisfies a weighted-distance test, it is ML.

## Anti-patterns
- **Sorting but not forcing an information set**: the k most reliable positions may be linearly dependent; you must skip dependent columns or OSD encodes the wrong set.
- **Chase list too small at low SNR**: p=2 is not enough for t=4 BCH at the coding threshold.
- **Skipping the optimality test**: you pay worst-case list size at high SNR where OSD-0 already wins.
- **Using Hamming metric to choose among Chase candidates**: the whole point is the *soft* correlation.
- **OSD on low-rate codes**: 2^w C(k,w) with large k is worse than a 2^{n−k} trellis; dualize.

## Key Takeaways
1. Soft MLD = Euclidean / correlation; reliability = |r_i|.
2. Chase / GMD / OSD turn one algebraic decoder into an approximate soft ML decoder via a short list.
3. Sufficient tests cut average complexity sharply as SNR grows.
4. ~2–3 dB over hard decoding is the budget these algorithms are chasing.
5. Contributor: Marc Fossorier; this chapter is the practical bridge from algebraic codes to turbo-era soft decoding.

## Connects To
- **Ch 1**: 3 dB asymptotic soft-vs-hard gap; Golay example.
- **Ch 6–7**: algebraic inner decoder that Chase/GMD wrap.
- **Ch 8**: weighted MLG iteration.
- **Ch 9, 14**: exact MLD via trellis when state complexity allows.
- **Ch 16–17**: iterative SISO is the other, more scalable, soft approach.
