# Chapter 18: Integration over General Measure Spaces

## Core Idea
All integration theorems from Part I (MCT, Fatou, DCT, Vitali) generalize to abstract measure spaces (X, M, μ). The centerpiece is the Radon-Nikodym theorem and Lebesgue decomposition, plus the Vitali-Hahn-Saks theorem on stability of absolute continuity under limits.

## Key Concepts
- **Measurable function on (X,M,μ)**: f: X → ℝ̄ with f⁻¹((c,∞]) ∈ M for all c ∈ ℝ.
- **Integration**: Three-stage construction parallels Ch04 (simple → nonneg → general). All properties (linearity, monotonicity, countable additivity, MCT, Fatou, DCT) hold verbatim.
- **Absolute continuity ν ≪ μ**: μ(E)=0 ⟹ ν(E)=0.
- **Singularity ν ⊥ μ**: ∃E with μ(E)=0 and ν(Eᶜ)=0.

## The Radon-Nikodym Theorem (§18.4)
**Statement**: Let (X, M) be a measurable space with σ-finite measures μ and ν, with ν ≪ μ. Then ∃ unique measurable f ≥ 0 (written dν/dμ) such that ν(E) = ∫_E f dμ for all E ∈ M.

**Properties of the RN derivative**:
- Change-of-measure: ∫_X h dν = ∫_X h·(dν/dμ) dμ for any ν-integrable h
- Chain rule: ν ≪ μ ≪ λ ⟹ dν/dλ = (dν/dμ)·(dμ/dλ) a.e.[λ]
- Symmetry: ν ≪ μ and μ ≪ ν ⟹ dν/dμ · dμ/dν = 1 a.e.

**Von Neumann's proof sketch**: Let λ = μ + ν. Apply Riesz-Fréchet to L2(X,λ): the functional φ ↦ ∫φ dν is bounded on L2(λ). ∃g ∈ L2(λ) with ∫φ dν = ∫φg dλ = ∫φg dμ + ∫φg dν. Algebra gives dν/dμ = g/(1-g).

**Lebesgue Decomposition**: ν = νₐc + νₛ where νₐc ≪ μ (νₐc(E) = ∫_E f dμ) and νₛ ⊥ μ. Unique.

## The Vitali-Hahn-Saks Theorem (§18.5)
**Statement**: Let {νₙ} be measures on (X,M), all absolutely continuous w.r.t. μ. If νₙ(E) → ν(E) for all E ∈ M (setwise convergence), then ν ≪ μ and the absolute continuity is uniform: ∀ε>0 ∃δ>0: μ(E)<δ ⟹ sup_n |νₙ(E)| < ε.

- **Proof**: Uses Nikodym metric space (space of measures with metric d(ν₁,ν₂) = |ν₁-ν₂|(X)) and Baire Category theorem.
- **Consequence**: Uniform AC prevents "mass escape" in the limit — the limit measure ν inherits the AC property and the absolute continuity is not eroded iteration by iteration.

## Key Takeaways
1. All Part I integration theorems hold for abstract measure spaces — the abstraction is "free."
2. Radon-Nikodym = abstract FTC. The condition ν ≪ μ is the abstract analog of absolute continuity of functions.
3. Von Neumann's proof connects RN to Hilbert space theory (Riesz-Fréchet) — a beautiful cross-part application.
4. Vitali-Hahn-Saks: setwise convergence of measures preserves absolute continuity and makes it uniform — a stability theorem for measure sequences.

## Connects To
- **Ch06**: Lebesgue FTC is the ℝ case of Radon-Nikodym
- **Ch17**: Signed measures, Hahn-Jordan decomposition used in this chapter
- **Ch19**: Dunford-Pettis uses RN as a key ingredient
- **Ch21**: Radon-Nikodym for Radon measures on locally compact spaces
