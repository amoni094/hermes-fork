# Chapter 2: Lebesgue Measure

## Core Idea
Constructs Lebesgue measure m on ℝ in two stages: outer measure m* (defined on all sets, not additive) → restriction to the σ-algebra of Lebesgue measurable sets (countably additive). This construction pattern is the model for all abstract measure theory.

## Key Concepts
- **Lebesgue outer measure**: m*(A) = inf{Σ ℓ(Iₖ) : A ⊆ ∪Iₖ, Iₖ open intervals}. Defined for every subset, monotone, countably subadditive.
- **Carathéodory condition**: E is Lebesgue measurable iff m*(A) = m*(A∩E) + m*(A∩Eᶜ) for every A ⊆ ℝ.
- **σ-algebra M**: Collection of Lebesgue measurable sets. Contains all Borel sets, all null sets. m restricted to M is a complete measure (supersets of null sets are measurable).
- **Countable additivity**: m(∪Eₖ) = Σm(Eₖ) for disjoint {Eₖ} ⊆ M.
- **Continuity of measure**: Eₙ ↑ E ⟹ m(Eₙ) → m(E); Eₙ ↓ E with m(E₁) < ∞ ⟹ m(Eₙ) → m(E).
- **Borel-Cantelli Lemma**: If Σm(Eₖ) < ∞, then m(lim sup Eₖ) = 0. Equivalently: a.e. point belongs to only finitely many Eₖ.
- **Nonmeasurable sets**: Vitali construction (using Axiom of Choice) produces non-Lebesgue-measurable sets — Lebesgue measure cannot be extended to all subsets of ℝ.
- **Cantor set**: Closed, nowhere dense, uncountable, measure zero. Cantor-Lebesgue function: continuous, monotone, f' = 0 a.e., yet f(0)=0, f(1)=1.

## Frameworks Introduced
- **Two-Stage Measure Construction** (Carathéodory): Define primitive set function → extend to outer measure (subadditive) → restrict to measurable sets (additive). Applied again in Ch17 for general abstract measures.
  - When to use: Constructing any σ-finite measure from a simpler prescription (e.g., length → Lebesgue)
  - How: (1) Cover formula for outer measure, (2) Carathéodory splitting condition, (3) Verify σ-algebra closure

## Worked Example — Borel-Cantelli Application
Let Eₙ = (0, 1/n²) ⊆ [0,1]. Then Σm(Eₙ) = Σ1/n² = π²/6 < ∞. By Borel-Cantelli, m(lim sup Eₙ) = 0. Although each Eₙ contains 0, for a.e. x ∈ [0,1], x is in only finitely many Eₙ.

**Hermes translation**: If event-set {Eₙ} = {sessions where skill k is invoked at step n}, Borel-Cantelli says: if the invocation probabilities decay fast enough (summable), skill k is invoked at only finitely many steps a.s.

## Key Takeaways
1. Lebesgue measure = the unique complete, translation-invariant Borel measure on ℝ normalized so m([0,1])=1.
2. Null sets (m=0) are negligible — countable sets, Cantor set, Lipschitz images of lower-dimensional sets.
3. The Borel-Cantelli Lemma converts decay of probabilities into almost-sure finiteness: the key tool for "convergence happens eventually a.s."
4. Nonmeasurable sets exist but require Axiom of Choice; practical computations stay within Borel/measurable sets.

## Connects To
- **Ch03**: Measurable functions defined relative to this σ-algebra
- **Ch17**: Carathéodory construction generalized to abstract spaces
