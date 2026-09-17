# Wald Sequential Analysis — glossary

**α (Type I error)** — P(reject H₀ | H₀ true). False alarm. (Ch 1, Ch 3)

**β (Type II error)** — P(accept H₀ | H₁ true). Missed detection. (Ch 1, Ch 3)

**A, B** — SPRT boundaries on the likelihood ratio: continue while B < Λ_m < A. Approx A=(1−β)/α, B=β/(1−α). (Ch 3)

**ASN (average / expected sample number)** — E_θ(n). Primary efficiency criterion among tests that meet the OC. (Ch 2.2.2, Ch 3)

**Composite hypothesis** — H that does not pin θ to a single point. Needs weight functions, not a simple likelihood ratio. (Ch 1.2.2, Ch 4)

**c.d.f.** — Cumulative distribution function of a random variable. (Ch 1.1.2)

**Grouping** — Taking observations in batches rather than one-at-a-time; slightly inflates ASN. (Ch 5.6)

**Indifference zone** — Parameter values where neither error is of practical importance; OC unconstrained; ASN typically largest. (Ch 2.3.1)

**Likelihood ratio Λ_m** — p_{1m}/p_{0m} = ∏ f(x_i,θ₁)/f(x_i,θ₀). SPRT's sufficient statistic. (Ch 3)

**OC (operating characteristic)** — L(θ) = P(accept H₀ | θ). (Ch 2.2.1)

**Overshoot** — Λ_n crossing A or B by more than the exact boundary (discrete z). Makes the A,B approximation slightly conservative. (Ch 3)

**Risk function** — Expected loss of a multi-valued sequential plan; used with ASN to choose among plans. (Ch 10.4)

**Simple hypothesis** — Fully specified distribution (single θ). (Ch 1.2.2)

**SPRT** — Sequential probability ratio test: continue iff B < Λ_m < A. Minimizes E(n) at θ₀ and θ₁ among tests with given α, β. (Ch 3, App A.7)

**Truncation** — Forced stop at n_max. Practical; distorts OC/ASN. (Ch 5.7)

**Weight function w(θ)** — Mixing measure over a composite hypothesis so a likelihood ratio can be formed. (Ch 4, App A.8–A.9)

**z_i** — log f(x_i,θ₁)/f(x_i,θ₀). S_m = ∑ z_i is the SPRT random walk. (Ch 3)
