# Chapter 7: Memoryless Channels with Discrete Time

## Core Idea
The random-coding theorem extends from finite alphabets to discrete-time channels with real (or continuous) alphabets. Capacity and E_r(R) are still max of I and of E_0 − ρR, now with integrals and input constraints (especially energy). Additive Gaussian noise with an energy constraint is the main example; parallel Gaussians waterfill.

OCR note: the narrative body of Ch 7 is missing from the OCR dump (only exercises at line 17735). This chapter is reconstructed from the ToC (§7.1–7.5), cross-references in Ch 4–5, and the exercise set.

## Key Concepts
- Discrete-time memoryless channel with continuous output (and possibly continuous input): specified by a transition density p(y | x), independent across time.
- Unconstrained inputs: I(X;Y) may be infinite (e.g. infinite-precision X through a noiseless real channel). Capacity problems are only well-posed with constraints.
- Constrained inputs: X ∈ [−A, A], or E[X^2] ≤ E, or a finite subset of amplitudes.
- Additive noise: Y = X + Z, Z independent of X. Additive Gaussian: Z ~ N(0, σ^2).
- Energy-constrained AWGN: C = (1/2) ln(1 + E/σ^2) nats per use (one real dimension).
- Parallel Gaussian channels: N independent AWGN uses with variances σ_n^2 and total energy ∑ E_n ≤ E. Capacity-achieving powers waterfill.
- E_0(ρ, Q) for densities: E_0(ρ, Q) = −ln ∫ [∫ Q(dx) p(y|x)^{1/(1+ρ)}]^{1+ρ} dy.
- Very noisy / Rayleigh-fading examples in exercises: ML metrics can be non-Euclidean (e.g. minimize ∑ |y_n| on a one-sided fading model).

## Frameworks and Methods
- Discretize then take limits: Gallager repeatedly tells the reader to use a finite input set, apply Ch 5, then let the set get finer. Exercise 7.3 (erasure on (0,1)) is the prototype.
- Theorem 5.6.1 generalizes by replacing sums over x, y with integrals; the ρ-union lemma is measure-theoretic but mechanically the same.
- Constraints enter as the domain of Q. Energy constraint: maximize I or E_0 over distributions on R with second moment ≤ E. Gaussian Q is optimal for AWGN.
- Parallel channels: reduce to a single “vector” DMC; allocate energy to equalize water levels μ − σ_n^2.

## Key Results and Theorems
- Unconstrained continuous input can yield infinite C; always state the constraint.
- Additive Gaussian noise, energy E, noise variance σ^2:
  C = (1/2) ln(1 + E/σ^2).
  Achieved by X ~ N(0, E).
- Random-coding exponent: same parametric form E_r(R) = max_{ρ∈[0,1]} [E_0(ρ) − ρR] with Gaussian (or discrete) Q as appropriate. Critical rate and R_0 remain defined via ρ = 1.
- Parallel AWGN with ∑ E_n ≤ E:
  E_n = (μ − σ_n^2)_+, choose μ so the sum of energies is E.
  C = ∑ (1/2) ln(1 + E_n/σ_n^2).
- Bounded amplitude plus bounded uniform noise can collapse to a BEC or a discrete-input channel (Exercise 7.5): the maximizing Q is discrete, masses on a grid.
- Two-word ML error on parallel Gaussians is a Gaussian tail in Euclidean distance; the optimal energy allocation at R = 0 matches the expurgated zero-rate exponent (Exercise 7.7).
- Data processing still applies: quantizing Y can only decrease I (Exercise 7.1).

## Algorithms and Techniques
AWGN capacity:
1. Impose E[X^2] ≤ E.
2. Use Gaussian input (or verify KT analog for densities).
3. I(X;Y) = h(Y) − h(Z) = (1/2) ln(2πe(E+σ^2)) − (1/2) ln(2πe σ^2).

Waterfilling (parallel):
1. Scale each channel so the problem matches §7.5 (Exercise 7.6 hint).
2. Pour energy into the lowest-noise channels first.
3. Compute C as sum of scalar AWGN capacities.

Error exponent:
1. Write E_0(ρ) for the Gaussian or the finite constellation actually used.
2. Maximize E_0 − ρR over ρ ∈ [0,1] (and over constellations if constrained).

## Anti-patterns
- Writing C = (1/2) log(1+SNR) without units (nats vs bits) or without saying per real dimension vs per two-dimensional symbol.
- Claiming Gaussian inputs are required at finite N. They maximize I and usually E_0; practical codes use discrete constellations, which need their own E_0(ρ,Q).
- Ignoring amplitude constraints: hard limiters change both C and the optimal Q (discrete).
- Treating fading as AWGN with the average SNR. Exercise 7.2 is a warning: the metric and E_0 change.

## Key Takeaways
1. Continuous alphabets do not change the logic of Ch 5; they add constraints so that I is finite.
2. AWGN capacity is (1/2) ln(1+SNR) nats per real use; waterfilling is the vector extension.
3. Optimal input distributions under amplitude limits are often discrete.
4. Zero-rate exponents still come from two-word (Bhattacharyya / Euclidean) distances.

## Connects To
- Ch 5: Theorem 5.6.1 “easily generalized to nondiscrete channels.”
- Ch 4: same max-I definition of C.
- Ch 8: pass from discrete time to waveforms via orthonormal expansions; AWGN becomes white Gaussian noise.
- Ch 9: Gaussian sources with MSE distortion are the dual of this channel.
- Ch 6.9: sequential decoding metrics become log p(y|x) for these densities.
