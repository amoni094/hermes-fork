# Cheatsheet: Algebraic Topology (Hatcher)

## Quick Reference — Key Spaces

| Space | π₁ | H₁ | H₂ | χ |
|-------|-----|-----|-----|---|
| Point | 0 | 0 | 0 | 1 |
| S¹ | ℤ | ℤ | 0 | 0 |
| S² | 0 | 0 | ℤ | 2 |
| Sⁿ (n≥2) | 0 | 0 | ...ℤ at n | 1+(−1)ⁿ |
| T² (torus) | ℤ² | ℤ² | ℤ | 0 |
| ℝP² | ℤ/2 | ℤ/2 | 0 | 1 |
| ℝP³ | ℤ/2 | ℤ/2 | 0 | 0 |
| Klein bottle | ℤ⋊ℤ | ℤ⊕ℤ/2 | 0 | 0 |
| Genus-g surface Σg | π₁(Σg) | ℤ²g | ℤ | 2-2g |
| S¹∨S¹ | ℤ∗ℤ | ℤ² | 0 | -1 |
| Graph: V vertices, E edges, C components | Free(E-V+C) | ℤ^{E-V+C} | 0 | V-E |

## Boundary Formula

∂[v₀,v₁,...,vₙ] = Σᵢ (−1)ⁱ [v₀,...,v̂ᵢ,...,vₙ]

Examples:
- ∂[v₀,v₁] = [v₁] − [v₀]
- ∂[v₀,v₁,v₂] = [v₁,v₂] − [v₀,v₂] + [v₀,v₁]

## Euler-Poincaré Formula
χ(X) = Σₙ (−1)ⁿ cₙ  =  Σₙ (−1)ⁿ bₙ
where cₙ = #n-cells, bₙ = rank Hₙ.

## Long Exact Sequences

**Pair (X,A)**:
→ Hₙ(A) →^i∗ Hₙ(X) →^j∗ Hₙ(X,A) →^∂ Hₙ₋₁(A) →

**Mayer-Vietoris** (X = int(A)∪int(B)):
→ Hₙ(A∩B) →^{(i∗,j∗)} Hₙ(A)⊕Hₙ(B) →^{k∗−l∗} Hₙ(X) →^∂ Hₙ₋₁(A∩B) →

**Fibration** F→E→B:
→ πₙ(F) → πₙ(E) → πₙ(B) →^∂ πₙ₋₁(F) →

## Van Kampen's Theorem
X = A∪B (A,B,A∩B open, path-connected):
π₁(X) = π₁(A) ∗_{π₁(A∩B)} π₁(B)

Special cases:
- A∩B simply connected: π₁(X) = π₁(A) ∗ π₁(B)
- Attaching 2-cell along α: kills [α] in π₁

## Covering Space Dictionary

| Covering X̃→X | Subgroup H ⊂ π₁(X) |
|--------------|---------------------|
| Universal cover | {1} |
| X itself | π₁(X) |
| Normal covering | H normal in π₁ |
| Degree n covering | [π₁:H] = n |
| Deck group | N(H)/H |
| Galois cover | π₁(X)/H |

## Universal Coefficient Theorem
0 → Ext(Hₙ₋₁(X), G) → Hⁿ(X;G) → Hom(Hₙ(X), G) → 0    (splits)

Key: Ext(ℤ/n, ℤ) = ℤ/n,  Ext(ℤ, G) = 0

## Hurewicz Theorem
If X path-connected and πₖ(X)=0 for k<n (n≥2):
Hₖ(X) = 0 for 0 < k < n
Hₙ(X) ≅ πₙ(X)

## Degree Formula
For f: Sⁿ→Sⁿ piecewise linear:  deg(f) = Σ_{p∈f⁻¹(q)} sign(det df_p)

Key degrees:
- Identity: +1
- Reflection: −1
- Antipodal (Sⁿ): (−1)ⁿ⁺¹
- Constant: 0

## Poincaré Duality
Closed orientable n-manifold M with fundamental class [M]:
Hₖ(M;ℤ) ≅ Hⁿ⁻ᵏ(M;ℤ)    (via cap product ⌢[M])

Betti numbers: bₖ = bₙ₋ₖ. If n odd: χ(M) = 0.

## Computational Pipeline

### Given: CW complex X with n-cells
1. List n-cells by dimension
2. Build cellular chain complex Cₙ = ℤ^{#n-cells}
3. Compute boundary matrices ∂ₙ (entries = degrees)
4. Compute Hₙ = ker(∂ₙ)/im(∂ₙ₊₁) via Smith normal form

### Given: X = A∪B
1. Compute H∗(A), H∗(B), H∗(A∩B) separately
2. Write Mayer-Vietoris LES
3. Use rank-nullity to fill in unknowns

### Given: fibration F→E→B
1. Compute π∗(B), π∗(F)
2. Write long exact sequence
3. Use algebra to determine π∗(E)

## Hermes Skill Graph Formulas

**Graph homology** (skill graph G = (V,E,C components)):
- H₀ rank = C  (number of isolated skill clusters)
- H₁ rank = E − V + C  (number of independent skill dependency cycles)
- χ = V − E  (structural balance)

**Homotopy equivalence criterion** (skills s₁, s₂):
- s₁ ≃ s₂ iff ∃ skill maps f: s₁→s₂, g: s₂→s₁ with fg≃id, gf≃id
- Approximate: Jaccard(triggers) > 0.8 AND Jaccard(tools) > 0.8

**Van Kampen for skill categories**:
If skills = devops∪research with bridging skills in intersection:
π₁(all) = π₁(devops) ∗_{π₁(bridge)} π₁(research)
→ cycles in bridge skills create amalgamation constraints
