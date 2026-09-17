# Section 24: The Capacity of a Continuous Channel

## Core Idea
A continuous channel has bandlimited input and output, specified for time T by 2TW numbers. Rate R = H(x) − Hy(x) as in the discrete case; C is the max of R over input ensembles. An integral form of R (mutual information) is preferred because H(x) − Hy(x) may be ∞ − ∞. Binary digits can still be sent at rate C with arbitrarily small error.

## Key Concepts
- **Statistics**: transmitted P(x1…xn)=P(x); noise Px(y)=P(y|x).
- **Coordinate invariance**: R and C do not depend on the coordinate system — numerator and denominator of log[p(x,y)/(p(x)p(y))] pick up the same Jacobian factors.
- **Quantization argument**: divide signal space into small cells so Px(y) is nearly constant on a cell; the discrete proofs apply; capacity is the limit of discrete capacities as cells shrink.
- **Data-processing** (Appendix 7): if u = message, x = signal, y = received, v = recovered, then H(x)−Hy(x) ≥ H(u)−Hv(u), regardless of the maps u→x and y→v. Encoding/decoding binary digits cannot beat C. Conversely, under mild continuity of P(x,y), binary digits can be sent at rate C with arbitrarily small equivocation.

## Key Results
**Definition.**

R = H(x) − Hy(x)

C = Max R  (over input ensembles)

Finite-dimensional form:

C = lim_{T→∞} Max_{P(x)} (1/T) ∬ P(x,y) log [ P(x,y) / (P(x)P(y)) ] dx dy

This integral “will always exist while H(x)−Hy(x) may assume an indeterminate form ∞−∞,” e.g. if x is supported on a lower-dimensional surface.

**Theorem 16 (additive independent noise).** If the received signal is the sum of independent signal and noise, Px(y)=Q(y−x), the noise has a definite entropy H(n) independent of the signal, and

R = H(y) − H(n)

C = Max_{P(x)} H(y) − H(n)

Proof: y=x+n ⇒ H(x,y)=H(x,n); independence ⇒ H(y)+Hy(x)=H(x)+H(n), so H(x)−Hy(x)=H(y)−H(n). Maximizing R is maximizing H(y) subject to the constraints on the transmitted ensemble.

## Key Equations
- R = H(x) − Hy(x) = ∬ p(x,y) log[p(x,y)/(p(x)p(y))] dx dy
- additive: R = H(y) − H(n)
- C = Max H(y) − H(n)

## Significance
This is the continuous mutual-information definition of capacity. Theorem 16 reduces AWGN and colored-noise problems to maxent of the received ensemble. Appendix 7 makes the definition measure-theoretic.

## Connects To
- Sec 12: discrete R and C.
- Sec 25–26: power-constrained specializations.
- Appendix 7: R as lub of discrete approximations; monotonicity under refinement; R(x;v) ≤ R(x;y).
