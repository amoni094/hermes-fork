# Glossary: Optimal Transport (Villani)

## Core Objects

**Coupling / Transference plan π:** A joint probability measure on X×Y with
marginals µ (on X) and ν (on Y). The set of all such couplings is Π(µ,ν).

**Optimal transport cost C(µ,ν):** `inf_{π∈Π(µ,ν)} ∫c(x,y) dπ`. The minimum
expected cost over all ways of jointly distributing mass.

**Monge map T:** A deterministic transport: π = (Id,T)#µ. Exists when µ≪vol.

**Kantorovich potential ψ:** The c-convex function such that T(x)∈∂ᶜψ(x).
For quadratic cost: T = ∇ψ (Brenier potential).

**Wasserstein distance Wₚ:** `(inf_{π∈Π(µ,ν)} ∫d(x,y)ᵖ dπ)^{1/p}`. Metric on Pₚ(X).

**Wasserstein space Pₚ(X):** {µ ∈ P(X) : ∫d(x₀,x)ᵖ dµ < ∞} with metric Wₚ.

**Displacement interpolation (µₜ):** The constant-speed geodesic from µ₀ to
µ₁ in (P₂,W₂). For quadratic cost: µₜ = ((1−t)Id + t∇ψ)#µ₀.

## Duality Concepts

**c-transform (Legendre-type):** `ψᶜ(y) = inf_x [ψ(x) + c(x,y)]`

**c-convex function ψ:** `ψ(x) = sup_y [φ(y) − c(x,y)]` for some φ.

**c-subdifferential ∂ᶜψ(x):** `{y : ψ(x) + c(x,y) = φ(y)}`. The set of
y's "optimally matched" to x.

**c-cyclically monotone set:** Cannot improve cost by rerouting along cycles.
Optimal plans are concentrated on such sets.

**Kantorovich–Rubinstein formula:** W₁(µ,ν) = sup_{ψ 1-Lipschitz} ∫ψ d(µ−ν)

## Regularity

**Monge–Ampère equation:** PDE satisfied by the Brenier potential:
`det(∇²ψ) = f(x)/g(∇ψ(x))`.

**Assumption (C):** c-subdifferentials are connected at every point.
Necessary (and roughly sufficient) for regularity of OT maps.

**MTW condition (Ma–Trudinger–Wang):** Positivity condition on the
MTW tensor: `S(x,y)[ξ,η] ≥ 0`. Equivalent to "regular cost" (Def. 12.14).
Required for smooth OT maps on manifolds.

**Caffarelli regularity:** For quadratic cost + convex supports + smooth
densities in ℝⁿ: T ∈ C^{k+1,α} if f,g ∈ C^{k,α}.

## Geometry of Probability Space

**Otto calculus:** Formal Riemannian structure on P₂ᵃᶜ(M). Tangent vectors
are −∇·(µ∇ψ); metric is `⟨−∇·(µ∇ψ), −∇·(µ∇φ)⟩ = ∫∇ψ·∇φ dµ`.

**Displacement convexity:** Convexity of functional F along Wasserstein
geodesics: F(µₜ) ≤ (1−t)F(µ₀) + tF(µ₁).

**λ-displacement convex:** F(µₜ) ≤ (1−t)F(µ₀) + tF(µ₁) − (λ/2)t(1−t)W₂(µ₀,µ₁)².
Implies gradient flow converges at rate e^{−λt}.

**DCN class:** Functions U: ℝ₊→ℝ for which Uν is displacement convex on
n-dimensional manifolds (N ≥ n) with non-neg curvature. DC_∞ ⊂ DC_N ⊂ DC_1.

**Pressure p(ρ):** `ρU'(ρ) − U(ρ)`. Appears in gradient and Hessian formulas.

**Γ₂ operator (Bakry–Émery):** `Γ₂(f) = ½L(|∇f|²) − ∇f·∇(Lf)`.
Encodes curvature. Γ₂ ≥ K iff Ric_L ≥ K.

## Gradient Flows

**JKO scheme:** `µₖ₊₁ = argmin_µ {Φ(µ) + W₂(µ,µₖ)²/(2τ)}`. Proximal
iteration converging to gradient flow of Φ in Wasserstein space.

**EVI (Evolution Variational Inequality):** `d⁺/dt d(X(t),y)²/2 ≤ Φ(y)−Φ(X(t)) − (λ/2)d²`.
Coordinate-free definition of gradient flow.

**Fokker–Planck equation:** ∂ₜρ = ∆ρ + ∇·(ρ∇V). Gradient flow of
free energy Hν(µ) = ∫ρ log(ρ/e^{−V}) in Wasserstein space.

## Concentration

**Talagrand T₁(λ):** W₁(µ,ν)² ≤ (2/λ)H(µ|ν). Implies Gaussian concentration.

**Talagrand T₂(λ):** W₂(µ,ν)² ≤ (2/λ)H(µ|ν). Equivalent to log-Sobolev.
Satisfied by Gaussian with λ=1, log-concave measures.

**Relative entropy H(µ|ν):** `∫log(dµ/dν) dµ`. Also called KL divergence.
Always ≥ 0; equals 0 iff µ=ν.

**Log-Sobolev inequality (LSI):** `∫f²log f² dν ≤ (2/λ)∫|∇f|² dν + ‖f‖²₂ log‖f‖²₂`.
T₂ is equivalent to LSI with same constant.

## Common Notation

| Symbol | Meaning |
|--------|---------|
| Π(µ,ν) | Set of couplings (joint measures) |
| Wₚ | Wasserstein-p distance |
| Pₚ(X) | Wasserstein space of order p |
| ψᶜ | c-transform of ψ |
| ∂ᶜψ | c-subdifferential |
| T# µ | Pushforward of µ through T |
| H(µ|ν) | Relative entropy (KL divergence) |
| DCN | Displacement convexity class |
| Uν | Energy functional ∫U(ρ)dν |
| Γ₂ | Bakry–Émery curvature operator |
| L | Distorted Laplacian ∆ − ∇V·∇ |
