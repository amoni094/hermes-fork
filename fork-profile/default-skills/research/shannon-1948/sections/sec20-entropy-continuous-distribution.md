# Section 20: Entropy of a Continuous Distribution

## Core Idea
Continuous entropy is H = −∫ p(x) log p(x) dx. Most discrete properties survive, but H is relative to the coordinate system (changes by −E[log |J|]) and can be negative. Rates and capacities, being differences of entropies, are coordinate-invariant and non-negative. Gaussians maximize entropy under second-moment constraints.

## Key Concepts
- **Definition**: 1-D: H = −∫_{−∞}^{∞} p(x) log p(x) dx. n-D: H = −∫ p(x1…xn) log p dx1…dxn.
- **Joint / conditional**:
  - H(x,y) = −∬ p(x,y) log p(x,y) dx dy
  - Hx(y) = −∬ p(x,y) log[p(x,y)/p(x)] dx dy
  - Hy(x) = −∬ p(x,y) log[p(x,y)/p(y)] dx dy
- **Coordinate dependence**: “In the discrete case the entropy measures in an absolute way the randomness of the chance variable. In the continuous case the measurement is relative to the coordinate system.”
- **Arbitrary zero**: “The scale of measurements sets an arbitrary zero corresponding to a uniform distribution over a unit volume. A distribution which is more confined than this has less entropy and will be negative.”

## Key Results
1. If x is confined to volume v, max H(x) = log v, achieved at p = 1/v.
2. H(x,y) ≤ H(x)+H(y), equality iff independence.
3. Averaging p'(y) = ∫ a(x,y) p(x) dx with ∫ a dx = ∫ a dy = 1, a≥0, does not decrease entropy.
4. H(x,y) = H(x)+Hx(y) = H(y)+Hy(x); Hx(y) ≤ H(y).
5. **Maxent, fixed variance σ**: p is Gaussian. Calculus of variations with constraints ∫ p x^2 = σ^2, ∫ p = 1 gives p(x) = (1/√(2πσ²)) exp(−x²/(2σ²)). In n-D, fixed second moments A_{ij} ⇒ n-dimensional Gaussian with those moments.
6. **Gaussian entropy**: 1-D, H = log √(2πe) σ. n-D with quadratic form a_{ij}: H = log (2πe)^{n/2} |a_{ij}|^{−1/2}.
7. **Half-line, fixed mean a**: maxent p(x) = (1/a) e^{−x/a} (x>0), H = log(e a).
8. **Change of coordinates** y = y(x): H(y) = H(x) − ∫ p(x) log |J(x/y)| dx. Linear y_j = ∑ a_{ij} x_i: H(y) = H(x) + log |a_{ij}|. Rotations (J=1): H unchanged.
9. Derived rates and capacities “depend on the difference of two entropies and this difference does not depend on the coordinate frame.” Rates and capacities are always non-negative.

## Key Equations
- H = −∫ p log p
- H_Gaussian(σ) = log √(2πe σ²) = log(σ √(2πe))
- H_n(a_{ij}) = (n/2) log(2πe) − (1/2) log |a_{ij}|
- H(y) = H(x) − E[log |J|]
- maxent N(0,σ²); maxent exponential on [0,∞)

## Significance
Differential entropy is introduced with its pitfalls (coordinate-dependence, possible negativity) and its saving grace (mutual information is invariant). The Gaussian maxent property is the engine of the AWGN capacity formula (Theorem 17) and of entropy power.

## Connects To
- Sec 6: discrete properties 1–6, now 1–4 and 8.
- Sec 21: ensemble entropy; white noise maxent for given power.
- Sec 24: R as difference, or as ∬ p(x,y) log[p(x,y)/(p(x)p(y))] to avoid ∞−∞.
- Appendix 7: measure-theoretic mutual information that covers both cases.
