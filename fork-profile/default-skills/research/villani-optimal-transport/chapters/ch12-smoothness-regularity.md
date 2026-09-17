# Chapter 12: Smoothness (Regularity of OT Maps)

**Book pages:** 281–332  
**Hermes relevance:** HIGH — Determines when OT maps are differentiable; critical for gradient-based skill scoring.

## Core Problem

The OT map T = ∇ψ satisfies a Monge–Ampère PDE. When is T smooth (C¹ or C∞)?
The answer is: **only under restrictive conditions.** This chapter characterizes
those conditions and explains why smoothness fails generically.

## Monge–Ampère Equation

For quadratic cost c = |x−y|²/2 in ℝⁿ:
```
det(∇²ψ(x)) = f(x) / g(∇ψ(x))
```
where f is the source density (µ = f·vol) and g is the target density (ν = g·vol).

For general cost c(x,y):
```
det(∇²ψ(x) + ∇²ₓₓc(x,T(x))) = |det ∇²ₓᵧc(x,T(x))| · f(x)/g(T(x))
```

## When Regularity Fails

### Caffarelli's Counterexample
Even for the quadratic cost on ℝ², if the support of ν is non-convex (e.g.,
two disjoint balls), the OT map T can be discontinuous — even when µ has
smooth density on a convex domain.

### Theorem 12.7: Smoothness Needs Connected Subdifferentials
**Theorem:** If there exists a c-convex function ψ and point x such that ∂ᶜψ(x)
is disconnected, then there exist C∞ smooth densities f,g for which any optimal
transport map is discontinuous.

**Consequence:** Smoothness requires that all c-subdifferentials are connected.
This is "Assumption (C)."

### MTW Condition Failure
The Ma–Trudinger–Wang condition (regular cost, Definition 12.14) is needed for
full regularity. It fails for:
- c = dᵖ with p > 2 on ℝⁿ
- c = d²/2 on most Riemannian manifolds (fails on sphere in some configurations)
- Generic cost functions

## When Regularity Holds

### Caffarelli's Regularity Theory (quadratic cost in ℝⁿ)

**Theorem (Caffarelli):** For c = |x−y|²/2 in ℝⁿ, if:
1. Source and target densities f, g are C^{k,α} (Hölder continuous)
2. Both supp(µ) and supp(ν) are bounded convex domains

Then T ∈ C^{k+1,α} (one derivative better than the densities).

This is essentially the best possible result for the quadratic cost.

### Regular Cost Functions (Definition 12.14)
Cost c: X×Y → ℝ is **regular** if for any x and c-convex ψ:
```
∂ᶜψ(x) ∩ Dom*(∇ₓc(x,·)) is c-convex w.r.t. x
```

The MTW tensor `S(x,y)[ξ,η] = ∂²ₛₜ c(expₓ(sξ), expᵧ(tη))|_{s=t=0}` must
satisfy `S ≥ 0` (MTW condition). Regularity = MTW + connectedness.

## Practical Consequences for Hermes

### Critical Warning
**OT maps are NOT generically smooth.** Do NOT assume smoothness when:
- Distributions have non-convex support (e.g., manifold-valued embeddings)
- Using non-quadratic costs (e.g., hyperbolic distance cost)
- Working on Riemannian manifolds without verifying MTW

### When to Expect Smoothness
- Quadratic cost in ℝⁿ with both supports convex and densities smooth: YES
- Distance cost on the real line: YES (monotone rearrangement is smooth if densities smooth)
- Most other cases: NO or UNKNOWN

### Design Implications
1. **Gradient-based OT scoring:** Only valid when Caffarelli conditions hold
2. **Differentiable skill routing:** Needs convex support assumptions on embedding distributions
3. **Entropic regularization softens this:** Sinkhorn transport plans are always smooth (C∞) in the regularization parameter — use this instead

## Key Lemma (12.2)
If T is a continuous optimal map and π = (Id,T)#µ, then for each x ∈ supp(µ),
the pair (x, T(x)) is in the support of π. This is used in many regularity proofs.
