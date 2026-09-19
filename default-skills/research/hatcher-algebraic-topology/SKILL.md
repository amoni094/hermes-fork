---
name: hatcher-algebraic-topology
description: >
  Knowledge base from Algebraic Topology by Hatcher. Use when applying
  fundamental groups, covering spaces, homology, cohomology, homotopy theory,
  CW complexes to topological reasoning about agent state spaces and skill
  relationship graphs.
tags: [algebraic-topology, homology, homotopy, fundamental-group, covering-spaces, CW-complexes, cohomology, research, mathematics]
related_skills: [milewski-category-theory, kreyszig-functional-analysis, clrs-algorithms]
source:
  title: "Algebraic Topology"
  author: "Allen Hatcher"
  pages: 560
  url: "https://pi.math.cornell.edu/~hatcher/AT/AT.pdf"
  type: textbook
book_type: technical
depth: study
---

# Hatcher — Algebraic Topology


## Model Routing

Dense abstract math reference lookup (no tool calls): deepseek-v4-pro non-think session. Graph-invariant analysis or implementation: grok-4.6 workers via delegate_task.


## Overview

Algebraic topology assigns algebraic invariants (groups, rings) to topological
spaces to distinguish them up to homotopy. The text is organized into four
main chapters plus preliminaries:

- **Chapter 0** — Geometric Notions (homotopy type, CW complexes, operations on spaces)
- **Chapter 1** — Fundamental Group (π₁, van Kampen, covering spaces)
- **Chapter 2** — Homology (simplicial/singular, cellular, Mayer-Vietoris)
- **Chapter 3** — Cohomology (UCT, cup product, Poincaré duality)
- **Chapter 4** — Homotopy Theory (πₙ, Hurewicz, fibrations, Postnikov towers)

## Core Concepts

### Homotopy and Homotopy Equivalence
Two maps f₀, f₁: X→Y are **homotopic** (f₀ ≃ f₁) if there exists a continuous
family ft: X→Y, t∈[0,1]. Spaces X and Y are **homotopy equivalent** (X ≃ Y)
if ∃ f: X→Y and g: Y→X with fg ≃ id and gf ≃ id. Homotopy equivalence is the
coarse equivalence of algebraic topology — coarser than homeomorphism, finer
than having the same homology.

**Key tool**: Mapping cylinder Mf deformation retracts onto Y; if (X,A) is a
CW pair with A contractible, X→X/A is a homotopy equivalence.

### CW Complexes
A CW complex is built inductively by attaching n-cells eⁿ (open n-disks) via
attaching maps Sⁿ⁻¹→Xⁿ⁻¹. The skeleton Xⁿ consists of all cells of dimension
≤n. CW complexes are the natural domain for algebraic topology.

**Euler characteristic**: χ(X) = Σ (-1)ⁿ cₙ where cₙ = number of n-cells.
This equals Σ (-1)ⁿ rank(Hₙ(X)) by the Euler-Poincaré formula.

### Fundamental Group π₁(X, x₀)
The **fundamental group** π₁(X, x₀) = homotopy classes of loops at basepoint x₀,
with concatenation as product. Key facts:
- π₁(S¹) ≅ ℤ (winding number)
- π₁(Sⁿ) = 0 for n ≥ 2
- π₁(S¹ ∨ S¹) = ℤ ∗ ℤ (free group on 2 generators)
- A map f: X→Y induces a homomorphism f∗: π₁(X)→π₁(Y)

**Van Kampen's theorem**: If X = A∪B with A, B, A∩B path-connected and open,
then π₁(X) = π₁(A) ∗_{π₁(A∩B)} π₁(B) (amalgamated free product).

### Covering Spaces
A **covering space** p: X̃→X is a surjective map where each point x has an
evenly covered neighborhood U with p⁻¹(U) a disjoint union of sheets.

**Classification** (Galois correspondence): Connected covering spaces of X
(up to isomorphism) ↔ conjugacy classes of subgroups of π₁(X, x₀).

- Universal cover X̃ (simply connected) corresponds to trivial subgroup
- Normal covers correspond to normal subgroups; deck group ≅ G/H
- The fiber p⁻¹(x₀) is acted on by π₁(X, x₀) transitively

**Lifting criterion**: A map f: Y→X lifts to f̃: Y→X̃ iff f∗(π₁(Y)) ⊂ p∗(π₁(X̃)).

### Homology Groups Hₙ(X)
**Simplicial homology**: Chain complex of free abelian groups Cₙ with boundary
maps ∂ₙ: Cₙ→Cₙ₋₁ satisfying ∂²=0.
- n-cycles Zₙ = ker(∂ₙ)
- n-boundaries Bₙ = im(∂ₙ₊₁)
- Hₙ(X) = Zₙ/Bₙ (measures n-dimensional "holes")

**Key computations**:
- Hₙ(Sⁿ) = ℤ, Hₖ(Sⁿ) = 0 for k≠0,n
- H₀(X) = ℤ^(# components)
- H₁(X) = π₁(X)^{ab} (abelianization of fundamental group)
- Hₙ(Tⁿ) = ℤ^C(n,k) in degree k (binomial coefficients)

**Exact sequences**: Short exact sequences of chain complexes give long exact
sequences in homology. Excision: Hₙ(X,A) ≅ Hₙ(X/A) when A is "nice".

**Mayer-Vietoris**: If X = A∪B (open),
→Hₙ(A∩B)→Hₙ(A)⊕Hₙ(B)→Hₙ(X)→Hₙ₋₁(A∩B)→

**Cellular homology**: For CW complex X, Hₙ(X) computed from cellular chain
complex where Cₙ = ℤ^{#n-cells}, ∂ₙ given by degrees of attaching maps.

### Cohomology Hⁿ(X; G)
Cohomology is the dual of homology. Key features not present in homology:
- **Cup product**: ⌣: Hᵖ(X;R) ⊗ Hq(X;R) → Hᵖ⁺ᵍ(X;R), making H*(X;R) a ring
- **Universal Coefficient Theorem**: Hⁿ(X;G) ≅ Hom(Hₙ(X),G) ⊕ Ext(Hₙ₋₁(X),G)
- **Poincaré Duality**: For closed orientable n-manifold: Hₖ(M) ≅ Hⁿ⁻ᵏ(M)
- Künneth formula: H*(X×Y) ≅ H*(X) ⊗ H*(Y) (over field)

### Higher Homotopy Groups πₙ(X)
πₙ(X, x₀) = homotopy classes of maps Sⁿ→X. For n≥2, πₙ is abelian.
- **Whitehead's theorem**: If f: X→Y is a map between CW complexes inducing
  isomorphisms on all πₙ, then f is a homotopy equivalence
- **Hurewicz theorem**: If πₖ(X)=0 for k<n, then Hₖ(X)=0 for 0<k<n and
  Hₙ(X) ≅ πₙ(X) (abelianization when n=1)
- **Fibrations**: p: E→B is a fibration if it has the homotopy lifting property.
  Long exact sequence: →πₙ(F)→πₙ(E)→πₙ(B)→πₙ₋₁(F)→

## Key Theorems for Applications

| Theorem | Statement | Application |
|---------|-----------|-------------|
| Van Kampen | π₁(A∪B) = π₁(A)∗_{π₁(A∩B)}π₁(B) | Graph decomposition |
| Galois correspondence | Covers ↔ subgroups of π₁ | Dependency hierarchy |
| Hurewicz | πₙ=Hₙ when lower groups vanish | Compute homotopy via homology |
| Euler-Poincaré | χ = Σ(-1)ⁿrank(Hₙ) | Structural audit of graphs |
| Mayer-Vietoris | LES for X=A∪B | Decompose/compute homology |
| UCT | Hⁿ ≅ Hom(Hₙ,G) ⊕ Ext(Hₙ₋₁,G) | Cohomology from homology |
| Poincaré duality | Hₖ ≅ Hⁿ⁻ᵏ (manifolds) | Symmetry in skill dimensions |
| Whitehead | π∗ isos → homotopy equiv | Skill deduplication criterion |

## Hermes Application Framework

### Skill Graph as Simplicial Complex
Model the Hermes skill graph as a simplicial complex K where:
- 0-simplices = individual skills
- 1-simplices = direct dependencies/related_skills edges
- 2-simplices = triangles of mutually related skills (skill clusters)

Then H₀(K) counts connected components, H₁(K) detects "holes" (missing
bridging skills between clusters), H₂(K) detects voids in coverage.

### Homotopy Equivalence for Skill Deduplication
Two skills S₁, S₂ are **homotopy equivalent** (functionally redundant) if:
- There exist skill maps f: S₁→S₂ and g: S₂→S₁ (one calls the other)
- fg ≃ id and gf ≃ id (returning same results up to reformulation)

In practice: check if two skills have identical trigger conditions, same tool
calls, and outputs that compose to identity transformations.

### Euler Characteristic for Graph Audit
For the skill graph as CW complex:
χ = V - E + F (vertices=skills, edges=dependencies, faces=3-cliques)
- χ > 0: fewer holes than connections (under-connected, siloed skills)
- χ < 0: more loops than trees (over-connected, possible cycles)
- χ = 0: "balanced" topology (like torus — well-connected clusters)

### Covering Spaces for Dependency Analysis
The skill dependency graph admits covering space interpretation:
- Universal cover = full dependency tree (no cycles, complete unrolling)
- Deck transformations = symmetries in skill reuse patterns
- Fundamental group of dependency graph = independent cycle generators

### Fundamental Group of Skill Graph
π₁(K, s₀) for skill graph K detects dependency cycles. A nontrivial element
is a loop of skill calls returning to the starting skill — potential infinite
loops or circular dependencies.

## Study Notes

### Key Computational Techniques
1. **Mayer-Vietoris**: Split space X=A∪B, compute H*(A), H*(B), H*(A∩B), use LES
2. **Cellular homology**: Count n-cells, compute boundary maps via degree
3. **Van Kampen**: Split X=A∪B, identify π₁(A∩B)→π₁(A), π₁(A∩B)→π₁(B)
4. **Covering spaces**: π₁(X)/H acts as deck group for covering with H⊂π₁(X)

### Pitfalls
- ∂² = 0 must be verified for any chain complex (boundary of boundary = 0)
- Signs matter in boundary formula: ∂[v₀,...,vₙ] = Σ(-1)ⁱ[v₀,...,v̂ᵢ,...,vₙ]
- Reduced homology H̃₀: removes one ℤ from H₀ (set to 0 for connected space)
- Long exact sequences require careful tracking of connecting homomorphisms
- Poincaré duality requires orientability; Klein bottle requires ℤ/2 coefficients

### Notation
- Hₙ(X) = nth singular/simplicial homology group
- Hⁿ(X;G) = nth cohomology with coefficients in G
- πₙ(X) = nth homotopy group
- X ≃ Y = homotopy equivalent
- p: X̃→X = covering map
- ∂ = boundary operator
- ⌣ = cup product
- χ(X) = Euler characteristic

## References to Chapters
- [ch0-geometric-notions](chapters/ch0-geometric-notions.md)
- [ch1-fundamental-group](chapters/ch1-fundamental-group.md)
- [ch2-homology](chapters/ch2-homology.md)
- [ch3-cohomology](chapters/ch3-cohomology.md)
- [ch4-homotopy-theory](chapters/ch4-homotopy-theory.md)
- [glossary](glossary.md)
- [patterns](patterns.md)
- [cheatsheet](cheatsheet.md)
