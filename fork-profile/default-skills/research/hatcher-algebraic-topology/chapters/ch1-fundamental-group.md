# Chapter 1: The Fundamental Group

## Core Topics
- Paths and homotopy classes (§1.1)
- van Kampen's theorem (§1.2)
- Covering spaces (§1.3)
- Graphs and free groups (§1.A)
- K(G,1) spaces (§1.B)

## 1.1 The Fundamental Group

**Paths**: A path in X is a continuous map γ: [0,1]→X. Concatenation: (γ·η)(t).
Paths are homotopic rel endpoints if there is a homotopy fixing γ(0) and γ(1).

**π₁(X, x₀)**: Homotopy classes of loops (paths with γ(0)=γ(1)=x₀) under concatenation.
This is a group with:
- Identity = constant loop at x₀
- Inverse = reverse traversal γ̄(t) = γ(1-t)

**Key computation** — π₁(S¹) = ℤ:
Proved via covering space p: ℝ→S¹, p(t)=e^{2πit}. Lifts of loops track winding number.

**Induced homomorphisms**: f: (X,x₀)→(Y,y₀) induces f∗: π₁(X,x₀)→π₁(Y,y₀).
Functorial: (fg)∗ = f∗g∗, id∗ = id. Homotopy equivalences induce isomorphisms.

**Simply connected**: X is simply connected if π₁(X)=0 (and path-connected).
Examples: ℝⁿ, Sⁿ (n≥2), trees, contractible spaces.

## 1.2 Van Kampen's Theorem

**Setup**: X = A∪B, A,B,A∩B open and path-connected, basepoint x₀∈A∩B.

**Theorem** (van Kampen):
π₁(X, x₀) ≅ π₁(A, x₀) ∗_{π₁(A∩B, x₀)} π₁(B, x₀)

This is the amalgamated free product: quotient of π₁(A)∗π₁(B) by relations
iA∗(γ) = iB∗(γ) for all γ∈π₁(A∩B), where iA, iB are inclusions.

**Special cases**:
- A∩B simply connected: π₁(X) = π₁(A) ∗ π₁(B) (free product)
- A simply connected: π₁(X) = π₁(B) / N(iB∗(π₁(A∩B)))

**Applications**:
- π₁(S¹∨S¹) = ℤ∗ℤ (free group on 2 generators)
- π₁(Torus) = ℤ×ℤ (A∩B simply connected, π₁(A)=π₁(B)=ℤ, then relator aba⁻¹b⁻¹)
- Attaching a 2-cell along α kills [α] in π₁

**Surface groups**: π₁(genus-g surface) = ⟨a₁,b₁,...,aₘ,bₘ | [a₁,b₁]···[aₘ,bₘ]⟩

## 1.3 Covering Spaces

**Definition**: p: X̃→X is a covering space if each x∈X has a neighborhood U
with p⁻¹(U) = ∐α Ṽα and p|_{Ṽα}: Ṽα→U a homeomorphism.

**Lifting properties**:
- **Path lifting**: Any path γ in X lifts uniquely to X̃ given initial lift
- **Homotopy lifting**: Path homotopies lift uniquely
- **Lifting criterion**: f: Y→X lifts to X̃ iff f∗(π₁(Y)) ⊂ p∗(π₁(X̃))

**Classification theorem** (Galois correspondence):
For "nice" X (path-connected, locally path-connected, semilocally simply-connected):
{connected covering spaces of X} / isomorphism ↔ {subgroups H ⊂ π₁(X,x₀)} / conjugacy

Key entries in this bijection:
- Universal cover X̃ ↔ trivial subgroup {1}
- X itself ↔ entire group π₁(X)
- Normal covering ↔ normal subgroup H ◁ π₁(X)

**Deck transformations**: Automorphisms of X̃→X as covering spaces.
- Deck group = N(H)/H where H=p∗(π₁(X̃)) and N(H)=normalizer
- For normal covers: Deck(X̃/X) ≅ π₁(X)/H
- For universal cover: Deck(X̃/X) ≅ π₁(X)

**Group actions**: A covering space action of G on X̃ is a free, properly
discontinuous action. Then X̃→X̃/G is a normal covering with deck group G.

## Key Computations

| Space | π₁ |
|-------|-----|
| S¹ | ℤ |
| Sⁿ (n≥2) | 0 |
| Torus T² | ℤ×ℤ |
| Klein bottle | ⟨a,b | abab⁻¹⟩ |
| ℝP² | ℤ/2 |
| ℝPⁿ (n≥2) | ℤ/2 |
| S¹∨S¹ | ℤ∗ℤ |
| Genus-g surface | ⟨a₁,b₁,...,aₘ,bₘ | Π[aᵢ,bᵢ]⟩ |

## Graphs and Free Groups (§1.A)

**Theorem**: The fundamental group of a graph is a free group.
The free group on n generators = π₁(∨ⁿ S¹).

Every subgroup of a free group is free (via covering space theory applied to graphs).

If G acts freely and properly discontinuously on a tree, G is free.

## K(G,1) Spaces (§1.B)

A K(G,1) space (Eilenberg-MacLane space) has π₁=G and all higher πₙ=0.
- S¹ = K(ℤ,1)
- T^n = K(ℤⁿ,1)
- ℝPⁿ→ K(ℤ/2, 1) = ℝP∞ as n→∞

H∗(K(G,1)) = group homology H∗(G).
