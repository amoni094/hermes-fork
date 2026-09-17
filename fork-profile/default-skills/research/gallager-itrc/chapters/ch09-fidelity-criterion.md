# Chapter 9: Source Coding with a Fidelity Criterion

## Core Idea
When perfect reconstruction is impossible or unnecessary, the figure of merit is average distortion d. The rate-distortion function R(d*) is the minimum mutual information I(X; X̂) over test channels satisfying E[d(X,X̂)] ≤ d*, and it is the operational rate needed to reproduce the source at distortion d*. Combined with channel capacity, R(d*) < C is the joint source–channel condition.

OCR note: narrative body missing from OCR (exercises at line 18477). Reconstructed from ToC §9.1–9.8, Ch 1 and Ch 3 cross-references, and problems (Hamming reproductions, convexity of R(d*), lemma 9.3.1).

## Key Concepts
- Distortion measure d(k, j): cost of representing source letter k by reproduction j. May be infinite on forbidden pairs.
- Single-letter distortion on blocks: d_N(x, x̂) = (1/N) ∑ d(x_n, x̂_n). Average distortion D = E[d_N].
- Rate-distortion function R(d*) of a source: minimum rate (nats per letter) such that some code of that rate achieves average distortion ≤ d* as N → ∞.
- Information-theoretic characterization: R(d*) = min I(X; X̂) over P(x̂ | x) with E[d(X,X̂)] ≤ d*.
- Test channel: the minimizing P(x̂ | x); not a physical channel — a variational object.
- Converse to the noisy-channel coding theorem revisited: sending a source over a channel of capacity C cannot achieve distortion below the d* with R(d*) = C.
- Continuous amplitudes: differential entropy appears; for Gaussian sources with square-error, R(d*) has a closed form.
- Gaussian process sources: waterfilling in reverse — discard eigenmodes below a distortion floor.
- Discrete ergodic sources: the theorem extends from i.i.d. to ergodic dependence via blocks.

## Frameworks and Methods
- Dual of capacity: capacity maximizes I over inputs given a channel; R(d*) minimizes I over reverse channels given a distortion constraint.
- Convexity: R(d*) is convex ∪, decreasing in d*. Infinite d on some pairs can make R not strictly convex (Problem 9.1).
- Random coding for sources: generate reproduction codebooks i.i.d. ~ the output of the test channel; encode x to a nearby codeword (typicality / covering). Lemma 9.3.1 is the covering tool used in exercises.
- Separation: compress to rate just above R(d*), then channel-code at rate < C. Joint coding cannot beat this asymptotically for this distortion class.

## Key Results and Theorems
- Coding theorem for sources with a fidelity criterion: for i.i.d. discrete sources and bounded single-letter distortion, distortion d* is achievable at any rate R > R(d*), and is not achievable at R < R(d*).
- R(d*) = min_{P(x̂|x): E d ≤ d*} I(X; X̂).
- Shannon lower bound / calculation: use symmetry to guess P(j | k) and verify by convexity of I in the test channel (Problem 9.1 hint).
- Hamming binary source, Hamming distortion: R(d*) = ln 2 − H_b(d*) for 0 ≤ d* ≤ 1/2, and 0 for d* ≥ 1/2.
- Converse revisited: if a source is sent over a DMC of capacity C, then any achievable distortion satisfies R(d*) ≤ C. Thus H < C is the lossless special case R(0) ≤ C when R(0) = H.
- Gaussian i.i.d. source, MSE: if X ~ N(0, σ^2) and d(x,x̂) = (x−x̂)^2,
  R(d*) = (1/2) ln(σ^2 / d*) for d* ≤ σ^2, and 0 otherwise.
- Gaussian processes: reverse waterfill — each eigenmode gets distortion min(λ_i, θ); rate is ∑ (1/2) ln(λ_i / θ)_+.
- Hamming codes as lossy compressors (Problem 9.2): map 7-bit strings to the nearest (7,4) Hamming codeword and send 4 bits; rate (4/7) ln 2, distortion = probability of not being a codeword times Hamming distance statistics. Generally above R(d*).

## Algorithms and Techniques
Computing R(d*) (discrete memoryless source):
1. Fix a Lagrange multiplier s ≤ 0 relating rate and distortion.
2. Optimize the test channel: P(j|k) ∝ Q(j) e^{s d(k,j)} (Blahut–Arimoto is later; Gallager uses convexity and KT).
3. Evaluate I and D; vary s to trace R(d*).

Operational encoding (existence):
1. Draw M = e^{NR} reproduction words i.i.d. ~ Q*.
2. Encode x to an x̂_m with small d_N(x, x̂_m) if one exists; else fail.
3. For R > R(d*), failure probability → 0.

Gaussian MSE:
1. If σ^2 ≤ d*, send nothing, D = σ^2.
2. Else send a Gaussian code of power σ^2 − d* over a notional AWGN of noise d* (test channel X̂ = X + Z is backward; forward is the dual AWGN).

## Anti-patterns
- Using lossless Huffman on quantized analog data and calling the bit rate R(d*). Quantizer + entropy code is a specific point on or above R(d*).
- Minimizing I without the distortion constraint (that would give 0).
- Assuming R(d*) is always strictly convex; infinite-distortion alphabets can create linear segments.
- Joint source–channel “cleverness” at large N: separation is asymptotically optimal here.
- Applying the Gaussian formula to non-Gaussian sources; it is a lower bound for MSE among sources with the same variance, not the rate of an arbitrary source.

## Key Takeaways
1. R(d*) is the source-coding dual of C: min I vs max I.
2. Lossless coding is R(0) = H when zero distortion is allowed on a discrete alphabet.
3. Reliable communication of a source at quality d* requires R(d*) < C.
4. Gaussian MSE and reverse waterfilling are the canonical continuous examples.

## Connects To
- Ch 3: lossless discrete coding is the d* = 0 corner.
- Ch 4–5: C and E_r(R) are the channel half of separation.
- Ch 7–8: Gaussian channels dual Gaussian sources; waterfilling vs reverse waterfilling.
- Ch 2: I(X;X̂) is the same mutual information.
