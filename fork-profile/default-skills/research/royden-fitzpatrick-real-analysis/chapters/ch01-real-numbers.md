# Chapter 1: The Real Numbers — Sets, Sequences, and Functions

## Core Idea
Establishes the foundational framework: field axioms, completeness of ℝ, Borel sets, and the topology of the real line — the setting for all of Part I measure theory.

## Key Concepts
- **Completeness Axiom**: Every nonempty subset of ℝ bounded above has a least upper bound (supremum). Equivalently: every Cauchy sequence of reals converges.
- **Borel σ-algebra B(ℝ)**: The smallest σ-algebra containing all open subsets of ℝ. Every open set, closed set, Gδ (countable intersection of opens), Fσ (countable union of closeds) is Borel.
- **lim sup / lim inf**: For {aₙ}, lim sup aₙ = inf_n sup_{k≥n} aₙ; lim inf = sup_n inf_{k≥n} aₙ. A sequence converges iff lim sup = lim inf.
- **Countable vs. Uncountable**: ℚ is countable; ℝ and any interval (a,b) are uncountable (Cantor diagonal). Countable union of countable sets is countable.
- **Open sets in ℝ**: Every open set is a countable disjoint union of open intervals.
- **Extended real line ℝ̄ = ℝ ∪ {±∞}**: Allows sup/inf without worrying about finiteness.

## Frameworks Introduced
- **σ-Algebra Construction**: Start with open sets → take complements, countable unions, countable intersections → arrive at Borel sets. This construction pattern recurs in all measure theory.
  - When to use: Defining measurable sets for any topological space
  - How: Identify generator class → apply σ-algebra closure operations
- **Zorn's Lemma** (nonconstructive): Every partially ordered set in which every chain has an upper bound has a maximal element. Required for Hahn-Banach, existence of nonmeasurable sets.

## Key Takeaways
1. The supremum property of ℝ is what makes Lebesgue measure possible — without completeness, we cannot pass to limits.
2. Borel sets are the "natural" measurable sets for measure theory on ℝ; Lebesgue measurable sets strictly contain Borel sets.
3. Countability distinctions are essential: countable additivity of measure depends on the fact that ℕ is countable.

## Connects To
- **Ch02**: σ-algebra of Lebesgue measurable sets extends the Borel σ-algebra
- **Ch17**: General measure spaces begin with an abstract σ-algebra, echoing this chapter
