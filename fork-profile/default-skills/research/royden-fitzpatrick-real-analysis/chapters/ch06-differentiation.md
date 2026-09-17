# Chapter 6: Differentiation and Integration

## Core Idea
Investigates when differentiation and integration are inverse operations. The Fundamental Theorem of Calculus for the Lebesgue integral: f = g' a.e. iff g is absolutely continuous, with g(x) = g(a) + ∫ₐˣ f.

## Key Concepts
- **Monotone function**: Differentiable a.e. (Lebesgue's theorem). Derivative is measurable and nonneg.
- **Functions of Bounded Variation (BV)**: TV[f] = sup_P Σ|f(xₖ)-f(xₖ₋₁)| < ∞. BV = (increasing) − (increasing) by Jordan's theorem. BV functions are differentiable a.e.
- **Absolutely Continuous (AC)**: f: [a,b]→ℝ is AC iff ∀ε>0 ∃δ>0: for any finite collection of disjoint intervals {(aₖ,bₖ)}, Σ(bₖ-aₖ) < δ ⟹ Σ|f(bₖ)-f(aₖ)| < ε.
- **AC ⊂ BV**: Every absolutely continuous function has bounded variation.
- **FTC for Lebesgue integral**: f integrable on [a,b] ⟹ g(x) = ∫ₐˣ f(t)dt is AC and g'=f a.e. Conversely, g AC ⟹ g'∈L¹ and g(x)-g(a) = ∫ₐˣ g'.
- **Convex functions**: f convex on (a,b) ⟹ f has left and right derivatives everywhere, f' exists a.e., f' is increasing. Jensen's inequality: f(∫ϕ dμ) ≤ ∫f∘ϕ dμ for probability measure μ.
- **Lebesgue decomposition**: Any BV function f = AC part + singular part (f'=0 a.e. but not constant, like Cantor-Lebesgue function).

## Key Takeaways
1. Absolute continuity is the exact condition for FTC: g(x) = ∫ₐˣ g' with no "singular" leftover.
2. BV but not AC: can have derivative zero a.e. yet be non-constant (Cantor-Lebesgue function is the canonical example).
3. Jensen's inequality for convex f: expectation under the curve is below the curve. Critical for proving Hölder, Young, information-theoretic inequalities.
4. In Hermes context: if memory score function is AC, it can be recovered from its derivative (rate of change) by integration.

## Connects To
- **Ch07**: Jensen's inequality used to prove Hölder; convexity is central to Lp theory
- **Ch18**: Radon-Nikodym generalizes the FTC to abstract measures: dν = f dμ when ν ≪ μ
