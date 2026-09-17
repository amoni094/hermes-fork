# Appendix 7: Abstract Definition of Rate and Dimension Rate

## Core Idea
Mutual information (rate R) is defined as the least upper bound of discrete approximations on a probability space of pairs (x,y), covering discrete, continuous, and mixed cases. Processing the output cannot increase R. Dimension rate generalizes 2W samples/s to arbitrary ensembles via covering numbers.

## Key Concepts
- **Probability space of pairs (x,y)**: x = transmitted, y = received, duration T.
- **Strips**: the set of pairs whose x lies in S1 (strip over S1); analogously for y.
- **Finite partitions** Xi of x-space, Yi of y-space. Approximate rate

R1 = (1/T) ∑_{i} P(Xi, Yi) log [ P(Xi,Yi) / (P(Xi) P(Yi)) ]

P(Xi) = measure of the strip over Xi, etc.

- **Dimension rate λ**: covering numbers N(ε, δ, T) = least number of centers so that all but measure δ of the ensemble is within distance ε (e.g. RMS over [0,T]) of some center.

## Key Results
**Monotonicity under refinement.** Subdividing a cell never decreases R1. Proof: replacing one pair (X1,Y1) by a split X1=X1′+X1″ replaces (d+e) log[(d+e)/(a(b+c))] by d log(d/(a b)) + e log(e/(a c)), which is larger by the log-sum inequality / convexity. “The various possible subdivisions form a directed set, with R monotonic increasing with refinement.”

**Definition.** R = lub R1, written

R = (1/T) ∬ P(x,y) log [P(x,y)/(P(x)P(y))] dx dy

“understood in the above sense.” Includes discrete, continuous, “and of course many others which cannot be represented in either form.”

**Invariance and data processing.**
- If x and u are in 1-1 correspondence, R(u;y) = R(x;y).
- If v is any function of y (not necessarily invertible), R(x;v) ≤ R(x;y), because y-partitions refine v-partitions.
- If y and v are only statistically related, still R(x;v) ≤ R(x;y). “Any operation applied to the received signal, even though it involves statistical elements, does not increase R.”

**Dimension rate.**

λ = lim_{δ→0} lim_{ε→0} lim_{T→∞}  [log N(ε, δ, T)] / (T log ε)

“A generalization of the measure type definitions of dimension in topology.” Bandlimited case: λ = 2W.

## Key Equations
- R1 = (1/T) ∑ P(Xi,Yi) log [P(Xi,Yi)/(P(Xi)P(Yi))]
- R = lub R1
- R(x;v) ≤ R(x;y)
- λ = lim lim lim log N(ε,δ,T) / (T log ε)

## Significance
This is Kolmogorov–Gelfand–Yaglom style mutual information before that school, and a packing-dimension rate that later reappears in ε-entropy (Kolmogorov, 1956) and rate-distortion. The data-processing inequality is here: encoding/decoding cannot beat C (Sec 24). The integral form of R avoids ∞−∞.

## Connects To
- Sec 12, 24: R as H(x)−Hy(x) or the integral.
- Sec 19: bandlimited dimension rate 2W.
- Sec 28: R1 for sources; Theorem 21.
- Sec 24: binary digits at rate C; processing inequality.
