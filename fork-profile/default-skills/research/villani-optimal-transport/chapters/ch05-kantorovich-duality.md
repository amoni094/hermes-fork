# Chapter 5: Cyclical Monotonicity and Kantorovich Duality

**Book pages:** 51–92  
**Hermes relevance:** HIGH — Provides the theoretical basis for computing routing costs via duality without solving the full transport problem.

## Key Concepts

### Cyclical Monotonicity (Definition 5.1)
A set Γ ⊂ X×Y is **c-cyclically monotone** if for any finite collection
(x₁,y₁),...,(xN,yN) in Γ:
```
Σᵢ c(xᵢ,yᵢ) ≤ Σᵢ c(xᵢ,yᵢ₊₁)    (yₙ₊₁ := y₁)
```
Intuition: you cannot reduce cost by rerouting mass along any cycle.

**Theorem (Rockafeller):** An optimal transport plan is always concentrated on
a c-cyclically monotone set. Conversely (under mild conditions), concentration
on such a set implies optimality.

### c-Convexity (Definition 5.2)
A function ψ: X → ℝ∪{−∞} is **c-convex** if:
```
ψ(x) = sup_y [φ(y) − c(x,y)]
```
for some function φ: Y → ℝ∪{−∞}.

- The **c-transform** of φ: `φᶜ(x) = sup_y [φ(y) − c(x,y)]`
- The **c-subdifferential** of ψ at x: `∂ᶜψ(x) = { y : ψ(x) + c(x,y) = φ(y) }`
- For c=d (distance): c-convex ⟺ 1-Lipschitz
- For c=|x−y|²/2 in ℝⁿ: c-convex ⟺ convex (standard convexity)

### Kantorovich Duality (Theorem 5.10)
Under mild conditions:
```
C(µ,ν) = inf_{π∈Π(µ,ν)} ∫c dπ = sup_{φ(y)−ψ(x)≤c(x,y)} [∫φ dν − ∫ψ dµ]
```

The supremum is attained, and optimal potentials (ψ,φ) satisfy:
- ψ is c-convex, φ = ψᶜ
- Complementary slackness: φ(y) − ψ(x) = c(x,y) on the support of an optimal plan

### Kantorovich–Rubinstein (Particular Case 5.16)
For c = d (distance) on Polish space X:
```
W₁(µ,ν) = sup { ∫ψ dµ − ∫ψ dν : ψ 1-Lipschitz }
```
This is the most computationally tractable case.

### Brenier Dual (Particular Case 5.17)
For c(x,y) = −x·y (equivalent to |x−y|²/2):
```
sup E[X·Y] = inf { ∫φ dµ + ∫φ* dν }
```
where φ* is the Legendre transform. The inf is over convex functions φ.

## Hermes Application

**Routing cost as dual:** Given two routing distribution snapshots µ,ν, compute
W₁(µ,ν) by solving the 1-Lipschitz dual — avoids constructing the transport plan.
For higher-order costs, use entropic regularization (Peyré–Cuturi).

**Optimality certificate:** A plan π is optimal iff it is concentrated on a
c-cyclically monotone set. Can verify near-optimality by checking cycle
improvements on sampled point sets.
