---
name: thompson-type-theory
description: "Use when type-driven development or Curry-Howard."
related_skills:
  - coding-conventions
  - test-driven-development
  - systematic-debugging
---

# Type Theory and Functional Programming
**Author**: Simon Thompson | **Source**: Addison-Wesley / University of Kent, March 1999 | **Chapters**: 8 + intro

Knowledge base from Thompson *Type Theory and Functional Programming*. Use when reasoning about type-driven development, propositions-as-types, correctness-by-construction, dependent types, or proof-carrying code.

Thompson's thesis: constructive type theory is simultaneously a logic and a total functional language. Program development and verification proceed in one system. Prefer these moves: write the type as the theorem, inhabit it with a total function as the proof, and refuse partiality.

## How to Use This Skill

- Load this file for Curry-Howard, dependent types, totality, structural induction, and correctness-by-construction.
- Apply the coding rules in `coding-conventions`, `test-driven-development`, and `systematic-debugging` when writing or debugging code.

---

## Core Frameworks

### Curry-Howard correspondence (Ch 4.4, 5.12)

Propositions are types; proofs are terms. Write `p : P` interchangeably as "p has type P" and "p proves proposition P".

| Logic | Programming |
|-------|-------------|
| A ∧ B | product / pair `(a, b)` |
| A ⇒ B | function space `A → B` |
| A ∨ B | disjoint union / sum |
| ⊥ | empty type |
| ∀x:A. B(x) | dependent function: result type depends on the value |
| ∃x:A. B(x) | dependent sum: value plus witness |

Formation rules say what the types are. Introduction/elimination rules say which terms inhabit them (static typing). Computation rules say how they reduce (dynamics). In the full system, type-checking and computation intertwine — dependent types make the "static" phase evaluate terms.

**Coding rule:** a type signature is a theorem; a function body is its proof. If the type admits a wrong input, the theorem is too weak — narrow the type instead of adding a runtime check.

Thompson's caveat: do not read `plus : N ⇒ N ⇒ N` as "plus meets its specification". That type is an under-specification. A real spec is an existential: `(a, b) : (∃x:A). B(x)` means *a of type A meets B, as proved by b*. You only claim a program meets a spec when you have the witness.

### Propositions-as-types

Constructive validity is explained by *what counts as a proof*. A proof of A ⇒ B is a function turning proofs of A into proofs of B. A proof of ∀x.∃y. R(x,y) *is* an algorithm taking x to a y with a witness for R.

**Coding rule:** a property-based test is an executable proposition. Frame each property as a theorem to be proved (inhabited for all generated inputs), not a checklist item that happened to pass.

### Correctness-by-construction

Type theory integrates development and proof: you do not write a program and then verify it; you inhabit a specification type, and the inhabitant *is* the program plus its correctness witness. Extracting an algorithm from ∀x.∃y. R(x,y) is not a post-hoc pass — the proof already contains the algorithm.

Subset / existential types encode "values that satisfy B". Invalid states have no constructor.

**Coding rule:** design data types so invalid states cannot be constructed (parse-don't-validate). The constructor *is* the validator. Runtime validation after construction is a failed formation rule.

### Dependent types (Ch 4.10.3, 6.3)

A dependent type is a type expression with free variables — logically, a predicate. Introduced by equality types `I(A, a, b)` (written `a =_A b`) and then closed under connectives and quantifiers.

- `(∀x:A). B(x)` — result type depends on the argument value (e.g. array ops parametrised on *dimension*, not just element type).
- `(∃x:A). B(x)` — a value together with a proof it satisfies B; also modules / ADTs.
- Example: `(∃l:[A]). (#l =_N n)` is lists of length n (pair of list + length proof).

Universes `U0, U1, …` let you define type families by recursion/cases, not only by wrapping booleans as propositions. Boolean-valued predicates are only the *decidable* fragment; quantification over infinite domains leaves that fragment.

### Structural induction (Def 2.11, Def 4.2)

To prove P(e) for all terms of an inductive type, prove it on constructors, assuming it on immediate predecessors.

- λ-terms: P(x); P(e f) from P(e), P(f); P(λx.e) from P(e).
- Trees: P(Null) outright; P(Bnode n u v) from P(u) and P(v).
- N: P(0); P(n+1) from P(n).

In a constructive setting, **induction and primitive recursion are the same object**: the induction proof *is* the recursive function. Recursion that is not structurally decreasing is not a proof and may fail to terminate.

**Coding rule:** when debugging a recursive function, split the failure: base case vs inductive step. A recursive bug lives in exactly one of those two places.

### Totality (Ch 2, 5.5–5.6, 6.1)

Every function in the type theory is total: evaluation terminates (strong normalisation) and is deterministic (Church-Rosser / unique normal forms). Unrestricted general recursion is refused because it admits Ω and non-termination, which would collapse the logic (a non-terminating "proof" of ⊥).

If a function is only defined on a subset, *narrow the domain* with an existential/subset type so the function is total on that type. Sometimes the definition itself carries an inductive termination proof — computation and verification are interleaved.

Anything provably total in Peano arithmetic can be programmed in TT0; the constructive derivation *is* the totality proof.

**Coding rule:** a partial function (throws/crashes on some inputs) is a defect. Handle every case; use Option/Result for expected failure instead of exceptions.

---

## Chapter Index

| # | Title | Key frameworks |
|---|-------|----------------|
| 1 | Introduction to Logic | natural deduction, quantifiers |
| 2 | Functional Programming and λ-Calculi | evaluation, Church-Rosser, structural induction, strong normalisation |
| 3 | Constructive Mathematics | BHK interpretation, no LEM |
| 4 | Introduction to Type Theory | Curry-Howard, formation/intro/elim/computation, N, trees, equality, dependent types |
| 5 | Exploring Type Theory | normalisation, equalities, universes, W-types, limits of the isomorphism |
| 6 | Applying Type Theory | recursion/totality, Quicksort, dependent quantifiers, vectors |
| 7 | Augmenting Type Theory | subset types, quotients, coinduction, controlled general recursion |
| 8 | Foundations | models, inversion of intro rules, related systems |

## Topic Index

- **Church-Rosser / unique NF** → ch2, ch5
- **Constructive mathematics / BHK** → ch3
- **Correctness-by-construction / specs as ∃** → intro, ch4
- **Curry-Howard** → intro, ch4.4, ch5.12
- **Dependent types / ∀ ∃ W** → ch4.10, ch6.3
- **Equality / I-types** → ch4.10, ch5.7–5.8
- **Extraction of programs from proofs** → intro, ch4, ch6
- **Normalisation / termination** → ch2.7, ch5.5–5.6
- **Primitive recursion = induction** → ch4.8–4.9, ch6.1
- **Propositions-as-types** → intro, ch4
- **Structural induction** → ch2 Def 2.11, ch4 Def 4.2
- **Subset types** → ch6.3, ch7
- **Totality** → preface, ch2, ch6.1
- **Universes** → ch5.9, ch6.3
- **Vectors / finite types Cn** → ch6.4

## Scope & Limits

Covers Thompson's 1999 text only. Not a tutorial for Coq/Agda/Lean syntax. For day-to-day coding rules distilled from this book, use the patched `coding-conventions`, `test-driven-development`, and `systematic-debugging` skills.
