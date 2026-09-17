# Chapter 18: Trellis-Coded Modulation

## Core Idea
Ungerboeck’s TCM puts redundancy in the *signal constellation* rather than extra symbols: a rate-k/(k+1) convolutional encoder selects a subset of an expanded 2^{k+1}-ary constellation (8-PSK instead of 4-PSK, etc.). Combined coding+modulation is decoded by Viterbi with Euclidean branch metrics. Gain comes from increasing free *Euclidean* distance at the same spectral efficiency.

## Key Concepts
- **Spectral efficiency**: bits per transmitted symbol (same baud rate as uncoded). TCM competes with uncoded 2^k-PSK/QAM, not with binary codes that expand bandwidth.
- **Set partitioning (Ungerboeck)**: recursively split the constellation into subsets with increasing *intraset* Euclidean distance: A0 → Δ0 < Δ1 < Δ2 < …
- **Natural / set-partition labeling**: encoder output bits select the partition path; least-protected bit chooses the coarsest split.
- **Ungerboeck encoder**: usually systematic recursive convolutional, rate k/(k+1), with the extra bit selecting the subset and the uncoded bits (if any) selecting the point inside the subset.
- **Free Euclidean distance d_free,E**: minimum Euclidean distance between distinct coded signal sequences. Asymptotic gain 10 log10(d_free,E^2 / d_uncoded^2) dB at same Es (and same bps/Hz).
- **Rotational invariance**: code + mapping unchanged under a constellation rotation (90°/180°). Needed so carrier-phase slips do not catastrophically fail Viterbi. Often uses differential encoding and a carefully chosen trellis.
- **Multidimensional TCM**: encode across L channel uses (e.g. 4D QAM). Finer partition distances and fractional rates (e.g. 2.5 bit/symbol). Wei codes; V.32/V.34 modem heritage.
- **Pragmatic TCM**: off-the-shelf binary convolutional encoder + Gray/SP mapping (Viterbi as usual). Slightly suboptimal vs Ungerboeck search, much simpler.

## Frameworks and Methods
- **Ungerboeck design rules** (heuristic):
  1. Expand the constellation (M → 2M) to free one extra bit.
  2. Partition to maximize intraset distances.
  3. All trellis branches leaving/entering a state get the highest-distance subsets.
  4. Parallel transitions (uncoded bits) get the largest Δ (they are not convolutionally protected).
- **Decoder**: Viterbi on the encoder trellis; branch metric = −||r_t − s(branch)||^2 (nearest point in the subset if parallel transitions: *subset decoding*).
- **Performance analysis**: union bound with Euclidean weights replacing Hamming d_free (Ch 12). Error events are trellis detours; multiplicity includes nearest-neighbor signal points.
- **When TCM vs binary coding + modulation**:
  - Band-limited AWGN (voiceband, satellite transponder, cable): TCM.
  - Power-limited / plenty of bandwidth: binary codes + BPSK/QPSK (Ch 11–17).
  - Fading: often bit-interleaved coded modulation (BICM) — after this book’s era — rather than classical Ungerboeck TCM.

## Key Results
- Canonical example: rate-2/3 coded 8-PSK vs uncoded QPSK, 4-state trellis, ~3 dB asymptotic / ~2.5 dB real gain at 10^{-5}, same 2 bit/symbol.
- 8-state 8-PSK TCM ≈ 3.6 dB asymptotic; 64-state ≈ 4.6 dB. Diminishing returns vs 2^ν.
- Shannon / coded-modulation limits: at 2 bit/symbol, capacity needs a few dB less than uncoded QPSK; TCM captures a large fraction with 8–64 states.
- Rotationally invariant 8-PSK (Wei, etc.) costs a fraction of a dB vs the best non-invariant code — usually worth it.
- Multidimensional TCM: V.32 32-QAM 4D codes; better shaping/partition than 2D at the same complexity.

## Algorithms and Techniques
**Set-partition 8-PSK**:
- Level 0: all 8 points, Δ0^2 = (2−√2) R^2 ≈ 0.586 (for unit radius).
- Level 1: two QPSK subsets, Δ1^2 = 2.
- Level 2: four BPSK subsets, Δ2^2 = 4.

**4-state Ungerboeck 8-PSK (sketch)**:
One systematic bit uncoded (parallel transitions: BPSK subsets, Δ^2=4). One bit through a 4-state rate-1/2 encoder selects the subset. Viterbi: 4 states, 2 parallel branches each, Euclidean metrics.

**Subset decoding for parallel transitions**:
For each subset on a branch, pick the constellation point closest to r_t; use that distance as the branch metric; the uncoded bits are those of the winning point.

**Rotational invariance recipe**:
1. Choose a mapping that commutes with rotation by 2π/M.
2. Make the trellis invariant: a rotation corresponds to a state automorphism.
3. Differential-encode the bits that select the rotation class.

## Anti-patterns
- **Hamming-distance Viterbi on TCM**: metrics must be Euclidean; Gray-mapped Hamming is BICM, not Ungerboeck TCM.
- **Expanding bandwidth instead of the constellation**: then you wanted Ch 11, not TCM.
- **Ignoring phase invariance on a loop with phase slips**: decoder lock loss; use Wei-style RI codes.
- **Putting parallel transitions on small-Δ subsets**: the free distance is then just that Δ, wasting the trellis.
- **Huge ν TCM**: 256-state 8-PSK gains little over 64-state; spend complexity on multidimensional mapping or a turbo-TCM (beyond core chapter).

## Key Takeaways
1. TCM = convolutional coding *inside* an expanded constellation; baud rate unchanged.
2. Set partitioning aligns trellis splits with Euclidean distance.
3. Decode with Euclidean Viterbi (subset decoding on parallel branches).
4. 3–6 dB over uncoded at the same bps/Hz is the realistic range.
5. Rotational invariance and multidimensional constellations are what made TCM the 1980s–90s modem standard.

## Connects To
- **Ch 1**: coded modulation and Shannon-limit figures.
- **Ch 11–12**: convolutional generators and Viterbi, now with Euclidean metrics.
- **Ch 16**: turbo-TCM is iterative TCM (not fully developed here).
- **Ch 19**: block-coded modulation — same partition idea without a trellis.
