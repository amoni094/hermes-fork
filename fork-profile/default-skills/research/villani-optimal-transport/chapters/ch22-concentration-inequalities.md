# Chapter 22: Concentration Inequalities

**Book pages:** 567–628  
**Hermes relevance:** MEDIUM — Talagrand transport inequalities connect KL divergence to Wasserstein distance; useful for bounding distribution shifts.

## Core Connection

Marton's key insight: concentration of measure can be encoded via **transport
inequalities** of the form:
```
∀µ ∈ P(X),   C(µ,ν) ≤ Eν(µ)
```
where C(µ,ν) is OT cost and Eν is an energy (e.g., relative entropy = KL divergence).

## Talagrand Transport Inequalities

### T₁(λ) Inequality
```
W₁(µ,ν)² ≤ (2/λ) H(µ|ν)
```
where H(µ|ν) = ∫ log(dµ/dν) dµ is the KL divergence.

**Equivalent to:** Gaussian concentration for 1-Lipschitz functions:
```
∀r ≥ 0, ν[f ≥ ∫f dν + r] ≤ exp(−λr²/2)
```

### T₂(λ) Inequality
```
W₂(µ,ν)² ≤ (2/λ) H(µ|ν)
```

**Stronger than T₁:** T₂ ⟹ T₁ (by W₁ ≤ W₂).

**T₂ is equivalent to:** Log-Sobolev inequality (LSI) with constant λ.

**Gaussian measure γ satisfies T₂(1):** `W₂(µ,γ)² ≤ 2 H(µ|γ)`

### Product Measures (Tensorization)
If ν satisfies T_p(λ), then ν^⊗N satisfies T_p(λ/N) on X^N with the ℓᵖ
product distance. This is the foundation for Talagrand's concentration results
on product spaces.

## Gaussian Concentration (Theorem 22.10)

The following are equivalent for ν ∈ P₁(X):
1. ν satisfies T₁(λ)
2. ν satisfies Gaussian concentration: ν[A] ≥ ½ ⟹ ν[Aᵣ] ≥ 1 − exp(−λr²/2)
3. For all 1-Lipschitz f: P(f(X) ≥ ∫f dν + r) ≤ exp(−λr²/2)
4. The moment generating function of the distance is bounded: ∫e^{ad²} dν < ∞ for some a

## Concentration via Ricci Curvature (Theorem 22.14)

If M has Ric ≥ K > 0 and ν = vol/vol(M), then ν satisfies T₂(K):
```
W₂(µ,ν)² ≤ (2/K) H(µ|ν)
```

More generally: log-concave measures satisfy T₂ with constant related to their
log-Sobolev constant.

## Log-Sobolev and Poincaré Inequalities (Theorem 22.17)

If ν satisfies LSI(λ): `∫f² log f² dν − ‖f‖²_2 log ‖f‖²_2 ≤ (2/λ) ∫|∇f|² dν`

Then ν satisfies T₂(λ): `W₂(µ,ν)² ≤ (2/λ)H(µ|ν)`

## Hermes Application

**KL-to-Wasserstein bridge:** If routing distribution µ is close to target ν
in KL divergence (H(µ|ν) ≤ ε), then by T₂:
```
W₂(µ,ν) ≤ √(2ε/λ)
```
This converts information-theoretic distance (easier to compute) into
geometric distance (more interpretable).

**Distribution shift bounding:** If a skill distribution shifts by ε in KL,
its Wasserstein-2 distance shifts by at most √(2ε/λ). Use for sensitivity
analysis of routing decisions.

**Practical note:** T₂ requires the reference measure ν to be log-concave
or to have bounded curvature. For arbitrary distributions on high-dimensional
embedding spaces, the constant λ may be very small (poor concentration).

**High-dimensional caveat:** Gaussian concentration becomes meaningful only
when dimension d is "small" relative to the sample size. For skill embeddings
in high-d spaces (d > 100), empirical Wasserstein distances have large
variance — use regularized versions.
