# Cheatsheet: Villani Optimal Transport

## Core Formulas

### Wasserstein Distance
```
Wₚ(µ,ν) = ( min_{π∈Π(µ,ν)} E_{(X,Y)~π}[d(X,Y)^p] )^{1/p}
```

### Kantorovich Duality
```
W₁(µ,ν) = max_{‖f‖_Lip ≤ 1} ( E_µ[f] − E_ν[f] )
W₂(µ,ν)² = max_{ψ convex} ( 2 E_µ[ψ] − E_ν[ψ*] )  [quadratic cost]
```

### Brenier Map (quadratic cost, ℝⁿ)
```
T = ∇ψ,    where ψ is convex
det(∇²ψ(x)) = f(x) / g(∇ψ(x))    [Monge–Ampère]
```

### Displacement Interpolation (quadratic cost, µ₀ ≪ vol)
```
µₜ = ((1−t)·Id + t·∇ψ)# µ₀
W₂(µₛ, µₜ) = |t−s| · W₂(µ₀, µ₁)
```

### Talagrand T₂ Inequality
```
W₂(µ,ν)² ≤ (2/λ) · KL(µ‖ν)     [when ν satisfies T₂(λ)]
```

### JKO Proximal Step
```
µₖ₊₁ = argmin_µ { Φ(µ) + W₂²(µ, µₖ) / (2τ) }
```

### Displacement Convexity (λ-convex F)
```
F(µₜ) ≤ (1−t)F(µ₀) + tF(µ₁) − (λ/2)t(1−t)W₂²(µ₀,µ₁)
→ W₂(µₜ, µ*) ≤ e^{−λt} W₂(µ₀, µ*)    [gradient flow]
```

---

## Gaussian Formulas (Closed Form!)

### Wasserstein-2 between Gaussians
```python
# µ = N(m₀, Σ₀),  ν = N(m₁, Σ₁)
W₂²(µ,ν) = ‖m₀ − m₁‖² + Bures²(Σ₀, Σ₁)

# Bures metric (matrix OT)
Bures²(Σ₀, Σ₁) = tr(Σ₀) + tr(Σ₁) − 2·tr( (Σ₀^{1/2} Σ₁ Σ₀^{1/2})^{1/2} )
```

### Brenier Map between Gaussians
```python
# T: N(m₀,Σ₀) → N(m₁,Σ₁)
A = Σ₀^{-1/2} @ sqrtm(Σ₀^{1/2} @ Σ₁ @ Σ₀^{1/2}) @ Σ₀^{-1/2}
T(x) = m₁ + A @ (x − m₀)
```

### Displacement Interpolation between Gaussians
```python
# µₜ = N(mₜ, Σₜ)
mₜ = (1−t)*m₀ + t*m₁
Aₜ = (1−t)*I + t*A    # where A is Brenier matrix above
Σₜ = Aₜ @ Σ₀ @ Aₜ.T
```

### Wasserstein Barycenter of Gaussians
```python
# Fixed point: Σ* = Σᵢwᵢ · S(Σ*,Σᵢ)  where S = OT map covariance
# Iteration: Σₖ₊₁ = (1/Σ*) · Σᵢwᵢ · (Σ*^{1/2} Σᵢ Σ*^{1/2})^{1/2}
# Mean: m* = Σᵢwᵢmᵢ (linear!)
```

---

## DC Class Membership Quick Check

| U(r) | DC class | Use case |
|------|---------|---------|
| r log r | DC_∞ | KL/entropy, always convex |
| rᵅ, α≥1 | DC_∞ | Lᵅ energy |
| −rᵅ, α<1 | DC_N, N≤1/(1−α) | Rényi entropy |
| −r^{1−1/N} | DC_N (minimal) | Dimension-dependent |
| const | DC_1 (trivial) | Anything works |

**Check U ∈ DC_∞:** Need `p₂(ρ) = ρ²U''(ρ) ≥ 0` for all ρ > 0.

---

## Talagrand Constants

| Distribution ν | T₂ constant λ | Notes |
|---------------|--------------|-------|
| 𝒩(0, σ²I) | 1/σ² | Exact |
| Uniform on [0,L] | π²/L² | Via Poincaré |
| Log-concave, V L-smooth, K-convex | K | Brascamp–Lieb |
| Manifold with Ric ≥ κ > 0 | κ | Bakry–Émery |
| Product ν^⊗N | λ/N | Tensorization |

---

## Regularity Conditions

| Cost | Domain | Regularity result |
|------|--------|-----------------|
| ‖x−y‖²/2 | ℝⁿ, convex supp | T ∈ C^{k+1,α} if f,g ∈ C^{k,α} |
| |x−y|, p=1 | ℝ | T = F_ν^{-1}∘F_µ (always monotone) |
| d(x,y)² on sphere | Hemisphere | T smooth |
| d(x,y)² on full sphere | Whole sphere | T may fail |
| General cost | Manifold | Requires MTW; usually fails |

**MTW fails for:** p-power costs (|x−y|^p, p>2), most Riemannian manifolds.

---

## Complexity Reference

| Task | Exact complexity | Approximate |
|------|----------------|------------|
| W₁, discrete N pts | O(N³) LP | O(N/ε) entropic |
| W₂, discrete N pts | O(N³) LP | O(N²/ε²) Sinkhorn |
| Brenier map T (ℝⁿ) | Solve Monge–Ampère | Not practical generally |
| Wasserstein barycenter | N × OT per step | Iterative Sinkhorn |
| Gaussian W₂ | O(d³) matrix ops | O(d²) with decomposition |
| JKO step | 1 OT solve + opt step | Sinkhorn + gradient |

---

## Key Inequalities

```
W₁ ≤ W₂ ≤ (W₂/W₁)^{1/2}·W₁ ≤ diam·TV    [hierarchy]
W₁(µ,ν) ≥ |E_µ[X] − E_ν[X]|              [mean difference]
W₂(µ,ν)² ≥ ‖E_µ[X] − E_ν[X]‖²           [mean squared]
W₂(µ,ν)² ≥ |tr(Σ_µ) − tr(Σ_ν)|²/d       [variance difference; rough]
TV(µ,ν)² ≤ 2·KL(µ‖ν)                     [Pinsker]
W₂(µ,ν)² ≤ (2/λ)·KL(µ‖ν)               [Talagrand T₂]
```

---

## Villani vs Peyré–Cuturi Reference

| Topic | Villani (theory) | Peyré–Cuturi (algorithms) |
|-------|-----------------|--------------------------|
| Existence & uniqueness | ✓✓✓ | brief |
| Kantorovich duality | ✓✓✓ | ✓ |
| Displacement interpolation | ✓✓✓ | ✓ |
| Regularity (MTW) | ✓✓✓ | minimal |
| Displacement convexity | ✓✓✓ | ✓ |
| Gradient flows | ✓✓ | ✓ |
| Sinkhorn algorithm | ✗ | ✓✓✓ |
| POT library | ✗ | ✓✓✓ |
| Sliced Wasserstein | ✗ | ✓✓ |
| Computational examples | ✗ | ✓✓✓ |
