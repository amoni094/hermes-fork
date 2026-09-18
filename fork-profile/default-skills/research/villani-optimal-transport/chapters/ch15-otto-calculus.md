# Chapter 15: Otto Calculus

**Book pages:** 421–434  
**Hermes relevance:** MEDIUM — Provides the Riemannian structure on Wasserstein space underlying gradient flows and displacement convexity.

## Core Idea

Felix Otto discovered that (P₂ᵃᶜ(M), W₂) can be treated as an
infinite-dimensional Riemannian manifold, with a formal metric that gives
meaningful geometric formulas. This "Otto calculus" is heuristic (not
rigorous at the differential-geometric level) but produces correct results
when formulas are verified independently.

## The Tangent Space

At µ ∈ P₂ᵃᶜ(M), the tangent space is identified with:
```
Tµ P₂ ≅ { −∇·(µ∇ψ) : ψ ∈ C∞(M) }
```
A tangent vector −∇·(µ∇ψ) represents an "infinitesimal push" of µ in
direction ∇ψ. The Riemannian metric is:
```
⟨−∇·(µ∇ψ), −∇·(µ∇φ)⟩µ = ∫ ∇ψ·∇φ dµ
```

## Gradient Formula (Otto)

For the energy functional Uν(µ) = ∫U(ρ) dν where µ = ρν:
```
gradµ Uν = −∇·(µ ∇(U'(ρ)))
```
Equivalently: the "direction of steepest ascent" pushes mass along ∇(U'(ρ)).

**Key examples:**
| Functional | Gradient |
|-----------|---------|
| H(µ) = ∫ρ log ρ dvol (entropy) | −∆µ (Laplacian) |
| Hν(µ) = ∫ρ log(ρ/e^{-V}) dν (relative entropy) | −Lµ = −(∆−∇V·∇)µ |
| H^{(m)}(µ) = ∫(ρᵐ−ρ)/(m−1) dvol | −∆(ρᵐ)µ |

**Reading:** gradµ H = −∆µ means: the heat equation ∂ₜρ = ∆ρ is the
gradient flow of the (negative) entropy in Wasserstein space.

## Hessian Formula (Formula 15.7)

For tangent vector µ̇ = −∇·(µ∇ψ):
```
Hessµ Uν(µ̇) = ∫ Γ₂(ψ) p(ρ) dν + ∫ (Lψ)² p₂(ρ) dν
```
where:
- p(ρ) = ρU'(ρ) − U(ρ) is the pressure
- p₂(ρ) = ρp'(ρ) − p(ρ) is the iterated pressure  
- Γ₂(ψ) = ½L(|∇ψ|²) − ∇ψ·∇(Lψ) is the Bakry–Émery Γ₂ operator
- L = ∆ − ∇V·∇ is the distorted Laplacian

**Interpretation:** The Hessian formula gives the curvature of the energy
landscape in Wasserstein space. If Hessµ Uν ≥ K for all µ,µ̇, then Uν is
K-displacement convex (converges to minimum at rate e^{−2Kt}).

## Pressure Functions

For U(ρ) = ρˢ:
- p(ρ) = (s−1)ρˢ
- p₂(ρ) = (s−1)(s−2)ρˢ... wait: p₂(ρ) = ρp'(ρ)−p(ρ) = (s−1)²ρˢ... 

For U(1) = ρ log ρ:
- p(ρ) = ρ (ideal gas)
- p₂(ρ) = 0

For U(m) = (ρᵐ−ρ)/(m−1):
- p(ρ) = ρᵐ
- p₂(ρ) = (m−1)ρᵐ

## Hermes Application

**Gradient flow as PDE:** Use Otto calculus to understand which PDE a
Wasserstein gradient flow corresponds to. If the routing update is a
gradient flow of KL divergence in W₂, it implements Fokker–Planck dynamics.

**Hessian for convergence:** If Hessµ F ≥ K > 0, then JKO gradient flow
of F converges at rate e^{−Kt}. Use as convergence certificate for routing
algorithms.

**Limitation:** Otto calculus is formal — do not use for existence proofs
without verification. For rigorous results, use displacement convexity
theorems (Ch. 16–17) directly.
