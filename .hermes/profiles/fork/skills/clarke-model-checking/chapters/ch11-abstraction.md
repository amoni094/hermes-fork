# Chapter 11: Abstraction

## Core Idea
Map concrete states into fewer abstract states (existential abstraction). ACTL properties true on the abstract model are true on the concrete model. False may be spurious — refine.

## Frameworks Introduced
- **Existential abstraction** h : S → Ŝ:
  R̂(ŝ,ŝ') iff ∃s∈h⁻¹(ŝ), s'∈h⁻¹(ŝ'). R(s,s')
  L̂(ŝ) ⊆ ⋂_{s∈h⁻¹(ŝ)} L(s) for preserved atoms (or over-approx labels carefully).
  Concrete is simulated by abstract: M ≼ M̂. Hence M̂ ⊦ ACTL φ ⇒ M ⊦ φ.
- **Spurious counterexample**: abstract path with no concrete lift. Refine h (split an abstract state) and re-check (CEGAR pattern; Clarke–Grumberg–Long, later Clarke–Grumberg–Jha–Lu–Veith).
- **Data abstraction**: ignore a variable or replace int by sign/{0,>0,<0}.

## Key Concepts
- **Preservation direction**: universal properties go *down* from abstract to concrete; existential (E) do not.
- **Cone of influence**: drop variables that cannot affect AP in φ (cheap exact reduction).
- **Predicate abstraction**: abstract state = valuation of a set of predicates — later work, same idea.

## Mental Models
- Abstract to *prove* AG; if abstract says no, either the bug is real or you over-merged.
- Never use an existential abstraction to prove EF/EG.

## Anti-patterns
- Using existential abstraction to prove EF/EG/EU (ECTL). ACTL (AX, AG, AF, AU) is preserved; ECTL is not.
- Treating a spurious abstract cex as a concrete bug without attempting a lift.
- Refining forever without a progress metric (number of abstract states or predicates).

## Worked Example
Gate-audit: concrete sweep has many file paths. Abstract to {no_data, fetching, available}. If AF available holds on the abstract scheduler (sweep eventually fires), it holds concretely. If abstract loops in no_data because you merged “timer fired” with “timer idle”, cex is spurious — split.

## Key Takeaways
1. Existential abstraction ⇒ simulation ⇒ ACTL preservation.
2. Spurious cex ⇒ refine, do not patch the formula.
3. Cone of influence first (exact).

## Connects To
- **Ch 9**: simulation.
- **Ch 16**: counterexample-guided simulation on the concrete log.
