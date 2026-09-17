# Chapter 3: Cohomology

## Core Topics
- Cohomology groups and UCT (§3.1)
- Cup product and cohomology ring (§3.2)
- Poincaré duality (§3.3)

## 3.1 Cohomology Groups

### Definition
Cⁿ(X; G) = Hom(Cₙ(X), G) = group of n-cochains.
Coboundary: δⁿ: Cⁿ→Cⁿ⁺¹ given by (δφ)(σ) = φ(∂σ).
δ²=0, so:

**Cohomology**: Hⁿ(X; G) = ker(δⁿ) / im(δⁿ⁻¹)

### Universal Coefficient Theorem (UCT)
```
0 → Ext¹(Hₙ₋₁(X), G) → Hⁿ(X; G) → Hom(Hₙ(X), G) → 0
```
This sequence splits (but not naturally). Key cases:
- G = ℤ: Hⁿ(X;ℤ) ≅ Free(Hₙ(X)) ⊕ Torsion(Hₙ₋₁(X))
- G = field F: Hⁿ(X;F) ≅ Hom(Hₙ(X;F), F) (vector space dual)

### Cohomology vs Homology
Cohomology carries more structure (ring structure via cup product).
Over a field, cohomology and homology are dual vector spaces.
Torsion elements appear in *different* degrees in homology vs cohomology.

## 3.2 Cup Product

### Definition
For cochains φ∈Cᵖ(X;R) and ψ∈Cq(X;R):
(φ⌣ψ)(σ) = φ(σ|_{[v₀,...,vₚ]}) · ψ(σ|_{[vₚ,...,vₚ₊q]})

This induces the **cup product**: ⌣: Hᵖ(X;R) ⊗ Hq(X;R) → Hᵖ⁺q(X;R)

**Cohomology ring**: H*(X;R) = ⊕ₙ Hⁿ(X;R) with cup product, graded-commutative:
α⌣β = (-1)^{pq} β⌣α for α∈Hᵖ, β∈Hq.

### Künneth Formula
Over a field F: H*(X×Y;F) ≅ H*(X;F) ⊗F H*(Y;F)
As rings, with (α⊗β)⌣(α'⊗β') = (-1)^{|β||α'|} (α⌣α')⊗(β⌣β').

### Key Cohomology Rings

| Space | H*(X;ℤ) as ring |
|-------|----------------|
| Sⁿ | ℤ[α]/(α²) with |α|=n |
| Tⁿ | exterior algebra Λ(x₁,...,xₙ), |xᵢ|=1 |
| ℂPⁿ | ℤ[α]/(αⁿ⁺¹) with |α|=2 |
| ℝPⁿ (mod 2) | ℤ/2[α]/(αⁿ⁺¹) with |α|=1 |

**Application**: Cup product distinguishes spaces with same homology.
E.g., T² and S¹∨S¹∨S² have same homology but different cup product structure.

## 3.3 Poincaré Duality

### Orientability
A closed n-manifold M is **orientable** if H_n(M;ℤ) ≅ ℤ.
This class [M]∈Hₙ(M;ℤ) is the **fundamental class**.

### Poincaré Duality Theorem
For a closed, connected, orientable n-manifold M:
**Hₖ(M;ℤ) ≅ Hⁿ⁻ᵏ(M;ℤ)**

More precisely: cap product with [M] gives an isomorphism ∩[M]: Hⁿ⁻ᵏ(M)→Hₖ(M).

**Cap product**: ⌢: Hⁿ(X;R) ⊗ Hₘ(X;R) → Hₘ₋ₙ(X;R)
Related to cup by: ⟨α⌣β, σ⟩ = ⟨α, β⌢σ⟩.

### Consequences of Poincaré Duality
- For closed orientable n-manifold: χ(M) = 0 if n is odd
- Betti numbers satisfy bₖ = bₙ₋ₖ (symmetric)
- For simply connected closed 4-manifold: H₂ determines the topology (with intersection form)

### Other Duality Theorems
- **Alexander duality**: H̃ₙ(Sⁿ⁺¹−K) ≅ H̃ⁿ⁻ᵢ₋₁(K) for nice K⊂Sⁿ⁺¹
- **Lefschetz duality**: Hₖ(M,∂M) ≅ Hⁿ⁻ᵏ(M) for compact manifold with boundary

## Computational Techniques

### Computing Cohomology from Homology
1. Compute Hₙ(X;ℤ) first (simpler)
2. Apply UCT: Hⁿ(X;ℤ) = Free(Hₙ) ⊕ Tor(Hₙ₋₁)
3. Identify generators and relations of ring structure via cup product

### Using Poincaré Duality
For closed orientable manifold M of dimension n:
- bₙ = b₀ = 1 (connected)
- bₙ₋₁ = b₁ (duality)
- χ(M) = Σ(-1)ᵏbₖ, and b₂ₖ₊₁ cancel in pairs when n odd
