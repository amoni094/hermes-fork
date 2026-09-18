# Chapters 16–17: Displacement Convexity

**Book pages:** 435–492  
**Hermes relevance:** HIGH — Provides rigorous convergence guarantees for gradient-flow-based routing and aggregation.

## Displacement Convexity (Definition)

A functional F: P₂(M) → ℝ∪{+∞} is **displacement convex** if for every
geodesic (µₜ)_{t∈[0,1]} in (P₂(M), W₂):
```
F(µₜ) ≤ (1−t)F(µ₀) + tF(µ₁)    ∀t ∈ [0,1]
```

**λ-displacement convex:** F(µₜ) ≤ (1−t)F(µ₀) + tF(µ₁) − (λ/2)t(1−t)W₂(µ₀,µ₁)²

This is the same as λ-convexity along geodesics.

**Critical distinction:** Displacement convexity ≠ convexity in the linear
structure of measures. The measure µₜ = (1−t)µ₀ + tµ₁ (mixture) is NOT
the same as the Wasserstein geodesic.

## Displacement Convexity Classes DCN

**Definition 17.1:** U: ℝ₊ → ℝ (twice differentiable on (0,∞)) belongs to
**DC_N** (N ∈ [1,∞]) if any of the equivalent conditions hold:
- (i) p₂(ρ) + p(ρ)/N ≥ 0  for all ρ > 0
- (ii) p(ρ)/ρ^{1−1/N} is nondecreasing (N < ∞) 
- (iii) δ ↦ δᴺ U(δ^{−N}) is convex (N < ∞); or δ ↦ e^δ U(e^{−δ}) is convex (N=∞)

where p(ρ) = ρU'(ρ) − U(ρ) is the pressure, p₂(ρ) = ρp'(ρ) − p(ρ) iterated.

**Class hierarchy:** DC_∞ ⊂ ... ⊂ DC_N ⊂ DC_1 (DC_1 is everything that qualifies).

## Key Examples

| U(r) | Class | Functional Uν(µ) |
|------|-------|------------------|
| r log r | DC_∞ | Boltzmann entropy H(µ) = ∫ρ log ρ dν |
| rᵅ, α≥1 | DC_∞ | Lᵅ energy ∫ρᵅ dν |
| −r^{1−1/N} | DC_N | Rényi entropy (minimal representative of DC_N) |
| −rᵅ, α<1 | DC_N iff N≤(1−α)^{−1} | Rényi entropies |

## Main Theorem: Displacement Convexity on Manifolds

**Theorem 17.15 (McCann / Sturm–Lott–Villani):** If M has dimension n and
Ric ≥ K·g (Ricci curvature bounded below by K), then for any U ∈ DC_N
with N ≥ n, the functional Uν is K-displacement convex on P₂(M).

**Corollaries:**
1. On ℝⁿ (Ric = 0, K=0): Uν is 0-displacement convex (non-negative curvature)
2. On manifolds with Ric ≥ K > 0: exponential convergence of gradient flows
3. Entropy H(µ) = ∫ρ log ρ is always displacement convex on ℝⁿ

## Convergence Implications

**Theorem:** If F is λ-displacement convex (λ > 0), and (µₜ) is a gradient
flow of F in W₂, then:
```
W₂(µₜ, µ*) ≤ e^{−λt} W₂(µ₀, µ*)
```
where µ* is the unique minimizer of F.

**Proof sketch:** λ-convexity gives:
```
F(µ*) ≥ F(µₜ) + ⟨gradF(µₜ), µ* − µₜ⟩ + (λ/2)W₂(µₜ,µ*)²
```
Combined with dF(µₜ)/dt = −‖gradF(µₜ)‖² gives exponential decay.

## Conditions for Non-Strict Displacement Convexity

If K=0 (flat space), displacement convexity gives only convergence as t→∞
(not exponential). In this case, need additional assumptions (e.g., Poincaré
inequality) for quantitative convergence.

## Hermes Application

**Routing convergence guarantee:** If the routing loss functional L(µ)
(e.g., KL divergence from target routing distribution) is λ-displacement
convex, then any Wasserstein gradient flow update converges at rate e^{−λt}.

**Check procedure:**
1. Express loss as Uν with explicit U
2. Compute p(ρ) = ρU'(ρ) − U(ρ) and p₂(ρ) = ρp'(ρ) − p(ρ)
3. Verify p₂ + p/N ≥ 0 → U ∈ DC_N → displacement convex

**KL divergence:** U = ρ log ρ ∈ DC_∞ → always displacement convex →
gradient flow of KL converges to unique minimum.

**Non-convex losses:** If the routing loss is not displacement convex,
no convergence guarantee from OT theory alone.

**Practical caveat:** Computing the full gradient flow requires solving OT
at each step. Use JKO scheme (Ch. 23) with Sinkhorn for approximation.
