# Appendix 6: Entropy Power of a Sum (Proof of Theorem 15)

## Core Idea
If two ensembles of powers N1, N2 and entropy powers N̄1, N̄2 are added, the sum’s entropy power N̄3 satisfies N̄1 + N̄2 ≤ N̄3 ≤ N1 + N2. The minimum is achieved by Gaussians with proportional covariance.

## Key Concepts
- **Convolution**: r(x) = ∫ p(y) q(x−y) dy on n-sample vectors.
- **Entropy power**: N̄ = exp(2H′)/(2π e) with H′ entropy per degree of freedom.

## Key Results
**Upper bound.** Maximum entropy for power N1+N2 is white noise of that power, whose entropy power is N1+N2. Hence N̄3 ≤ N1 + N2.

**Lower bound (calculus of variations).** Minimize H3 = −∫ r log r subject to fixed H1, H2. Varying p at si varies r by q(x−si). Stationarity:

∫ q(x − si) log r(x) dx = −μ log p(si)
∫ p(x − si) log r(x) dx = −ν log q(si)

Multiplying by p(si) or q(si) and integrating: H3 = −μ H1 = −ν H2.

Gaussians with quadratic forms Aij, Bij (inverses aij, bij) have convolution Gaussian with cij = aij + bij. These satisfy the stationarity conditions iff aij = K bij, i.e. the covariances are proportional, and then give the minimum H3. In that case entropy powers add: N̄3 = N̄1 + N̄2.

## Key Equations
- N̄1 + N̄2 ≤ N̄3 ≤ N1 + N2
- cij = aij + bij  (Gaussian inverse-covariance add)
- minimum iff aij = K bij

## Significance
This is Shannon’s entropy-power inequality (EPI). It powers the lower bound of Theorem 18 (arbitrary-noise capacity) and the small-signal absorption argument (white noise “absorbs” a weak additive ensemble). Stam (1959) and Blachman (1965) later gave complete proofs; Shannon’s variational argument identifies the minimizer but is not a full existence/uniqueness proof by later standards.

## Connects To
- Theorem 15 (Sec 23): statement.
- Theorems 18–19 (Sec 25): C bounds.
- Theorem 20 small-S/N limit; Theorem 23 source-rate bounds.
