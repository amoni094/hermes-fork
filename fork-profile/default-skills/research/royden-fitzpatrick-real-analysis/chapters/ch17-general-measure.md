# Chapters 17–18: General Measure Spaces and Radon-Nikodym

## Ch17 Core Idea: General Measure Spaces
Abstracts Lebesgue measure to an arbitrary measure space (X, M, μ). Defines signed measures, proves Hahn-Jordan decomposition, and shows the Carathéodory construction works for any outer measure.

## Ch18 Core Idea: Integration and Radon-Nikodym
All integration theorems (MCT, Fatou, DCT, Vitali) hold for general measure spaces. The Radon-Nikodym theorem is the abstract FTC: if ν ≪ μ, then dν = f dμ for a measurable density f.

## Key Concepts

### σ-finite Measures (Ch17)
μ is σ-finite if X = ∪Xₙ with μ(Xₙ) < ∞. Lebesgue measure is σ-finite (ℝ = ∪[-n,n]). Most theorems require σ-finiteness.

### Signed Measures and Hahn-Jordan Decomposition (Ch17)
- **Signed measure**: ν: M → ℝ̄, countably additive, ν(∅) = 0, at most one of ±∞ in range.
- **Hahn decomposition**: ∃ disjoint P,N with P∪N = X where P is positive (ν(E∩P) ≥ 0 for all E) and N is negative.
- **Jordan decomposition**: ν = ν⁺ - ν⁻ where ν⁺(E) = ν(E∩P), ν⁻(E) = -ν(E∩N). Total variation |ν| = ν⁺ + ν⁻.

### Absolute Continuity and Radon-Nikodym (Ch18)
- **ν ≪ μ** (ν absolutely continuous w.r.t. μ): μ(E) = 0 ⟹ ν(E) = 0.
- **ν ⊥ μ** (ν singular w.r.t. μ): ∃ E with μ(E) = 0 and ν(Eᶜ) = 0.
- **Lebesgue Decomposition**: ν = νₐc + νₛ where νₐc ≪ μ and νₛ ⊥ μ. Unique decomposition.

### Radon-Nikodym Theorem
**Statement**: If μ and ν are σ-finite measures on (X,M) with ν ≪ μ, then ∃ unique measurable f ≥ 0 (the **Radon-Nikodym derivative** dν/dμ or f = dν/dμ) such that ν(E) = ∫_E f dμ for all E ∈ M.

**Chain rule**: If ν ≪ μ ≪ λ (all σ-finite): dν/dλ = (dν/dμ)(dμ/dλ) a.e.[λ].

**Proof strategy (von Neumann's proof)**: Define A = μ + ν. Apply Riesz-Fréchet to L2(X,A): the functional φ ↦ ∫φ dν is bounded on L2(A). Get g ∈ L2(A) with ∫φ dν = ∫φg dA. Then f = g/(1-g) is the RN derivative.

### Vitali-Hahn-Saks Theorem (Ch18)
If {νₙ} are measures absolutely continuous w.r.t. μ and νₙ(E) → ν(E) for all E, then ν ≪ μ and the absolute continuity is uniform: ∀ε>0 ∃δ>0: μ(E)<δ ⟹ sup_n |νₙ(E)| < ε.
- **Use**: Continuity of measure limits. Prevents "escape of mass" in limit of measures.

## Worked Example — Radon-Nikodym in Skill Weighting
Let μ = uniform distribution over skills (reference). Let ν = learned distribution from usage data. If every skill with μ-probability 0 also has ν-probability 0 (ν ≪ μ), then the weight update is a Radon-Nikodym derivative: weight(skill) = dν/dμ(skill). The chain rule then says: if weights are updated in two stages (ν ≪ μ ≪ λ), the total weight = product of stage weights.

## Key Takeaways
1. Radon-Nikodym is the abstract FTC: "density of ν w.r.t. μ." The condition ν ≪ μ is the abstract version of absolute continuity.
2. Lebesgue decomposition: every measure = AC part + singular part w.r.t. reference measure. In Hermes: routing weight = "learnable" AC part + "fixed" singular part.
3. Vitali-Hahn-Saks: uniform absolute continuity is inherited by limits of measures. Prevents gradual erosion of absolute continuity over iterations.
4. σ-finiteness is the right generality: excludes pathological infinite measures, includes all practical cases.

## Connects To
- **Ch06**: Radon-Nikodym generalizes the FTC (absolutely continuous functions ↔ RN derivatives)
- **Ch19**: RN theorem used to identify [L1]* = L∞ and for Dunford-Pettis
- **Ch21**: Radon measures on topological spaces; RN for Borel measures
