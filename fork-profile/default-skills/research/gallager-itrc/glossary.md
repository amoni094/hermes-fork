# Glossary — Gallager, Information Theory and Reliable Communication (1968)

Notation: natural logs unless noted. Rates and capacities in nats. Binary rates appear as R_bits = R / ln 2.

## Source entropy H
H(X) = −∑ P(x) ln P(x). Operationally, the minimum expected code-letter rate (in nats) to represent a discrete memoryless source essentially losslessly (Ch 3). For stationary/Markov sources use the entropy rate H_∞ = lim H(X_1…X_n)/n.

## Mutual information I(X;Y)
I(X;Y) = ∑ P(x,y) ln [P(x,y)/(P(x)P(y))] = H(X) − H(X|Y). The information transferred per ensemble drawing. Capacity and rate-distortion are max / min of this quantity.

## Channel capacity C
For a DMC, C = max_Q I(Q; P) nats per use. Operationally: R < C ⇔ there exist block codes with P_e → 0 (Ch 4 converse + Ch 5 random coding).

## BSC capacity
BSC(ε): C = ln 2 − H_b(ε) nats = 1 − h_2(ε) bits, H_b(ε) = −ε ln ε − (1−ε) ln(1−ε).

## AWGN capacity (discrete time, one real dimension)
C = (1/2) ln(1 + E/σ^2) nats per use, X energy E, noise variance σ^2.

## Bandlimited waveform AWGN
C = W ln(1 + P/(N_0 W)) nats/second. Infinite bandwidth: C → P/N_0 nats/s.

## Error exponent E_r(R) (random-coding)
E_r(R) = max_{0≤ρ≤1} max_Q [E_0(ρ, Q) − ρ R].
P_e ≤ exp(−N E_r(R)) for some (N,R) codes. E_r(R) > 0 iff R < C.

## Gallager function E_0(ρ, Q)
E_0(ρ, Q) = −ln ∑_j [∑_k Q(k) P(j|k)^{1/(1+ρ)}]^{1+ρ}.
E_0(0,Q) = 0, ∂E_0/∂ρ at 0 equals I(Q;P). Convexity: F = e^{−E_0} is convex in Q.

## Cutoff rate R_0
R_0 = max_Q E_0(1, Q).
The ρ = 1 intercept: for R ≤ R_cr one has E_r(R) = R_0 − R (with the maximizing Q). Sequential decoding computation is practical for R < R_0 and explodes for R > R_0. Modern literature calls this the cutoff rate; Gallager works with E_0(1,Q) directly.

## Expurgated exponent E_ex(R) (Gallager E_x)
At low rates, delete bad codewords from a larger ensemble.
E_ex(R') = sup_{ρ≥1} max_Q [E_x(ρ,Q) − ρ R'], with E_x(1,Q) = E_0(1,Q).
P_{e,m} ≤ exp(−N E_ex(R + (ln 4)/N)) uniformly in m. Strictly above E_r at low R except on very noisy channels.

## Random coding bound
Average over an ensemble of codes with independent (or pairwise independent) words ~ Q:
P̄_e ≤ exp(−N E_r(R)).
Existence of at least one code follows. Pairwise independence is enough (used for linear/coset codes).

## Critical rate R_cr
The rate at which the optimizing ρ for E_r hits 1. For R ≥ R_cr, 0 ≤ ρ ≤ 1 is interior or at 0 as R → C; for R ≤ R_cr the bound uses ρ = 1.

## Parity-check (linear) code
(N,L) binary code: x = u G over GF(2). Systematic: information bits appear in x. Parity-check matrix: xH = 0. Syndrome S = yH = zH.

## Coset code
x = uG ⊕ v. Random G,v give pairwise independent words; same E_r on the BSC as unstructured random codes (Theorem 6.2.1).

## Convolutional code
λ source digits in, ν channel digits out, via shift-register linear combinations over a field. Rate R = (λ ln 2)/ν nats per channel digit. Constraint length N = ν L (L = register stages). Systematic if the first λ outputs copy the source digits.

## Free distance / designed distance
Gallager emphasizes Hamming weight of nonzero linear combinations and BCH designed distance. Later convolutional literature’s d_free is the minimum Hamming distance between distinct semi-infinite encoded sequences; threshold decoding uses orthogonal checks rather than d_free.

## Sequential decoding
Tree search with tentative branch hypotheses, backtracking when the path metric fails. Wozencraft (1957) originated it; Gallager presents Fano (1963). Moves: forward, lateral, backward on a replica encoder. Stack algorithm is a later sibling (Zigangirov/Jelinek), not this book’s algorithm.

## Fano algorithm / Fano metric
Γ(x_ℓ; y_ℓ) = ∑ ln[P(y|x)/ω(y)] − (length)·B. Bias B sets the drift. Threshold T is stepped by Δ; search keeps Γ above T.

## Threshold decoding (Massey)
Majority vote on 2e parity checks orthogonal on a noise digit. Corrects that digit if ≤ e of the involved noises are nonzero. Efficient at short constraint length; does not achieve vanishing P_e by letting constraint length → ∞.

## Burst; burst-correcting capability b relative to guard space g
A burst of length b relative to g is a noise run with 1s at both ends, no g consecutive 0s inside, and g 0s on each side. A code has capability b relative to g if every such noise pattern is corrected.

## Interlacing (interleaving)
Split into r coded streams so channel bursts become sparse errors inside each word. Cyclic: g(D) → g(D^r).

## Rate-distortion R(d*)
R(d*) = min {I(X;X̂) : E[d(X,X̂)] ≤ d*}. Operational rate to reproduce a source at average distortion d*. Lossless discrete: R(0) = H.

## LDPC codes
Gallager invented low-density parity-check codes in his 1963 MIT monograph/thesis *Low-Density Parity-Check Codes*, not as a chapter of this 1968 book. ITRC Ch 6 treats dense/algebraic parity-check codes, BCH, convolutional, threshold, and sequential decoding. LDPC: sparse H, iterative (original: Gallager A/B bit-flipping / probability propagation). Mention when tracing the origin of sparse-graph codes; do not cite ITRC as the LDPC construction paper.

## Natural units vs bits
Throughout ITRC, ln and nats. Bits: divide by ln 2. An (N,L) binary code has R = (L ln 2)/N nats = L/N bits per channel digit.
