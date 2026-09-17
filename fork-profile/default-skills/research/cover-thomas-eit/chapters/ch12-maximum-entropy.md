# Chapter 12: Maximum Entropy

## Core Idea
The distribution that maximizes entropy (or differential entropy) given moment constraints is an exponential family: f^*(x) ∝ exp(λ0 + ∑ λ_i r_i(x)). This is Jaynes’ prescription, Boltzmann’s counting, and the I-projection of the uniform/Lebesgue prior onto the constraint set. Burg’s theorem: the maxent process given autocorrelations R_0..R_p is Gauss–Markov of order p.

## Key Concepts
- **Maxent problem**: max h(f) (or H(p)) s.t. ∫_S f = 1, ∫ f r_i = α_i, f≥0 on S.
- **Exponential family solution**: f^*(x) = exp(λ0 + ∑_{i=1}^m λ_i r_i(x)) on S, λ chosen to meet the moments.
- **Uniqueness**: f^* uniquely maximizes entropy; equivalently it uniquely minimizes D(f||f0) for a reference f0 (uniform / Lebesgue).
- **Anomalous maxent**: constraints can be incompatible with a density (e.g. conflicting support/moments) or yield improper λ.
- **Burg**: given R(0),...,R(p), maxent spectrum is all-pole: S(λ) = σ^2 / |1+∑_{k=1}^p a_k e^{−ikλ}|^2.

## Frameworks and Methods
- **Lagrange in function space**: δ/δf [ −∫ f log f + λ0(1−∫f) + ∑ λ_i (α_i − ∫ f r_i) ] = 0 ⇒ −log f −1 −λ0 −∑ λ_i r_i = 0.
- **Information inequality proof**: for any f satisfying the constraints, h(f^*)−h(f)=D(f||f^*)≥0. This is the clean uniqueness proof (Thm 12.1.1).
- **Physics**: macrostate P has |T(P)|≈2^{nH(P)} microstates; the maxent macrostate dominates (AEP / types).
- **Spectrum**: maximize h of a Gaussian process = (1/2)log(2πe)+ (1/4π)∫ log S(λ) dλ subject to ∫ S(λ) e^{ikλ} dλ = R(k).

## Key Results and Theorems

**Theorem 12.1.1 (Maximum entropy distribution).** If f^*(x)=exp(λ0+∑ λ_i r_i(x)) satisfies the moment constraints, then f^* uniquely maximizes h(f) over all densities meeting those constraints.
Proof: h(f^*)−h(f)=∫ f log(f^*/f)= −D(f||f^*)+∫ f log f^* −∫ f^* log f^*, and log f^* is linear in the r_i’s so the constraints cancel.

**Standard examples.**
- Support [a,b], no moments: uniform.
- Support R, fixed EX^2=σ^2: N(0,σ^2).
- Support (0,∞), fixed EX: exponential.
- Support {1..6}, fixed EX=α: p_i ∝ e^{λ i} (Boltzmann dice).
- Support R^+, fixed E log X and EX: Gamma (etc.).

**Dice / Boltzmann.** n dice, total spots nα. Most probable face frequencies are the maxent p^* with mean α. By types, P(P̂ ≈ p^* | mean = α) → 1.

**Burg’s maximum entropy theorem.** Among stochastic processes with given R(0),...,R(p), the entropy *rate* is maximized by the p-th order zero-mean Gauss–Markov process matching those autocorrelations. Entropy rate
h^* = (1/2) log(2πe |K_p| / |K_{p−1}|),
and the spectrum is the all-pole form above.

**Gaussian process entropy rate.** h = (1/2) log(2πe) + (1/4π) ∫_{−π}^{π} log S(λ) dλ.

## Key Equations
- f^*(x) = exp(λ0 + ∑ λ_i r_i(x)),  x∈S
- h(f^*)−h(f)=D(f||f^*)≥0 under matching moments
- N(0,σ^2) maxent on R given variance
- Burg: S(λ)=σ^2 / |1+∑ a_k e^{−ikλ}|^2
- h^* = ½ log(2πe |K_p|/|K_{p−1}|)

## Worked Example
Max h(X) on R given EX=0, EX^2=σ^2. Exponential family: f ∝ exp(λ1 x + λ2 x^2). Completing the square forces Gaussian N(0,σ^2). Any other density with the same second moment has strictly smaller h, by D(f||N)>0.

Dice mean α=4 on {1..6}: p_i ∝ e^{λ i}, λ>0 (tilted toward high faces). This is also Sanov’s I-projection of uniform onto {P: E[X]=4} (Ch 11).

## Anti-patterns
- **Maxent without specifying the constraint set and support**: the answer is undefined (Lebesgue vs counting measure).
- **Treating maxent as a probability law of nature rather than an I-projection**: operationally it is the typical macrostate under a uniform prior on microstates.
- **Using too many autocorrelation lags**: Burg with p=n−1 interpolates noise; choose p by MDL (Ch 14).
- **Forgetting uniqueness comes from strict convexity of −h / of D**.
- **Anomalous constraints**: e.g. EX^2=1 and support in [−0.1,0.1] — empty set.

## Key Takeaways
1. Maxent under linear constraints ⇒ exponential family.
2. Proof is D(f||f^*)≥0, not formal Lagrange theater.
3. Boltzmann counting + types justify maxent physically.
4. Burg: maxent spectrum given p lags is Gauss–Markov p / all-pole.

## Connects To
- **Ch 8**: Gaussian maxent is the m=1, r(x)=x^2 case.
- **Ch 11**: I-projection / Sanov; maxent is min D(P||U).
- **Ch 14**: MDL chooses the constraint order p.
- **Ch 16–17**: entropy rates of Gaussians; determinant inequalities.
