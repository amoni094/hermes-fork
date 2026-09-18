# Chapter 23: Gradient Flows I

**Book pages:** 629–692  
**Hermes relevance:** MEDIUM — JKO scheme provides the link between OT and optimization algorithms in probability space.

## Gradient Flows in Abstract Metric Spaces

A gradient flow of energy Φ in a Riemannian manifold M satisfies:
```
dX(t)/dt = −gradΦ(X(t)),    d/dt Φ(X(t)) = −‖gradΦ‖²
```

**Reformulations (Proposition 23.1):** The above is equivalent to:
1. (Maximal slope) `d/dt Φ(X(t)) = −|∇⁻Φ|²(X(t))`
2. (Metric inequality) `d/dt d(X(t),y)² ≤ 2[Φ(y) − Φ(X(t))] − 2|∇⁻Φ|²(X(t))`
3. (EVI) For λ-convex Φ: `d⁺/dt d(X(t),y)²/2 ≤ Φ(y) − Φ(X(t)) − (λ/2)d(X(t),y)²`

The **EVI (Evolution Variational Inequality)** formulation (3) extends to metric
spaces without differentiable structure.

## Gradient Flows in Wasserstein Space

**Jordan–Kinderlehrer–Otto (JKO) discovery:** Many PDEs are gradient flows in
(P₂(M), W₂). Specifically, ∂ₜρ = −gradρ Uν in Wasserstein space corresponds
to a PDE in ρ.

**Examples:**
| Energy Φ(µ) | Gradient flow PDE | Equation |
|------------|------------------|---------|
| H(µ) = ∫ρ log ρ dvol | ∂ₜρ = ∆ρ | Heat equation |
| Hν(µ) = ∫ρ log(ρ/e^{−V}) dν | ∂ₜρ = ∆ρ + ∇·(ρ∇V) | Fokker–Planck |
| H^{(m)}(µ) = ∫(ρᵐ−ρ)/(m−1) | ∂ₜρ = ∆(ρᵐ) | Porous medium |
| F(µ) = ∫V dµ + W₂(µ,ν)² | → JKO step | Proximal update |

## Gradient Flow in Geodesic Space (Definition 23.7)

X(t) is a gradient flow trajectory of Φ in geodesic space (X,d) if:
```
d⁺/dt d(X(t),y)²/2 ≤ d/ds⁺ Φ(γₛ)|_{s=0}
```
for any y ∈ X and any geodesic γ from X(t) to y.

For λ-convex Φ, this implies the EVI:
```
d⁺/dt d(X(t),y)²/2 ≤ Φ(y) − Φ(X(t)) − (λ/2) d(X(t),y)²
```

## Derivative of the Wasserstein Distance (Theorem 23.9)

For absolutely continuous curves (µₜ), (µ̃ₜ) in P₂ᵃᶜ(M):
```
d/dt W₂(µₜ, µ̃ₜ)² = 2∫ vₜ·∇φₜ dµₜ + 2∫ ṽₜ·∇φ̃ₜ dµ̃ₜ
```
where vₜ is velocity field of (µₜ), φₜ is Kantorovich potential from µₜ to µ̃ₜ,
and similarly for tilded quantities.

**Special case:** d/dt W₂(µₜ, ν)² ≤ 2∫ vₜ·∇φₜ dµₜ where φₜ is the
potential from µₜ to ν.

## The JKO Scheme (Proximal Point Algorithm in W₂)

Given step size τ > 0 and initial µ₀, define recursively:
```
µₖ₊₁ = argmin_{µ∈P₂(M)} { Φ(µ) + W₂(µ, µₖ)² / (2τ) }
```

**Convergence:** As τ → 0, the piecewise-constant interpolation converges to
the gradient flow of Φ. The convergence is in W₂ topology.

**Existence of minimizers:** If Φ is lower-semicontinuous and has compact
sublevel sets in P₂, then each step has a unique minimizer (when Φ is
strictly displacement convex).

## Hermes Application

**Routing update as JKO step:** Each routing update can be framed as a JKO
proximal step minimizing a routing loss Φ plus a W₂ regularizer penalizing
large distribution shifts.

**Practical JKO:** Each JKO step requires solving an OT problem (to compute
W₂) plus minimizing the energy. Use:
1. Sinkhorn algorithm for W₂ approximation (ε-regularized)
2. Fixed-point iteration for the minimization

**Convergence guarantee:** If Φ is λ-displacement convex, JKO converges
at rate O(e^{−λt}) — exactly like Euclidean gradient descent with strongly
convex objective.

**Heat equation interpretation:** Routing that minimizes KL-divergence while
regularizing by W₂ distance = Fokker–Planck dynamics in embedding space.

**Feasibility:** One JKO step = one OT solve. At inference time, this is
expensive (O(n² log n) for Sinkhorn). Use for offline routing policy updates,
not real-time decisions.
