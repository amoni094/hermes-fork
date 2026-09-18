# Chapter 2: Homology

## Core Topics
- Simplicial and singular homology (§2.1)
- Computations: degree, cellular homology, Mayer-Vietoris (§2.2)
- Formal viewpoint: axioms, functors (§2.3)
- Relationship to fundamental group (§2.A)

## 2.1 Simplicial and Singular Homology

### Delta (Δ) Complexes
Generalization of simplicial complexes allowing face identifications.
A Δ-complex on X: collection of maps σα: Δⁿ→X satisfying:
1. σα|_{interior of Δⁿ} is injective
2. Each restriction to a face is some σβ
3. A ⊂ X is open iff σα⁻¹(A) is open in Δⁿ for all σα

### Simplicial Homology
Chain groups: Δₙ(X) = free abelian group on n-simplices of X.
Boundary operator: ∂ₙ(σ) = Σᵢ (-1)ⁱ σ|_{[v₀,...,v̂ᵢ,...,vₙ]}

Key identity: ∂ₙ₋₁ ∘ ∂ₙ = 0 (boundary of boundary = 0)

**Homology groups**: Hₙ(X) = ker(∂ₙ) / im(∂ₙ₊₁) = Zₙ/Bₙ

### Singular Homology
Cₙ(X) = free abelian group on all continuous maps σ: Δⁿ→X.
Same boundary formula. More functorial but harder to compute directly.

**Homotopy invariance**: f≃g implies f∗=g∗ on homology. (Proved via chain homotopy.)
So homotopy equivalent spaces have isomorphic homology.

### Long Exact Sequence of a Pair (X,A)
0 → Cₙ(A) → Cₙ(X) → Cₙ(X,A) → 0 yields:
→ Hₙ(A) → Hₙ(X) → Hₙ(X,A) →^∂ Hₙ₋₁(A) → ...

**Excision theorem**: If Z̄⊂int(A), then Hₙ(X-Z, A-Z) ≅ Hₙ(X,A).
Equivalently: Hₙ(X,A) ≅ Hₙ(X/A, pt) when A is "nice" (NDR or CW subcomplex).

**Reduced homology**: H̃ₙ(X) = Hₙ(X) for n>0, H̃₀(X) = ker(Cₒ→ℤ)/Bₒ.
Long exact sequence of (X,A) uses reduced homology for good pairs.

## 2.2 Computations and Applications

### Degree
For a map f: Sⁿ→Sⁿ, f∗: Hₙ(Sⁿ)→Hₙ(Sⁿ) is multiplication by deg(f).
- Identity: degree 1
- Reflection: degree -1
- Antipodal map on Sⁿ: degree (-1)ⁿ⁺¹
- Composition: deg(fg) = deg(f)deg(g)

**Hairy ball theorem**: No continuous nonvanishing vector field on Sⁿ for even n.
(Antipodal map has degree (-1)ⁿ⁺¹; a vector field would give a homotopy id≃antipodal.)

### Cellular Homology
For CW complex X, cellular chain groups: Cₙ = Hₙ(Xⁿ, Xⁿ⁻¹) ≅ ℤ^{#n-cells}.

Cellular boundary map dₙ: Cₙ→Cₙ₋₁ given by:
dₙ(eⁿα) = Σβ dαβ eⁿ⁻¹β
where dαβ = degree of the composition Sⁿ⁻¹ →^{φα} Xⁿ⁻¹ →^{qβ} Sⁿ⁻¹.

**Theorem**: Cellular homology = singular homology.

### Mayer-Vietoris Sequence
If X = int(A) ∪ int(B):
→ Hₙ(A∩B) →^{(iA∗,iB∗)} Hₙ(A)⊕Hₙ(B) →^{jA∗-jB∗} Hₙ(X) →^∂ Hₙ₋₁(A∩B) →

**Standard computation**: Hₙ(Sⁿ) using X=Sⁿ, A=upper hemisphere, B=lower hemisphere, A∩B≃Sⁿ⁻¹.

### Homology with Coefficients
Hₙ(X; G) = Hₙ(C∗(X)⊗G).
- Universal Coefficient Theorem: 0 → Hₙ(X)⊗G → Hₙ(X;G) → Tor(Hₙ₋₁(X),G) → 0
- Hₙ(X;ℚ) = Hₙ(X;ℤ)⊗ℚ (rationals kill torsion)
- Hₙ(X;ℤ/2) is particularly useful for non-orientable spaces

## 2.3 The Formal Viewpoint

### Eilenberg-Steenrod Axioms for a Homology Theory
1. **Functoriality**: Maps f: X→Y induce f∗: Hₙ(X)→Hₙ(Y)
2. **Homotopy**: f≃g ⟹ f∗=g∗
3. **Exactness**: Long exact sequence for pairs
4. **Excision**: Hₙ(X-Z,A-Z) ≅ Hₙ(X,A) when Z̄⊂int(A)
5. **Dimension axiom**: Hₙ(pt) = 0 for n≠0, H₀(pt) = G

### Functors
Homology is a functor: Top→Ab. Naturality means diagrams commute.
Chain complexes and chain maps form a category; Hₙ is a functor on this.

## Key Homology Computations

| Space | H₀ | H₁ | H₂ | Hₙ (n>2) |
|-------|-----|-----|-----|----------|
| Sⁿ | ℤ | 0 | ... | ℤ (deg n), else 0 |
| T² | ℤ | ℤ² | ℤ | 0 |
| ℝP² | ℤ | ℤ/2 | 0 | 0 |
| ℝP³ | ℤ | ℤ/2 | 0 | ℤ (n=3) |
| Klein bottle K | ℤ | ℤ⊕ℤ/2 | 0 | 0 |
| Genus-g surface | ℤ | ℤ^{2g} | ℤ | 0 |
| ∨ⁿ S¹ | ℤ | ℤⁿ | 0 | 0 |

## Relationship: Homology and Fundamental Group

**Theorem**: H₁(X) ≅ π₁(X)^{ab} (the abelianization of π₁).

Consequence: H₁ is a computable algebraic shadow of π₁ that ignores
non-commutativity. For abelian π₁ (e.g. torus), H₁ = π₁ exactly.
