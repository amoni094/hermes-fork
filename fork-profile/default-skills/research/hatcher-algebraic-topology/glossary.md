# Glossary: Algebraic Topology (Hatcher)

## A

**Amalgamated free product**: G₁ ∗_H G₂ = (G₁ ∗ G₂) / ⟨i₁(h) = i₂(h) for h∈H⟩.
Appears in van Kampen's theorem.

**Attaching map**: The map φ: Sⁿ⁻¹ → Xⁿ⁻¹ used to attach an n-cell to a CW complex.

## B

**Betti number**: bₙ = rank(Hₙ(X;ℤ)) = dimension of Hₙ(X;ℚ). Free part of homology.

**Boundary map / operator**: ∂ₙ: Cₙ→Cₙ₋₁, satisfying ∂²=0. Geometric boundary of chains.

## C

**Cap product**: ⌢: Hᵖ(X;R) ⊗ Hₙ(X;R) → Hₙ₋ₚ(X;R). Used to state Poincaré duality.

**CW complex**: Space built by attaching cells inductively. The natural setting for algebraic topology.

**CW pair**: (X,A) where A is a subcomplex of CW complex X.

**Chain complex**: Sequence ...→Cₙ₊₁→Cₙ→Cₙ₋₁→... with consecutive maps composing to 0.

**Chain homotopy**: Maps sₙ: Cₙ→C'ₙ₊₁ with ∂s + s∂ = f - g. Implies f∗=g∗ on homology.

**Coboundary**: δ: Cⁿ→Cⁿ⁺¹, the dual of boundary. (δφ)(σ) = φ(∂σ).

**Cohomology ring**: H*(X;R) = ⊕Hⁿ(X;R) with cup product. Graded-commutative ring.

**Cone**: CX = (X×I)/(X×{0}). Contractible. Used in suspension SX = CX ∪_X CX.

**Contractible**: Space homotopy equivalent to a point. Identity map is nullhomotopic.

**Covering space**: p: X̃→X surjective with each point having an evenly covered neighborhood.

**Cup product**: ⌣: Hᵖ⊗Hq → Hᵖ⁺q. Defined via restriction of singular simplices to faces.

## D

**Deck transformation**: Automorphism φ: X̃→X̃ with p∘φ = p. Forms deck group.

**Deformation retract**: Subspace A of X is a deformation retract if ∃ homotopy ft: X→X
with f₀=id, f₁(X)=A, ft|A=id for all t.

**Degree**: For f: Sⁿ→Sⁿ, the integer d such that f∗ = multiplication by d on Hₙ(Sⁿ)≅ℤ.

**Δ-complex (Delta complex)**: Generalized simplicial complex allowing face identifications.

## E

**Eilenberg-MacLane space K(G,n)**: Space with πₙ=G and πₖ=0 for k≠n.
Classifying space for Hⁿ(-;G): [X, K(G,n)] ≅ Hⁿ(X;G).

**Euler characteristic**: χ(X) = Σₙ (-1)ⁿ cₙ = Σₙ (-1)ⁿ bₙ. Homotopy invariant.

**Exact sequence**: Sequence ... → Aₙ →^{fₙ} Aₙ₋₁ → ... with im(fₙ₊₁) = ker(fₙ).

**Excision**: Hₙ(X−Z, A−Z) ≅ Hₙ(X, A) when Z̄⊂int(A). Makes pairs behave like quotients.

**Ext**: Ext¹(A, B) = derived functor of Hom. Appears in UCT. Ext(ℤ/n, ℤ) = ℤ/n.

## F

**Fibration**: Map p: E→B with homotopy lifting property. Long exact sequence in homotopy.

**Fiber bundle**: Locally trivial fibration p: E→B with fiber F. p⁻¹(b) ≅ F for all b.

**Free abelian group**: Direct sum of copies of ℤ. Chain groups are free abelian.

**Free group**: Group with a set of generators and no relations. Fₙ = π₁(∨ⁿ S¹).

**Free product**: G₁∗G₂ = group of alternating words from G₁, G₂. Identity element only.

**Fundamental class [M]**: Generator of Hₙ(M;ℤ)≅ℤ for closed orientable n-manifold M.

**Fundamental group**: π₁(X,x₀) = homotopy classes of loops at x₀. First homotopy group.

## G

**Good pair**: (X,A) where inclusion A↪X is a cofibration / homotopy extension pair.
For good pairs: H̃ₙ(X/A) ≅ Hₙ(X,A).

## H

**Homology group Hₙ(X)**: ker(∂ₙ)/im(∂ₙ₊₁). Measures n-dimensional "holes" in X.

**Homotopy**: A continuous family of maps ft: X→Y, t∈[0,1].

**Homotopy equivalence**: f: X→Y with homotopy inverse g: Y→X (fg≃id, gf≃id).

**Homotopy extension property**: See HEP. Pair (X,A) satisfies HEP if homotopies of maps
from A extend to maps from X.

**Homotopy groups πₙ**: πₙ(X,x₀) = [(Sⁿ,*),(X,x₀)]. Groups for n≥1, abelian for n≥2.

**Homotopy type**: Equivalence class under homotopy equivalence.

**Hopf fibration**: S¹→S³→S² (unit complex numbers acting on S³⊂ℂ²). Generates π₃(S²)=ℤ.

**Hurewicz map**: h: πₙ(X)→Hₙ(X), [f]↦f∗([Sⁿ]). Isomorphism when X is (n-1)-connected.

## J

**Join**: X∗Y = formal line segments between X and Y. S^m ∗ S^n = S^{m+n+1}.

## K

**Künneth formula**: H*(X×Y;F) ≅ H*(X;F) ⊗_F H*(Y;F) over a field F.

## L

**Lifting**: f̃: Y→X̃ with p∘f̃ = f: Y→X. Exists iff f∗(π₁(Y)) ⊂ p∗(π₁(X̃)).

**Long exact sequence (LES)**: Exact sequence →Hₙ(A)→Hₙ(X)→Hₙ(X,A)→Hₙ₋₁(A)→ for pairs.

## M

**Mapping cone**: Cf = X ∪_f CY for f: Y→X. Fits into cofiber sequence Y→X→Cf.

**Mapping cylinder**: Mf = (Y×I) ∪_f X. Deformation retracts to X. The "graph" of f.

**Mayer-Vietoris sequence**: LES for X=A∪B open: →Hₙ(A∩B)→Hₙ(A)⊕Hₙ(B)→Hₙ(X)→

## N

**n-cell**: Open n-disk eⁿ ≅ int(Dⁿ). Attached to CW complex via attaching map.

**Nullhomotopic**: Map homotopic to a constant map. π₁ detects non-nullhomotopic loops.

## O

**Orientation**: Consistent choice of generator for Hₙ(Dⁿ, Sⁿ⁻¹) across all n-cells.

## P

**Path-connected**: Any two points are connected by a path. π₀=0.

**Poincaré duality**: Hₖ(M) ≅ Hⁿ⁻ᵏ(M) for closed orientable n-manifold.

**Postnikov tower**: Decomposition of X into stages Pₙ(X) truncated at πₙ.

## R

**Reduced homology H̃ₙ**: H̃₀(X) removes one ℤ (for connected X: H̃₀=0). H̃ₙ=Hₙ for n>0.

**Relative homology Hₙ(X,A)**: Homology of chain complex Cₙ(X)/Cₙ(A). Measures X relative to A.

**Retraction**: Map r: X→A with r|_A = id_A. A need not be a deformation retract.

## S

**Simply connected**: π₁ = 0. Loops are contractible.

**Simplicial complex**: Collection of simplices closed under taking faces, with simplices
uniquely determined by their vertex sets.

**Singular chain**: Formal sum Σnᵢσᵢ of singular simplices σᵢ: Δⁿ→X.

**Skeleton Xⁿ**: The union of all cells of dimension ≤n in a CW complex.

**Smash product**: X∧Y = X×Y / X∨Y. S^m ∧ S^n = S^{m+n}.

**Suspension**: SX = X×I / (X×{0} ∪ X×{1}) ≅ ΣX. SX = CX ∪_X CX.

## T

**Tor**: Tor(A,B) = first left derived functor of tensor product. Tor(ℤ/n, ℤ/m) = ℤ/gcd(n,m).

## U

**UCT (Universal Coefficient Theorem)**: 0 → Ext(Hₙ₋₁(X),G) → Hⁿ(X;G) → Hom(Hₙ(X),G) → 0.

**Universal cover**: Simply-connected covering space X̃→X. Corresponds to trivial subgroup.

## V

**Van Kampen's theorem**: π₁(A∪B) = π₁(A) ∗_{π₁(A∩B)} π₁(B) for open path-connected A,B,A∩B.

## W

**Weak homotopy equivalence**: f: X→Y inducing πₙ isomorphisms for all n.
Equals homotopy equivalence for CW complexes (Whitehead's theorem).

**Wedge sum**: X∨Y = one-point union. π₁(X∨Y) = π₁(X)∗π₁(Y) when X,Y simply connected.

**Whitehead's theorem**: Weak homotopy equivalence between CW complexes is a homotopy equivalence.
