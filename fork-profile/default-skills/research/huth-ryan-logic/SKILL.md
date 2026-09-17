---
name: huth-ryan-logic
description: "Use when Hoare logic, LTL/CTL, or model checking."
related_skills:
  - coding-conventions
  - systematic-debugging
  - verification-before-completion
  - test-driven-development
---

# Huth & Ryan — Logic in Computer Science (2nd ed., 2004)

Knowledge base from Huth & Ryan, *Logic in Computer Science: Modelling and Reasoning about Systems* (Cambridge). Use when reasoning about program correctness, Hoare logic, model checking, temporal logic (LTL/CTL), formal specification, or invariant verification. Notation follows the book. Prefer this file over informal paraphrases.

Source PDF: `/var/home/rainbow/books/logic/Logic in computer science_ modelling and reasoning about systems.pdf`
Extract: `/tmp/book_skill_work_logic/full_text.txt`

Chapters: 1 propositional logic · 2 predicate logic · 3 model checking (LTL/CTL, NuSMV) · 4 program verification (Hoare) · 5 modal logics and agents · 6 BDDs / symbolic model checking.

## When to use

- Specifying or checking a function's entry/exit conditions (Hoare triples).
- Choosing or checking a loop invariant.
- Distinguishing safety vs liveness in concurrent/async code.
- Debugging by computing weakest preconditions backwards from a failing postcondition.
- Deciding whether a property is LTL, CTL, or neither, before writing tests or a model.
- SAT/CNF/Horn as a decision procedure for propositional constraints.

## Propositional logic

**Language.** Atoms `p, q, r, …` and connectives `¬, ∧, ∨, →, ↔`. Formulas are trees (or DAGs when subformulas are shared).

**Sequents.** `φ1, …, φn ⊢ ψ` is valid iff a natural-deduction proof of `ψ` from the premises exists. Semantic entailment `φ1, …, φn ⊨ ψ` holds iff every valuation that makes all premises true makes `ψ` true. `⊨ φ` = tautology; `φ` is satisfiable iff some valuation makes it true.

**Natural deduction.** One introduction and one or more elimination rules per connective. Core rules:

| Rule | Form |
|------|------|
| `∧i` | from `φ` and `ψ` infer `φ ∧ ψ` |
| `∧e1/∧e2` | from `φ ∧ ψ` infer `φ` / `ψ` |
| `→i` | discharge assumption `φ` to conclude `φ → ψ` |
| `→e` (modus ponens) | from `φ → ψ` and `φ` infer `ψ` |
| `¬i` | from `φ ⊢ ⊥` infer `¬φ` |
| `¬e` | from `φ` and `¬φ` infer `⊥` |
| `⊥e` | from `⊥` infer any `φ` |
| PBC | from `¬φ ⊢ ⊥` infer `φ` (classical) |
| LEM | `φ ∨ ¬φ` |

Soundness is easy (each rule preserves truth). Completeness is harder: every semantically valid sequent has a proof. Corollary 1.39: `φ1,…,φn ⊨ ψ` iff `φ1,…,φn ⊢ ψ`.

**Practice.** A sequent with no proof is shown by a countermodel (valuation making premises true and conclusion false). Soundness then forbids a derivation. Do not hunt for a missing proof of an invalid sequent.

## Normal forms and SAT

**CNF.** A formula is in conjunctive normal form if it is a conjunction of clauses, each a disjunction of literals (`p` or `¬p`). Validity of CNF is easy (a clause is a tautology iff it contains `p` and `¬p`). Satisfiability of CNF is hard in general.

**Horn SAT is linear.** A Horn clause is an implication whose body is a conjunction of atoms and whose head is an atom or `⊥` (at most one positive literal). Algorithm HORN: mark `⊥`-free facts that must be true; propagate; if `⊥` is marked, unsat. At most `n+1` while-iterations for `n` atoms (Thm 1.47). Invariant: every marked atom is true in every satisfying valuation.

**SAT solvers (Ch 1.6).** Represent the formula as a DAG (share repeated subformulas). A linear solver applies *forcing laws* (e.g. `¬` swaps T/F; `∧` with T on the parent forces T on both children). Outcomes: all nodes forced consistently → sat witness; contradictory marks → unsat. Incomplete: some CNF instances need a cubic solver that tries assignments. Validity check: `φ` is valid iff `¬φ` is unsatisfiable. Translate sequents to SAT via `T(φ1 ∧ … ∧ φn ∧ ¬ψ)`.

**Agent use.** Encode a boolean constraint as CNF; if it is Horn, decide in linear time; otherwise call a SAT solver rather than building a truth table (`2^n`).

## Predicate logic

Richer language: terms (variables, constants, function applications), atomic formulas `P(t1,…,tn)` and `t1 = t2`, quantifiers `∀x`, `∃x`.

- Free vs bound variables; capture-avoiding substitution `[t/x]`.
- Natural deduction extends with `∀i/∀e`, `∃i/∃e` (eigenvariable / freshness side conditions).
- Semantics: a model is a domain plus interpretations of constants, functions, predicates. Semantic entailment matches Ch 1, over models instead of valuations.
- Predicate logic is undecidable (Church/Turing). Validity is not a SAT-style decision procedure.
- Expressiveness: existential/universal second-order logic strictly exceed first-order in some cases (Ch 2.6).
- Micromodels (Alloy-style, Ch 2.7): finite state machines as bounded models of software; useful for finding counterexamples, not for proving unbounded correctness.

## Temporal logic and model checking

**Models.** Transition system `M = (S, →, L)`: states, total transition relation, labelling of states with atomic propositions. A *path* is an infinite sequence `s1 → s2 → …`. Deadlocks are encoded by a sink `sd → sd`.

### LTL (linear-time)

Formulas evaluated on paths, then lifted to states: `M, s ⊨ φ` iff **every** path from `s` satisfies `φ`. Operators (future includes present):

| Op | Meaning on path `π` |
|----|---------------------|
| `X φ` | `φ` holds in the next state |
| `F φ` | `φ` holds in some future state (incl. now) |
| `G φ` | `φ` holds in every state of `π` |
| `φ1 U φ2` | `φ2` holds at some `i`, and `φ1` holds at all `j < i` |

Validities that follow from "future includes present": `G p → p`, `p → F p`, `p → q U p`.

`G F p` = infinitely often `p`. `F G p` = eventually always `p`.

**Specification patterns (Ch 3.2.3):**

- Safety ("nothing bad"): `G ¬(started ∧ ¬ready)`, mutex `G ¬(c1 ∧ c2)`.
- Request/ack: `G (requested → F acknowledged)`.
- Infinitely often enabled: `G F enabled`.
- Fair response: `G F enabled → G F running`.
- Conditional until: `G (floor2 ∧ directionup ∧ ButtonPressed5 → (directionup U floor5))`.

LTL on states cannot assert *existence* of a path (that needs CTL `E`). Negating a safety formula on states says *every* path eventually hits the bad state, not that one path can.

### CTL (branching-time)

State formulas. Path quantifier `A` (all paths) or `E` (exists a path) must immediately precede a temporal operator. Standard six:

| Formula | Meaning |
|---------|---------|
| `AG φ` | `φ` on every state of every path (invariant) |
| `AF φ` | every path eventually hits `φ` |
| `EG φ` | some path on which `φ` always holds |
| `EF φ` | some path eventually hits `φ` |
| `A[φ1 U φ2]`, `E[φ1 U φ2]` | until, all / some paths |
| `AX φ`, `EX φ` | next-state, all / some successors |

CTL* mixes freely; LTL ≈ A-only path formulas; LTL and CTL are incomparable (some properties only in one).

**Mutual exclusion (Ch 3.3).** Four properties, different techniques:

1. **Safety** — `G ¬(c1 ∧ c2)` / `AG ¬(c1 ∧ c2)`. Counterexample is a finite prefix to a bad state.
2. **Liveness** — `G (t1 → F c1)`. Counterexample is an infinite unfair path; needs fairness assumptions (`FAIRNESS` in SMV).
3. **Non-blocking** — a waiting process can enter.
4. **No strict sequencing** — not forced to alternate.

Safety and liveness are not interchangeable. Safety is refuted by a finite bad trace; liveness is refuted only by an infinite trace that postpones the good event forever. Tests that only run finite scenarios can miss liveness bugs; model checkers need fairness constraints so that "process 2 stays in CS forever" is excluded.

### Model checking and state explosion

CTL labelling is linear in `|M| · |φ|`, but `|M|` is typically **exponential in the number of variables and parallel components**. Adding one boolean **doubles** the state space. That is the state-explosion problem (Ch 3.6).

Mitigations in the book: symbolic model checking with OBDDs (Ch 6), fairness-restricted search, abstraction, symmetry, compositionality, bounded model checking (NuSMV). NuSMV supports LTL and CTL; original CMU SMV was CTL-only.

**Agent use.** Before debugging concurrent code at full scale, write a *small* explicit model (few booleans, few processes) and enumerate reachable states. If that model already explodes, the concurrency design is too complex — simplify the protocol before hunting the bug.

## Hoare logic (Ch 4)

A **Hoare triple** `{P} C {Q}` (book: `φ P ψ`) means: if command `C` is started in a state satisfying precondition `P`, then —

- **Partial correctness** `⊨par {P} C {Q}`: *if* `C` terminates, the final state satisfies `Q`. Non-termination vacuously satisfies every partial spec.
- **Total correctness** `⊨tot {P} C {Q}`: `C` *does* terminate, and the final state satisfies `Q`.

Prove partial correctness first, then termination (Ch 4.4). A looping program satisfies no total spec.

**Logical vs program variables.** Program variables occur in `C` and may be mutated. Logical variables (`x0`) appear only in `P`/`Q`, are universally quantified in the precondition, and remember initial values: `{x = x0 ∧ x ≥ 0} Fac2 {y = x0!}`.

### Proof rules (partial correctness, Fig 4.1)

**Assignment axiom** (apply *backwards*):

```
{ψ[E/x]}  x = E  {ψ}
```

To establish `ψ` after `x = E`, prove `ψ` with `E` in place of free `x` *before* the assignment. Forwards is not mechanical; backwards is substitution. Never skip intervening assignments (they overwrite the values the substitution refers to).

**Composition.** Find a midcondition `η`:

```
{P} C1 {η}    {η} C2 {Q}
---------------------------
{P} C1 ; C2 {Q}
```

**If.**

```
{P ∧ B} C1 {Q}    {P ∧ ¬B} C2 {Q}
--------------------------------------
{P} if B {C1} else {C2} {Q}
```

Weakest-precondition form: `P = (B → P1) ∧ (¬B → P2)` where `P1`/`P2` are WPs of the branches.

**Partial-while** (the invariant rule):

```
{I ∧ B} C {I}
-------------------------------
{I} while B {C} {I ∧ ¬B}
```

`I` is the **loop invariant**: true before the loop, preserved by the body when `B` holds, and `I ∧ ¬B` must imply the desired postcondition (Implied rule). Choosing `I` requires ingenuity; assignment and composition do not.

**Implied (consequence).** If `P' → P` and `{P} C {Q}` and `Q → Q'`, then `{P'} C {Q'}`.

**Total-while** adds a variant `E ≥ 0` that strictly decreases each iteration; WP of the while is then `I ∧ 0 ≤ E`.

### Weakest precondition

Work from the postcondition *upwards* through the program. The WP of `C` wrt `Q` is the weakest `P` such that `{P} C {Q}` (partial). For assignment, WP is exactly `ψ[E/x]`. For a sequence, push `Q` through `Cn`, then `Cn-1`, … For while, you still invent `I`; WP does not invent invariants.

**Debugging reading.** If `C` is incorrect for postcondition `Q`, the WP of `C` wrt `Q` is the *minimal* entry condition under which `Q` would hold. The bug manifests precisely when the actual precondition does not imply that WP — that gap *is* the reproduction case. Compute WP backwards from the failing assertion until the implication `actual P → WP` breaks; the first broken command is the fault.

### Programming by contract (Ch 4.5)

A method's Hoare triple *is* its contract: callers must establish `P`; the method guarantees `Q` if it returns. Contracts compose only if the call graph is acyclic (else circular reasoning). Use logical variables for values the callee mutates.

## Agent rules distilled

1. Every non-trivial function has an implicit Hoare triple. Write `P` and `Q` in the docstring when state is complex; types are not a substitute for `Q`.
2. Every loop that is not obviously a `for`-over-finite-collection needs an invariant `I` such that `{I} loop {I}` and `I ∧ ¬B` implies the postcondition. Without `I`, loop correctness cannot be verified.
3. Debug incorrect functions by computing WP backwards from the failing postcondition; the first place `P ⊨ WP` fails is the reproduction.
4. In concurrent/async code, classify each property as safety (finite counterexample, mutex, no data race) or liveness (infinite counterexample, progress, no deadlock). Test and verify them differently; liveness needs fairness.
5. Concurrent bugs: enumerate reachable states of a *small* model first. State explosion means simplify the protocol, do not scale the debugger.

## Quick index

| Need | Reach for |
|------|-----------|
| Proof vs truth | `⊢` sequent vs `⊨` entailment; soundness/completeness |
| Boolean decision | CNF; Horn if possible; else SAT |
| Function contract | `{P} C {Q}` partial vs total |
| Assignment reasoning | backwards substitution `ψ[E/x]` |
| Loop | invariant `I` + optional variant `E` |
| "Never happens" | LTL `G ¬bad` / CTL `AG ¬bad` |
| "Eventually happens" | LTL `F` / `G (· → F ·)` + fairness |
| "Some path exists" | CTL `E·`, not LTL |
| State space too big | explode → abstract / compose / BDD / shrink the model |
