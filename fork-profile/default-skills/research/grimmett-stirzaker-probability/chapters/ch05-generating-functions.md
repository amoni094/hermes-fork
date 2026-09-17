# Chapter 5: Generating Functions and Applications

## Core Idea
Probability generating functions (PGFs), moment generating functions (MGFs), and characteristic functions transform convolutions into products and encode all distributional information. Characteristic functions always exist and characterize distributions uniquely; the CLT is proved by showing their pointwise convergence to exp(−t²/2).

## Frameworks Introduced

- **PGF**: GX(s) = E(sX) for non-negative integer X. GX+Y(s) = GX(s)·GY(s) for independent X,Y. E(X) = G'(1), var(X) = G''(1) + G'(1) − G'(1)².
  
- **MGF**: M(t) = E(e^{tX}). Finite on open interval containing 0 → moments via M^(k)(0) = E(Xk). Independent sum: M_{X+Y}(t) = MX(t)·MY(t). May not exist (Cauchy).

- **Characteristic function (CF) φ(t) = E(e^{itX})**:
  - Always exists (|φ(t)| ≤ 1)
  - Uniquely determines distribution (inversion theorem)
  - Independent sum: φ_{X+Y}(t) = φX(t)·φY(t)
  - Bochner's theorem: φ is a CF iff positive-definite, uniformly continuous, φ(0)=1
  - Moments: φ^(k)(0) = iᵏ E(Xk) when E|Xk| < ∞

- **CLT via CFs** (§5.10.4): If Xi iid mean 0 var σ², then φ_{Sn/σ√n}(t) = [φX(t/σ√n)]ⁿ → exp(−t²/2). Lévy continuity theorem converts this to distributional convergence.

- **Large deviations** (§5.11): P(Sn ≥ na) ≈ exp(−nI(a)) where I(a) = sup_t {ta − log M(t)} is the rate function (Legendre transform of log-MGF). For rare events, exponential decay.

## Key Concepts

- **PGF** — generating function for integer-valued r.v.; encodes probabilities as Taylor coefficients
- **MGF** — E(e^{tX}); exists when distribution has light tails
- **Characteristic function φ** — E(e^{itX}); always exists, Fourier dual of PDF
- **Inversion theorem** — distribution uniquely recoverable from φ
- **Lévy continuity theorem** — φn → φ pointwise iff Xn →D X (when φ is continuous at 0)
- **Cumulant** — κn = n-th derivative of log φ at 0; κ₁=mean, κ₂=variance
- **Rate function I(a)** — Legendre transform of log M; governs large deviation probabilities
- **Branching process extinction** — η = P(extinction) is smallest non-negative root of G(s) = s

## Anti-patterns

- **Relying on MGF when it doesn't exist**: Heavy-tailed distributions (Cauchy, Pareto) have MGF = ∞. Always check domain; use characteristic functions instead.
- **Moment problem non-uniqueness**: Moments alone don't always determine the distribution (log-normal counterexample). CFs do determine it uniquely.

## Key Takeaways

1. Characteristic functions always exist and uniquely determine distributions — prefer them over MGFs for general results.
2. CLT: (Sn−nμ)/σ√n →D N(0,1) whenever E(X₁²) < ∞.
3. Lévy continuity theorem: convergence of CFs ↔ convergence in distribution.
4. Large deviations: exponential tail bounds via rate function I(a) = sup_t{ta − log M(t)}.
5. For sums of independent r.v.s: log φ_{X+Y} = log φX + log φY (cumulants are additive).

## Connects To

- **Ch07**: CLT proved here; LLN proved in Ch07 without CFs.
- **Ch10**: PGFs used for renewal theory; branching processes via G(s)=s.
- **Ch12**: Wald's identity uses MGF to analyze stopping times.
