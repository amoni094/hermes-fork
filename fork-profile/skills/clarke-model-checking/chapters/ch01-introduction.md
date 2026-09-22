# Chapter 1: Introduction

## Core Idea
Model checking decides M ⊦ φ automatically for a finite-state concurrent system M and a temporal specification φ, and returns a counterexample path when the answer is no.

## Frameworks Introduced
- **Automatic verification**: exhaustive exploration of the state graph vs testing (incomplete) vs theorem proving (not push-button).
  - When to use: finite AP, finite S, properties in CTL/LTL.
  - How: model → formula → check → counterexample or proof certificate (all states labelled).
- **Counterexample-guided debugging**: a failing AG p is a finite trace to ¬p; a failing AF p is a lasso that avoids p forever.
  - When to use: any negative result.
  - How: replay the path on the concrete scheduler (guided simulation).

## Key Concepts
- **Finite-state concurrent system**: sequential circuits, protocols, interleaving products of local machines.
- **State-space explosion**: |S| ≈ product of local state counts; the central engineering problem of the book.
- **Soundness of the method**: if the checker says yes, every initial state satisfies φ on the model (not on the undocumented real world).
- **Incompleteness of testing**: a test suite is a finite set of paths; LTL/CTL quantify over *all* paths.
- **Kanellakis Award (1998)**: industrial uptake of SMV-style checkers is the book's practical warrant.

## Mental Models
- Think of model checking as **exhaustive simulation with a formula as the observer**.
- Prefer a small faithful Kripke model over a large informal story: φ is only as good as AP and R.
- A counterexample is a *proof of bug-in-the-model*; fix the model or the code, then re-check.

## Anti-patterns
- **Testing as verification**: passing tests does not entail AG ¬bad.
- **Unbounded data in the model**: integers/files without abstraction → infinite S; the 1999 algorithms assume finite S.
- **Ignoring the modelling gap**: SMV/SPIN success ≠ deployed-system success.

## Worked Example
Mutual exclusion sketch: two processes with states {idle, trying, cs}. Bug if both in cs. Property AG ¬(cs1 ∧ cs2). If the lock is forgotten, the checker returns a path idle,idle → trying,idle → trying,trying → cs,trying → cs,cs. That path *is* the debug script.

## Key Takeaways
1. Model checking is decision, not search for a proof term.
2. Negative answers come with traces; use them.
3. Explosion is expected; later chapters are mitigation, not optional extras.
4. Finite S is a modelling obligation, not a theorem.

## Connects To
- **Ch 2**: how to build M.
- **Ch 4–7**: how to decide M ⊦ φ.
- **Ch 8–13**: how to survive |S|.
