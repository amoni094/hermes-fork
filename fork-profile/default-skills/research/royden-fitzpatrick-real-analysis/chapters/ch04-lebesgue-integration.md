# Chapter 4: Lebesgue Integration

## Core Idea
Builds the Lebesgue integral for bounded, nonneg, then general measurable functions via simple function approximation. Proves the three principal limit theorems (MCT, Fatou, DCT) plus the Vitali Convergence Theorem as their culmination.

## Key Concepts
- **Integral of simple function**: ∫ψ dμ = Σ aᵢ m(Eᵢ) (finite, well-defined for finite-measure support)
- **Integral of bounded measurable f** on finite-measure E: sup{∫ψ : ψ ≤ f simple} = inf{∫φ : φ ≥ f simple}
- **Integral of nonneg measurable f**: ∫f = sup{∫h : 0 ≤ h ≤ f, h bounded, finite-measure support} ∈ [0,∞]
- **General integral**: ∫f = ∫f⁺ - ∫f⁻ when min(∫f⁺, ∫f⁻) < ∞. f is integrable (f ∈ L¹) iff ∫|f| < ∞.
- **Linearity and monotonicity**: ∫(αf+βg) = α∫f + β∫g; f ≤ g a.e. ⟹ ∫f ≤ ∫g
- **Countable additivity**: ∫_E f = Σ ∫_{Eₙ} f for disjoint partition {Eₙ} of E, f ≥ 0
- **Uniform integrability**: {fₙ} UI iff ∀ε>0 ∃M>0: sup_n ∫_{|fₙ|>M} |fₙ| < ε. Equivalently, tails of integrals vanish uniformly.

## The Four Convergence Theorems

### Monotone Convergence Theorem (MCT)
{fₙ} measurable, fₙ ↑ f pointwise a.e., fₙ ≥ 0 ⟹ ∫fₙ → ∫f.
- **Proof idea**: ∫f = sup ∫h (h bounded/simple) ≥ sup ∫fₙ ≥ lim inf ∫fₙ; reverse via fₙ ≤ f.
- **Use when**: Increasing approximations (natural for nonneg series, step functions)

### Fatou's Lemma
{fₙ} measurable, fₙ ≥ 0 ⟹ ∫(lim inf fₙ) ≤ lim inf ∫fₙ.
- **Proof**: Apply MCT to gₙ = inf_{k≥n} fₖ ↑ lim inf fₙ.
- **Use when**: You only have a lower bound / no dominator. Gives you a lower bound on the limiting integral.
- **Warning**: Strict inequality can occur (mass can escape to infinity).

### Dominated Convergence Theorem (DCT)
fₙ → f a.e., |fₙ| ≤ g, ∫g < ∞ ⟹ ∫|fₙ - f| → 0 and ∫fₙ → ∫f.
- **Proof**: Apply Fatou to g - fₙ and g + fₙ.
- **Use when**: Pointwise limit + integrable dominator. The dominator g is the key hypothesis to verify.
- **Hermes application**: If scoring function score_n(ctx) → score(ctx) pointwise and |score_n| ≤ g with ∫g < ∞, then E[score_n] → E[score]. Justifies "the average score of converging agent policies converges."

### Vitali Convergence Theorem
{fₙ} uniformly integrable (UI) and tight over E, fₙ → f a.e. ⟹ ∫fₙ → ∫f.
- **Uniform integrability replaces dominator**: UI is the generalization when no single dominator exists.
- **Tightness**: ∀ε>0 ∃ finite-measure E₀ s.t. sup_n ∫_{E\E₀} |fₙ| < ε. (Automatically satisfied when m(E)<∞.)
- **Use when**: Sequence bounded in L¹ but no explicit dominator; e.g., memory consolidation batches.

## Worked Example — DCT in Practice
Let fₙ(x) = n·1_{[0,1/n]}(x). Then fₙ → 0 a.e. and ∫fₙ = 1 ≠ 0 = ∫0. DCT fails because there's no integrable dominator (the sequence is dominated by g = 1/x which is not integrable on [0,1]).

Contrast: let fₙ(x) = sin(nx)/n on [0,π]. Then fₙ → 0 a.e., |fₙ| ≤ 1 (integrable on [0,π]). By DCT: ∫fₙ → 0. ✓

**Hermes pattern**: To apply DCT to an agent loop, find the dominator: is there a fixed budget B such that all intermediate scores are bounded by an integrable B?

## Key Takeaways
1. MCT is the engine; Fatou and DCT derive from it. Know all three hypotheses by heart.
2. DCT's dominator hypothesis is the real constraint in applications — must find a dominator, not just assume convergence.
3. Vitali Convergence generalizes DCT to the uniformly integrable case: the price of no dominator is proving uniform integrability.
4. Linearity + DCT together: ∫ Σfₖ = Σ ∫fₖ when the series is dominated.

## Connects To
- **Ch05**: Extends Vitali to infinite-measure domains (tightness condition)
- **Ch07**: Completeness of Lp uses rapidly Cauchy sequences + MCT-style arguments
- **Ch18**: Same theorems hold for abstract measure spaces
