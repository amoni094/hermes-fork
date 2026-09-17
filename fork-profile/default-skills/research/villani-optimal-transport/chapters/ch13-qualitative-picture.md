# Chapter 13: Qualitative Picture

**Book pages:** 333–352  
**Hermes relevance:** HIGH — Unified summary of what is always true about OT without regularity assumptions.

## What Always Holds (The Robust Theory)

This chapter synthesizes the results of Chapters 4–12 into a qualitative
picture that holds without any smoothness assumptions.

### 1. Existence (Always)

There always exists:
- An optimal coupling (x₀,x₁) with law π (possibly randomized)
- A displacement interpolation (µₜ)_{t∈[0,1]}
- A random minimizing curve γ with law Π

such that law(γₜ) = µₜ and law(γ₀,γ₁) = π.

Individual curves γ satisfy Euler–Lagrange equation:
```
d/dt [∇ᵥL(γₜ,γ̇ₜ,t)] = ∇ₓL(γₜ,γ̇ₜ,t)
```
For quadratic Lagrangian: `d²γₜ/dt² = 0` — straight lines (geodesics).

**Non-crossing:** Two trajectories in supp(Π) may intersect at t=0 or t=1
but never at intermediate times t ∈ (0,1).

### 2. Absolute Continuity Preservation

If either µ₀ or µ₁ is absolutely continuous, then µₜ is absolutely
continuous for all t ∈ (0,1).

### 3. Deterministic Transport (When Source is AC)

If µ₀ ≪ vol, the optimal coupling is:
- **Unique** (in law)  
- **Deterministic:** x₁ = T(x₀)
- **Characterized by:** `∇ψ(x₀) = −∇ₓc(x₀,x₁)`

where ψ is a c-convex function (the Kantorovich potential), and T(x₀) is the
point from which sending to x₀ is "most expensive."

The Brenier map formula on ℝⁿ: `T = ∇ψ` (gradient of convex function).

### 4. Uniqueness of Displacement Interpolation

Under the same assumption (µ₀ ≪ vol), the displacement interpolation (µₜ) is
unique. This follows from the a.s. uniqueness of minimizing curves.

### 5. Potentials

The Kantorovich potentials (ψ,φ) are related by:
- φ(y) = inf_x [ψ(x) + c(x,y)]  (c-transform)
- ψ(x) = sup_y [φ(y) − c(x,y)]  (c-concave transform back)
- On the support of π: φ(y) − ψ(x) = c(x,y)

### 6. Without Regularity: What's Lost

Without MTW/Caffarelli conditions:
- T may be discontinuous (even with smooth densities)
- ∇ψ may not exist classically (only approximate gradients)
- The PDE picture (Monge–Ampère) may not be smooth

**Key insight from Villani:** OT theory works robustly without smoothness.
Many applications (concentration, gradient flows, curvature) only need the
qualitative picture, not smooth maps.

## Practical Summary Table

| Scenario | What's guaranteed |
|----------|-------------------|
| Always | Optimal coupling exists; displacement interpolation exists |
| µ₀ ≪ vol | Transport is deterministic; T = ∇ψ; interpolation unique |
| µ₀ ≪ vol + convex supports + smooth f,g (ℝⁿ) | T is C^{k+1,α} (Caffarelli) |
| µ₀ ≪ vol + MTW cost | T is smooth |
| General Riemannian | T exists; smoothness requires MTW (hard to verify) |

## Hermes Application

This chapter provides the **minimal assumptions** needed for reliable OT-based
algorithms:
1. For any two distributions, OT cost C(µ,ν) is well-defined and computable
2. If source is AC, transport is deterministic — safe to use T for interpolation
3. Smoothness of T is NOT guaranteed — prefer entropic regularization which always gives smooth approximations

**Design rule:** Build Hermes OT components to work with the qualitative
guarantees only. Smoothness is a bonus when Caffarelli conditions hold.
