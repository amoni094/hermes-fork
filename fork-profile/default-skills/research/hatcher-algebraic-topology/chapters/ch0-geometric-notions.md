# Chapter 0: Some Underlying Geometric Notions

## Core Topics
- Homotopy and homotopy type
- CW complexes and cell structures
- Operations on spaces (join, cone, suspension, wedge sum, smash product)
- Homotopy equivalence criteria
- Homotopy extension property

## Homotopy

A **homotopy** is a continuous family of maps ft: X→Y, t∈[0,1], equivalently a
continuous map F: X×I→Y with F(x,t) = ft(x).

**Deformation retraction**: A homotopy ft: X→X with f₀=id, f₁(X)=A, ft|A=id.
The subspace A is a deformation retract of X. This implies X≃A.

**Homotopy equivalence**: f: X→Y is a homotopy equivalence if ∃g: Y→X with fg≃id, gf≃id.
We write X≃Y. This is an equivalence relation.

**Contractible**: X is contractible if X≃{point} (identity map is nullhomotopic).

## CW Complexes

Built inductively:
1. Start with discrete set X⁰ (0-cells = vertices)
2. Form X¹ by attaching 1-cells via maps S⁰→X⁰ (edges)
3. Form Xⁿ by attaching n-cells eⁿ via attaching maps φ: Sⁿ⁻¹→Xⁿ⁻¹

**Key facts**:
- X/Xⁿ⁻¹ ≅ ∨α Sⁿα (wedge of n-spheres, one per n-cell)
- If (X,A) is a CW pair with A contractible, X→X/A is homotopy equivalence
- Compact subsets meet only finitely many cells

## Space Operations

| Operation | Definition | Key property |
|-----------|------------|--------------|
| Cone CX | (X×I)/(X×{0}) | CX is contractible |
| Suspension SX | (X×I)/(X×{0} ∪ X×{1}) | π̃ₙ(SX) ≅ πₙ₋₁(X) (stably) |
| Join X∗Y | segments connecting X to Y | S^m ∗ S^n = S^{m+n+1} |
| Wedge X∨Y | one-point union | π₁(X∨Y) via van Kampen |
| Smash X∧Y | X×Y / X∨Y | S^m ∧ S^n = S^{m+n} |
| Mapping cylinder Mf | (X×I)⊔Y / (x,1)~f(x) | deformation retracts to Y |

## Homotopy Extension Property (HEP)

A pair (X,A) has the HEP if: for any map f: X→Y and homotopy of f|A,
the homotopy extends to all of X. CW pairs satisfy HEP.

## Key Examples

- Letters of alphabet: homotopy types determined by number of loops (holes)
  - A, B, D, O, P, Q, R have holes; others are contractible or tree-like
- Figure-8 (S¹∨S¹) has fundamental group ℤ∗ℤ
- Torus = S¹×S¹ as CW complex: 1 vertex, 2 edges, 1 face

## Euler Characteristic

For finite CW complex: χ(X) = Σₙ (-1)ⁿ cₙ where cₙ = #(n-cells)
- Invariant under homotopy equivalence (once homology is defined)
- S²: 1 vertex + 0 edges + 1 face → χ=2
- Torus: 1+2+1 cells → χ=0
- Graph with V vertices and E edges: χ = V - E
