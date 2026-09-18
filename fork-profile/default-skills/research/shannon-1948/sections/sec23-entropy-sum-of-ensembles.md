# Section 23: Entropy of a Sum of Two Ensembles

## Core Idea
Adding two ensembles (convolution of their sample densities) corresponds to adding noises or signals. Entropy power of the sum lies between the sum of entropy powers and the sum of actual powers. Small signals added to white Gaussian noise are “absorbed”: the result is nearly Gaussian with power N + P_signal.

## Key Concepts
- **Sum of ensembles**: r = p ∗ q on the n-sample vectors. Physically, add the waveforms.
- **Entropy powers** N1, N2 of the summands; N3 of the sum; actual powers N1, N2 (Shannon’s notation overlaps: N1, N2 for powers and N1, N2 with bars/underscores for entropy powers in the paper).

## Key Results
**Theorem 15.** Let the average powers be N1, N2 and entropy powers N̄1, N̄2. Entropy power of the sum N̄3 satisfies

N̄1 + N̄2  ≤  N̄3  ≤  N1 + N2

Upper bound: max entropy for power N1+N2 is white noise of that power, entropy power N1+N2. Lower bound: Appendix 6; Gaussians with proportional covariance matrices achieve the minimum.

**Absorption in white noise.** White Gaussian noise “can absorb any other noise or signal ensemble which may be added to it with a resultant entropy power approximately equal to the sum of the white noise power and the signal power … provided the signal power is small, in a certain sense, compared to noise.”

Geometry: rotate to principal axes of the signal’s second-moment form b_ii. Require each b_ii ≪ N (noise variance per coordinate). Convolution ≈ Gaussian with variances N + b_ii. Entropy power ≈ [∏(N+b_ii)]^{1/n} ≈ N + (1/n)∑ b_ii = N + P_signal.

## Key Equations
- r(x) = ∫ p(y) q(x−y) dy
- N̄1 + N̄2 ≤ N̄3 ≤ N1 + N2
- small signal: N̄_{n+s} ≈ N + P_s

## Significance
Theorem 15 is Shannon’s entropy-power inequality (EPI) in the form needed for capacity bounds. The absorption argument is why, at high SNR, arbitrary noise “looks white” after a strong white signal is added, so upper and lower capacity bounds meet (Theorems 18–19).

## Connects To
- Appendix 6: variational proof that proportional Gaussians minimize N̄3.
- Sec 25: lower bound C ≥ W log((P+N1)/N1) uses N̄(signal+noise) ≥ P + N̄_noise.
- Sec 26: small peak-S/N limit uses the absorption theorem.
- Sec 29: rate bounds for non-white sources vs mean-square fidelity.
