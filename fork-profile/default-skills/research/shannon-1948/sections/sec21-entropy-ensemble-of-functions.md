# Section 21: Entropy of an Ensemble of Functions

## Core Idea
For an ergodic bandlimited ensemble, entropy per degree of freedom is the limit of (1/n) times the continuous entropy of n successive samples; entropy per second is 2W times that. White noise maximizes entropy for given power N. Long sample vectors occupy a well-defined high-probability volume of log-radius H'. Entropy power is the white-noise power with the same entropy.

## Key Concepts
- **H' (per degree of freedom)**: H' = lim_{n→∞} (−1/n) ∫ p(x1…xn) log p dx.
- **H (per second)**: divide by time T rather than n; n = 2TW so H = 2W H'.
- **Entropy power N1**: “the power in a white noise limited to the same band as the original ensemble and having the same entropy.” Geometrically, squared radius of a sphere with the same high-probability volume. N1 ≤ actual power, with equality iff white.

## Key Results
White thermal noise, power N: p Gaussian, H' = log √(2πe N), H = W log(2πe N). For given average power N, white noise has the maximum possible entropy (Gaussian maxent, Sec 20).

**AEP for densities.** If p(x1…xn) is continuous in all xi for all n, then for large n, | (log p)/n − H' | < ε except on a set of probability < δ.

**Volume version.** V_n(q) = smallest volume containing probability q. Then lim (log V_n(q))/n = H' for q ≠ 0,1.

Thus for large n there is a well-defined high-probability volume, and inside it the density is relatively uniform (logarithmically).

**White noise geometry.** p depends only on ∑ x_i²: spherical symmetry. High-probability region is a sphere of radius √(nN). As n→∞, P(outside √(n(N+ε))) → 0, and (1/n) log(volume) → log √(2πe N).

**Definition.** If H' is the entropy per degree of freedom,

N1 = (1/(2πe)) exp(2 H')

Entropy power of any noise ≤ actual power.

## Key Equations
- H' = lim (−1/n) ∫ p log p
- H = 2W H'
- white: H' = log √(2πe N),  H = W log(2πe N)
- N1 = exp(2H') / (2πe)
- lim (log V_n(q))/n = H'

## Significance
Entropy power converts an abstract differential entropy into a comparable wattage. It is the continuous analogue of 2^H typical-set size. Theorems 15, 18, 23 are all stated in entropy-power form.

## Connects To
- Sec 7: discrete AEP; here volume replaces counting.
- Sec 22: filters multiply entropy power by the geometric-mean gain.
- Sec 23 / Theorem 15: entropy-power inequalities for sums.
- Sec 25: C bounds in terms of N and N1.
