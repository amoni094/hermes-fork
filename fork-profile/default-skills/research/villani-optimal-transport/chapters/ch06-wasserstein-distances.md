# Chapter 6: The Wasserstein Distances

**Book pages:** 93–112  
**Hermes relevance:** HIGH — Core metric for comparing distributions in Hermes.

## Key Definitions

### Wasserstein Distance of Order p (Definition 6.1)
For p ∈ [1,+∞) and (X,d) Polish metric space, µ,ν ∈ P(X):
```
Wₚ(µ,ν) = ( inf_{π∈Π(µ,ν)} ∫∫ d(x,y)ᵖ dπ(x,y) )^{1/p}
```

**Wasserstein Space Pₚ(X) (Definition 6.4):**
```
Pₚ(X) = { µ ∈ P(X) : ∫ d(x₀,x)ᵖ dµ < ∞ }
```
equipped with Wₚ — a complete separable metric space when (X,d) is.

### Topology (Theorem 6.9)
Wₚ(µₙ, µ) → 0 iff:
1. µₙ → µ weakly (in duality with bounded continuous functions)
2. ∫d(x₀,x)ᵖ dµₙ → ∫d(x₀,x)ᵖ dµ  (p-th moment convergence)

Equivalently: Wₚ convergence ⟺ weak convergence + tightness + moment convergence.

## Why Wasserstein Distances?

1. **Strong:** Sensitive to spatial displacements (unlike weak-* or total variation for diffuse measures)
2. **Dual:** Rich duality theory; W₁ = Kantorovich–Rubinstein via 1-Lipschitz functions
3. **Easy upper bounds:** Any coupling π gives an upper bound: Wₚ ≤ (∫∫d^p dπ)^{1/p}
4. **Pushforward Lipschitz:** If f: X→X' is C-Lipschitz, then f#: P₁(X)→P₁(X') is C-Lipschitz
5. **Geometric:** Incorporates metric structure of X — geodesics in X lift to geodesics in Pₚ

## Comparison with Other Distances

| Distance | Type | Comparison to Wₚ |
|----------|------|-------------------|
| Total variation | Strong | Incomparable (TV doesn't see geometry) |
| Bounded Lipschitz (Fortet–Mourier) | Weak | W₁ ≥ dbL |
| Weak-* | Very weak | Wₚ ≥ (all weak distances) |
| Toscani | Frequency domain | Used for PDEs |
| KL divergence | Information | Connected via Talagrand (Ch. 22) |

**Order relations:** Wₚ ≤ Wᵩ for p ≤ q (by Jensen), so W₁ is weakest.

## Geodesic Structure

(P₂(X), W₂) is a geodesic space when X is a geodesic space. The geodesics
are exactly the displacement interpolations (Chapter 7).

**Curvature:** (P₂(ℝⁿ), W₂) has non-negative Alexandrov curvature. The
space is "positively curved" in the sense that Wasserstein space is more
curved than Euclidean space.

## Practical Notes

- W₂ is the natural metric for displacement interpolation and gradient flows
- W₁ is easier to compute (linear program or dual 1-Lipschitz problem)
- For empirical distributions with N samples: W₁ converges at rate N^{−1/d} (slow in high d)
- Entropic regularization (Sinkhorn) approximates Wₚ efficiently — see Peyré–Cuturi

## Hermes Application

**Distribution comparison:** Use W₂ to compare skill embedding distributions
across routing decisions. Sensitive to both shape and location shifts.

**Metric space structure:** Since Pₚ(X) is a metric space, can apply any
algorithm that works on metric spaces (k-nearest neighbors, etc.) to
distributions by using Wₚ as the distance.

**Lipschitz propagation:** If skill scorer f: embeddings → ℝ is L-Lipschitz
in d, then the induced scorer on P₁ is also L-Lipschitz in W₁. Useful
for robustness analysis.
