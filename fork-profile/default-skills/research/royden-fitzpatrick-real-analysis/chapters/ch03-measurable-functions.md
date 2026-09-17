# Chapter 3: Lebesgue Measurable Functions

## Core Idea
Defines the class of measurable functions (pointwise limits of simple functions) and proves the two "Littlewood principles" connecting pointwise a.e. convergence to uniform convergence: Egorov's theorem and Lusin's theorem.

## Key Concepts
- **Measurable function**: f: E → ℝ̄ is measurable if {x ∈ E : f(x) > c} ∈ M for all c ∈ ℝ. Equivalently, preimage of every Borel set is measurable.
- **Simple function**: ψ = Σ aᵢ·1_{Eᵢ}, Eᵢ disjoint measurable, finitely many values. These are the atoms of integration.
- **Simple Approximation Theorem**: If f is measurable and bounded on E (finite measure), ∃ simple functions {ψₙ}, {φₙ} with ψₙ ≤ f ≤ φₙ and ‖φₙ - ψₙ‖_∞ < 1/n → 0. For nonneg measurable: ∃ simple ψₙ ↑ f pointwise.
- **Algebraic closure**: Measurable functions are closed under sums, products, compositions with Borel functions, pointwise limits, sup, inf, lim sup, lim inf.

## Frameworks Introduced

### Egorov's Theorem (Almost-Uniform Convergence)
**Statement**: Let m(E) < ∞. If {fₙ} → f a.e. on E, then ∀ε > 0 ∃ closed F ⊆ E with m(E\F) < ε such that fₙ → f **uniformly** on F.

- **When to use**: Upgrading a.e. pointwise convergence to uniform convergence on a large set
- **Hypothesis check**: m(E) < ∞ is essential — fails on ℝ (take fₙ = 1_{[n,n+1]})
- **How**: Choose Eₙₖ = {x : |fₙ(x) - f(x)| ≥ 1/k for some n ≥ N}. For each k, pick N large enough that m(Eₙₖ) < ε/2^k. Then F = E \ ∪ Eₙₖ has m(E\F) < ε and fₙ → f uniformly on F.

### Lusin's Theorem (Measurable ≈ Continuous on Large Set)
**Statement**: f measurable and finite a.e. on E (finite measure) iff ∀ε > 0 ∃ closed F ⊆ E with m(E\F) < ε such that f|_F is continuous.

- **When to use**: Approximating measurable functions by continuous ones
- **Hermes**: Routing functions that are measurable can be treated as continuous on the "stable" portion of skill space

## Worked Example — Egorov Applied
Let E = [0,1], fₙ(x) = xⁿ. Then fₙ → f pointwise where f = 0 on [0,1), f(1) = 1. So fₙ → f a.e. (null set {1}).

By Egorov: ∀ε > 0 ∃ closed F ⊆ [0,1) with m([0,1]\F) < ε and xⁿ → 0 uniformly on F. Indeed, take F = [0, (ε/2)^{1/n_0}]ᶜ∩[0,1] for appropriate n_0 — the set away from x=1.

**Hermes translation**: Skill routing that converges pointwise on individual contexts converges uniformly on the "F-fraction" of stable contexts. The ε-mass in E\F = the slow-converging edge cases.

## Key Takeaways
1. Measurability is preserved under all standard operations — you rarely lose measurability in practice.
2. Egorov: finite measure + a.e. convergence ⟹ nearly uniform convergence. The "nearly" (ε-set) is unavoidable.
3. Simple functions are the basic building block of integration — every measurable function is their limit.
4. Lusin's theorem makes precise the idea that measurable functions are "almost continuous."

## Connects To
- **Ch04**: Simple Approximation → integral defined via simple functions
- **Ch05**: Convergence in measure is another mode weaker than Egorov's uniform-on-F
