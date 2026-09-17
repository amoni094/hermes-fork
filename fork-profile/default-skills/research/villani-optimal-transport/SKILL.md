---
name: villani-optimal-transport
description: >
  Knowledge base from Optimal Transport: Old and New by Villani. Use when
  applying Wasserstein distances, displacement interpolation, Brenier theorem,
  displacement convexity, geodesics in probability space, and regularity theory
  of OT maps to distribution comparison, skill embedding geometry, and
  probabilistic routing in Hermes.
tags: [optimal-transport, wasserstein, probability, geometry, math]
book: "Optimal Transport: Old and New"
author: "Cédric Villani"
year: 2009
pages: 969
book_type: technical
depth: study
---

# Villani – Optimal Transport: Old and New

## Book Overview

Villani's treatise is the theoretical foundation for optimal transport (OT). It
covers measure-theoretic underpinnings (Parts I–III) and is notably more
abstract than Peyré–Cuturi. The book's computational payoff concentrates in
**Part I** (qualitative theory, Chapters 4–13) and selected chapters from
**Part II** (Riemannian geometry of probability space, Chapters 14–25). Part
III (synthetic Ricci curvature, Chapters 26–30) is relevant primarily for
theoretical guarantees, not runtime algorithms.

**Key coverage map:**

| Chapter | Title | Hermes relevance |
|---------|-------|-----------------|
| 5 | Cyclical monotonicity & Kantorovich duality | HIGH – routing cost duality |
| 6 | Wasserstein distances | HIGH – distribution metrics |
| 7 | Displacement interpolation | HIGH – geodesic interpolation |
| 9–10 | Monge problem solutions | MEDIUM – existence & uniqueness |
| 12 | Smoothness (regularity) | HIGH – when OT maps are differentiable |
| 13 | Qualitative picture | HIGH – unified summary |
| 15 | Otto calculus | MEDIUM – Riemannian structure of P₂ |
| 16–17 | Displacement convexity I & II | HIGH – convergence proofs |
| 20 | Infinitesimal displacement convexity | MEDIUM |
| 22 | Concentration inequalities | MEDIUM – Talagrand T₂ |
| 23 | Gradient flows I | MEDIUM – JKO / Wasserstein gradient flows |
| 28 | Stability of optimal transport | LOW-MEDIUM |

---

## Core Theoretical Framework

### 1. Kantorovich Duality (Ch. 5)

The primal Kantorovich problem:
```
C(µ,ν) = inf_{π∈Π(µ,ν)} ∫ c(x,y) dπ(x,y)
```
has a dual:
```
C(µ,ν) = sup { ∫φ dν − ∫ψ dµ : φ(y)−ψ(x) ≤ c(x,y) }
```

For `c = d` (a distance), this collapses to the **Kantorovich–Rubinstein formula**:
```
W₁(µ,ν) = sup { ∫ψ dµ − ∫ψ dν : ψ is 1-Lipschitz }
```

For `c(x,y) = |x−y|²/2` in ℝⁿ, optimal ψ is convex and `T = ∇ψ` (Brenier).

**c-convexity:** A function ψ: X → ℝ∪{−∞} is c-convex if
`ψ(x) = sup_y [φ(y) − c(x,y)]` for some φ. Optimal potentials are always
c-convex. The c-subdifferential `∂ᶜψ` carries the optimal transport plan.

**Cyclical monotonicity:** A set Γ ⊂ X×Y is c-cyclically monotone iff
`Σ c(xᵢ,yᵢ) ≤ Σ c(xᵢ,yᵢ₊₁)` for all finite cycles. An optimal plan is
always concentrated on such a set.

### 2. Wasserstein Distances (Ch. 6)

**Definition:** For p ≥ 1 and (X,d) Polish metric space:
```
Wₚ(µ,ν) = ( inf_{π∈Π(µ,ν)} ∫ d(x,y)ᵖ dπ )^{1/p}
```

**Wasserstein space Pₚ(X):** Probability measures with finite p-th moment,
equipped with Wₚ. This is a complete separable metric space when X is.

**Topology:** Wₚ convergence ⟺ weak convergence + convergence of p-th moments.

**Key advantages over other metrics:**
1. Strong enough to detect large displacements (unlike weak-* distance)
2. Rich duality (especially p=1 via Kantorovich–Rubinstein)
3. Upper bounds easy: any coupling gives an upper bound
4. Respects geometry: C-Lipschitz f induces C-Lipschitz pushforward on P₁

**Comparison with other distances:**
- W₁ ≤ W₂ ≤ ... (Hölder)
- W₁ ≥ bounded-Lipschitz distance (dbL)
- W₂ is the natural metric for displacement interpolation

### 3. Displacement Interpolation (Ch. 7)

**McCann interpolation (Theorem 7.21):** Given µ₀, µ₁ ∈ P₂(M) with µ₀
absolutely continuous, there exists a unique geodesic (µₜ)_{t∈[0,1]} in
Wasserstein space. For quadratic cost on ℝⁿ:
```
µₜ = ((1−t)Id + t∇ψ)# µ₀
```
where ψ is the Brenier potential.

**Properties:**
- Intermediate measures µₜ are absolutely continuous if either endpoint is
- Trajectories are minimizing geodesics in (P₂, W₂) — no crossings at t∈(0,1)
- W₂(µₛ, µₜ) = |t−s| · W₂(µ₀, µ₁) — constant speed geodesic

**General Lagrangian setting:** For Lagrangian L(x,v,t), the displacement
interpolation lifts to the space of paths. Trajectories satisfy Euler–Lagrange
equations; for quadratic Lagrangian, they are straight lines (geodesics).

### 4. Brenier's Theorem (Ch. 9–10)

**Theorem (Brenier/McCann):** If µ ≪ vol and c(x,y) = |x−y|²/2 on ℝⁿ, then:
1. The optimal transport plan is unique and deterministic: π = (Id, T)#µ
2. T = ∇ψ for some convex function ψ (the Brenier map)
3. T is the unique µ-a.e. gradient of a convex function pushing µ to ν

**On Riemannian manifolds (McCann):** T(x) = expₓ(−∇ψ(x)) where ψ is
c-convex with c = d²/2.

### 5. Regularity Theory (Ch. 12)

The OT map T = ∇ψ satisfies the **Monge–Ampère equation:**
```
det(∇²ψ(x)) = f(x) / g(∇ψ(x))
```
(quadratic cost). For general cost, it becomes:
```
det(∇²ψ(x) + ∇²ₓₓc(x,T(x))) = |det ∇²ₓᵧc| · f(x)/g(T(x))
```

**Critical negative result (Theorem 12.7):** If the c-subdifferential at some
point is disconnected, there exist smooth densities for which the OT map is
discontinuous. Regularity requires "Assumption (C)": c-subdifferentials are
connected (c-convex).

**MTW condition / Regular cost (Definition 12.14):** Cost c is *regular* if
for any x and c-convex ψ, the contact set ∂ᶜψ(x) is c-convex. This is the
Ma–Trudinger–Wang (MTW) condition. Fails for most Riemannian manifolds.

**Practical consequence:** For general distributions and manifolds, OT maps are
NOT smooth. Regularity is the exception, not the rule. Design algorithms to
work without regularity.

### 6. Displacement Convexity (Ch. 16–17)

**Definition:** A functional F: P₂(M) → ℝ is displacement convex if it is
convex along every Wasserstein geodesic:
```
F(µₜ) ≤ (1−t)F(µ₀) + t F(µ₁)
```

**Displacement convexity class DCN:** U ∈ DCN if the functional
`Uν(µ) = ∫U(ρ) dν` (µ = ρν) is displacement convex on manifolds with
dimension ≥ N and non-negative Ricci curvature.

**Key examples in DC∞ (all dimensions):**
- U(r) = r log r  → entropy H(µ) = ∫ρ log ρ dν (relative entropy / KL divergence)
- U(r) = rᵅ, α ≥ 1

**Key examples in DCN:**
- U(r) = −r^{1−1/N}  (minimal representative)
- Rényi entropies for appropriate parameters

**Theorem (Generalization):** On a manifold with Ric ≥ K, the functional
F = Uν with U ∈ DCN is K-displacement convex (Hessian ≥ K in Wasserstein
sense). This implies convergence of gradient flows at rate e^{−Kt}.

### 7. Otto Calculus (Ch. 15)

**Riemannian structure on P₂(M):** The tangent space at µ ∈ P₂ᵃᶜ(M) is
identified with gradients of functions:
```
Tµ P₂ ≅ { −∇·(µ∇ψ) : ψ smooth }
```
with inner product `⟨ξ,η⟩µ = ∫ ∇ψ·∇φ dµ` (where ξ=−∇·(µ∇ψ)).

**Gradient formula (Otto):** For Uν(µ) = ∫U(ρ) dν:
```
gradµ Uν = −∇·(µ ∇(U'(ρ)))
```
**Key example:** gradµ H = −∆µ (gradient of entropy = Laplacian)

**Hessian formula (Formula 15.7):**
```
Hessµ Uν(µ̇) = ∫Γ₂(ψ) p(ρ) dν + ∫(Lψ)² p₂(ρ) dν
```
where p = ρU'(ρ) − U(ρ) (pressure), Γ₂ is Bakry–Émery operator.

### 8. Gradient Flows in Wasserstein Space (Ch. 23)

**JKO scheme (Jordan–Kinderlehrer–Otto):** The gradient flow of energy Φ in
P₂ is approximated by:
```
µ_{k+1} = argmin_µ { Φ(µ) + W₂(µ, µ_k)² / (2τ) }
```
Each step is a proximal step in Wasserstein metric. This gives a rigorous
meaning to PDEs as Wasserstein gradient flows.

**Examples of PDEs as gradient flows:**
- Heat equation ∂ₜρ = ∆ρ  →  gradient flow of entropy H(µ) = ∫ρ log ρ
- Fokker–Planck ∂ₜρ = ∆ρ + ∇·(ρ∇V)  →  gradient flow of free energy
- Porous medium equation ∂ₜρ = ∆(ρᵐ)  →  gradient flow of Rényi entropy

**Derivative of Wasserstein distance (Theorem 23.9):**
```
d/dt W₂(µₜ,ν)² = 2∫ vₜ·∇φₜ dµₜ
```
where vₜ is the velocity field of (µₜ) and φₜ is the Kantorovich potential.

### 9. Concentration Inequalities (Ch. 22)

**Talagrand transport inequality T₁(λ):**
```
W₁(µ,ν) ≤ √(2 H(µ|ν) / λ)
```

**Talagrand T₂(λ):**
```
W₂(µ,ν)² ≤ (2/λ) H(µ|ν)
```
where H(µ|ν) = ∫ log(dµ/dν) dµ is the relative entropy (KL divergence).

T₂ implies Gaussian concentration. Satisfied by log-concave measures (Ric ≥ λ).

**Practical use:** If you have a KL bound between distributions, T₂ gives a
W₂ bound — bridging information-theoretic and geometric distances.

---

## Hermes Application Patterns

### Routing cost via Kantorovich duality
Instead of computing the primal OT transport plan, compute the dual potentials
(ψ, φ) using entropic regularization (see Peyré–Cuturi skill for algorithms).
The dual value equals the primal transport cost — use as routing cost metric.

### Displacement interpolation between skill distributions
Given skill embedding distributions µ₀ (current router state) and µ₁ (target
state), the geodesic path µₜ = ((1−t)Id + t∇ψ)#µ₀ provides a principled
interpolation. **Feasibility concern:** Computing ∇ψ requires solving Brenier
problem — use Sinkhorn approximation for runtime.

### Displacement convexity for convergence analysis
If a routing loss functional is displacement convex (e.g., entropy of routing
distribution), then gradient descent in Wasserstein space converges
exponentially. Use DCN membership check as a convergence guarantee:
- KL divergence from target → DC∞ → exponential convergence guaranteed
- Non-convex objectives → no guarantee

### Wasserstein barycenter for skill aggregation
The Wasserstein-2 barycenter of skill distributions {µ₁,...,µN} is:
```
µ* = argmin_µ Σᵢ wᵢ W₂(µ, µᵢ)²
```
This is a fixed-point problem. At theoretical level: unique if one µᵢ is
absolutely continuous. Runtime: requires iterative OT solvers per step.

### Regularity check before differentiable scoring
OT map T is smooth (C∞) only if: (a) source and target densities are C∞,
(b) their supports are convex (Caffarelli theory), (c) cost satisfies MTW.
For skill embeddings in non-Euclidean spaces (e.g., hyperbolic), MTW fails
generically — do not assume smooth T.

---

## Feasibility Assessment for Runtime Use

| Operation | Feasibility | Notes |
|-----------|-------------|-------|
| W₁ via Kantorovich–Rubinstein | HIGH | Linear program or 1-Lipschitz dual |
| W₂ approximation via Sinkhorn | HIGH | See Peyré–Cuturi skill |
| Exact Brenier map (∇ψ) | LOW | Requires Monge–Ampère solve |
| Displacement interpolation µₜ | MEDIUM | Feasible with Sinkhorn approx |
| Wasserstein barycenter | MEDIUM | Fixed-point iteration, expensive |
| JKO proximal step | LOW-MEDIUM | One OT solve per step |
| Regularity verification (MTW) | LOW | No practical algorithm for general c |
| Gradient flow simulation | LOW | Requires many JKO steps |

---

## Chapter Files

See `chapters/` for detailed notes on:
- ch05-kantorovich-duality.md
- ch06-wasserstein-distances.md
- ch07-displacement-interpolation.md
- ch12-smoothness-regularity.md
- ch13-qualitative-picture.md
- ch15-otto-calculus.md
- ch16-displacement-convexity.md
- ch22-concentration-inequalities.md
- ch23-gradient-flows.md

See also: `glossary.md`, `patterns.md`, `cheatsheet.md`

## Related Skills
- `peyre-cuturi-optimal-transport` — Algorithmic counterpart (Sinkhorn, POT library)
- `jaynes-probability` — Bayesian framework for KL / entropy connections
- `kreyszig-functional-analysis` — Functional analysis background
