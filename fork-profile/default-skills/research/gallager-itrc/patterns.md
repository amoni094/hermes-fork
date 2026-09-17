# Proof techniques — Gallager ITRC (1968)

## Random coding argument

**When.** Existence of codes with P_e ≤ exp(−N E_r(R)). Also source-coding covering for R(d*).

**How.**
1. Draw M codewords independently from Q_N (usually i.i.d. letters ~ Q), or from a pairwise-independent ensemble (random G, v for coset codes).
2. Bound the ensemble-average error P̄_{e,m} with a Chernoff / ρ-union estimate (Theorem 5.6.1).
3. Conclude some code (in fact most, via Chebyshev) meets the average.

**Key insight.** You never construct the code. Averaging linearizes the union bound: E[∑_m' P(y|x_{m'})^s] factors into a product of single-letter sums, which becomes e^{−N E_0}. Pairwise independence of words is enough; full independence is not required (Theorem 6.2.1).

**Trade-offs.** Gives existence, not an encoder/decoder of polynomial size. The average is dominated by rare bad codes at low rate — fix with expurgation. The bound with ρ ∈ [0,1] is tight near C (sphere-packing) and loose at low R.

---

## Expurgation

**When.** Low rates, where E_r(R) is limited by the chance two words collide or are unusually close. Binary-symmetric illustration: as R → 0 the random-coding bound tracks M (1/4)^N, i.e. the probability another word is identical.

**How.**
1. Draw M' = 2M − 1 words.
2. For each m, P_{e,m} is a r.v. over the ensemble. Chebyshev: Pr(P_{e,m} > 2 E[P_{e,m}^s]^{1/s}) ≤ 1/2.
3. Some code has at least M words satisfying the moment bound. Delete the rest. Remaining decoding regions only grow.
4. Optimize s ∈ (0,1], set ρ = 1/s ≥ 1, obtain E_ex.

**Key insight.** The ensemble mean is not the typical code’s P_e when the tail is heavy. Removing a constant fraction of words costs (ln 4)/N in rate and buys a better exponent below the ρ = 1 point.

**Trade-offs.** Still non-constructive. E_ex uses a pairwise (Bhattacharyya-like) metric, so it does not improve the bound where E_r already uses ρ < 1. On very noisy channels E_ex ≈ E_r even at low R.

---

## Error-exponent optimization over ρ and Q

**When.** Any numerical or analytic evaluation of E_r(R), R_0, or E_ex(R).

**How.**
1. For fixed ρ, maximize E_0(ρ, Q) over input distributions Q (or minimize F = exp(−E_0), which is convex in Q). Use KT conditions analogous to capacity: each used input has the same “tilted information.”
2. Then maximize E_0(ρ, Q*) − ρ R over ρ ∈ [0,1] for E_r, or ρ ≥ 1 for E_ex.
3. Geometry: E_r(R) is the upper envelope of lines of slope −ρ. At optimum, ρ = −dE_r/dR.
4. Limits: ρ → 0 recovers R = I(Q;P) = C when Q is capacity-achieving; ρ = 1 recovers R_0.

**Key insight.** ρ is a Chernoff / Hölder parameter that interpolates the union bound (ρ = 1) and a typical-set / capacity bound (ρ → 0). Choosing Q for E_0(ρ) is not always the same as choosing Q for C; symmetric channels collapse to uniform Q for all ρ.

**Trade-offs.** Inner max over Q is a convex program (in F); outer max over ρ is one-dimensional. Wrong units (bits vs nats) break E_0 − ρR. Using only ρ = 1 near capacity can underestimate the exponent badly.

---

## Distance-spectrum analysis for convolutional / linear codes

**When.** Bounding P_e for a specific linear or convolutional encoder, or designing taps for threshold decoding.

**How.**
1. Linearity: pairwise errors depend on the Hamming weight of the difference word, not on the transmitted word. The spectrum is the weight distribution of the code (or of convolutional code sequences).
2. Union bound: P_e ≤ ∑_d A_d P_2(d), where A_d is the number of weight-d words (or paths) and P_2(d) is the two-word error for distance d (Chernoff or exact BSC Q-function analog).
3. Convolutional: count paths that diverge and remerge (later: generating functions). Gallager’s threshold analysis replaces the full spectrum by an orthogonal-check count 2e.
4. Sequential decoding: the same tree’s incorrect-path metrics are large-deviation events; computation tails are governed by E_0(1) vs R.

**Key insight.** One generating matrix determines an entire distance profile. Orthogonal checks are a combinatorial stand-in for “designed distance” that yield a majority decoder instead of ML.

**Trade-offs.** Union-bound + spectrum is ML-oriented and can be tight at high SNR / low R; it does not automatically yield E_r(R). Threshold decoding uses only a few checks, so it cannot harvest the full spectrum as constraint length grows — hence Gallager’s warning that P_e will not vanish. Sequential decoding harvests the tree but is limited by R_0 and by buffer/computation tails, not by d_free alone.

---

## Other recurring moves

- **Kraft / tree counting:** prefix codes as D-ary trees; uniquely decodable cannot beat prefix (McMillan).
- **Fano inequality:** H(M|Y) ≤ h(P_e) + P_e ln(M−1); the engine of converses (Ch 4, Ch 9).
- **Data processing:** I(X;Z) ≤ I(X;Y) along Markov chains; quantization cannot help C.
- **Convexity:** I concave in Q, convex in P; R(d*) convex in d*; exp(−E_0) convex in Q. Guess a symmetric optimizer and verify KT rather than searching blindly.
- **Typicality / covering:** ~e^{nH} source blocks; ~e^{n R(d*)} reproduction words cover the distortion ball (Ch 3, Ch 9).
- **Waterfilling:** Lagrange allocation of energy (or distortion) across parallel Gaussian eigenmodes (Ch 7–9).
- **Interleaving reduction:** if memory dies, a burst channel contains a DMC of the same single-letter P(y|x); do not claim a capacity loss from memory without ISI.
