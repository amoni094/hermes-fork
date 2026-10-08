# Chapter 3: Temporal Logics

## Core Idea
CTL talks about the computation *tree* (branching); LTL talks about *paths* (linear); CTL* contains both. Path quantifiers A/E combine with X, F, G, U.

## Frameworks Introduced
- **CTL syntax** (state formulas):
  φ ::= p | ¬φ | φ∨φ | EX φ | EG φ | E[φ U φ]
  Derived: AX φ = ¬EX ¬φ, EF φ = E[true U φ], AG φ = ¬EF ¬φ, AF φ = ¬EG ¬φ, A[φ U ψ] = ¬E[¬ψ U (¬φ ∧ ¬ψ)] ∧ ¬EG ¬ψ.
  - When to use: nested path quantifiers, reset properties, “from every state there exists a recovery”.
- **LTL syntax** (path formulas, then required of all paths from s):
  ψ ::= p | ¬ψ | ψ∨ψ | X ψ | ψ U ψ
  F ψ = true U ψ, G ψ = ¬F ¬ψ.
  - When to use: safety G ¬bad, response G(req → F ack), persistence FG p.
- **CTL***: state formulas and path formulas mixed; E ψ and A ψ wrap path formulas. CTL and LTL are proper, incomparable fragments.

## Key Concepts
- **A** — on *all* paths from this state; **E** — on *some* path.
- **X** — next state; **F** — some future state; **G** — all future states (including now); **U** — until (strong: ψ must occur).
- **Until vs weak until**: φ W ψ = G φ ∨ φ U ψ (ψ not required).
- **Incomparable examples**: AG EF restart is CTL not LTL; FG stable is LTL not CTL.
- **ACTL**: CTL with only universal path quantifiers (and ¬ only on atoms) — preserved by simulation (Ch 9–11).

## Mental Models
- Use **CTL** when the claim is about *existence of a branch* (can recover, can schedule).
- Use **LTL** when the claim is about *every infinite run* (no crash, every request served).
- If you need both, either split into two checks or step up to CTL*.

## Anti-patterns
- Writing AF AG p and claiming it means “eventually always p” (that is LTL FG p).
- Mixing a naked U without A/E in a CTL checker.
- Using X on a stuttering model you later POR-reduce (X is not stutter-invariant).

## Worked Example
Cron no-contention (CTL):
AG (writer_active → AX ¬concurrent_writer)
Branching next-state: after any writer-active state, *every* successor has no concurrent writer.

Skill-router response (LTL):
G (skill_queried → F skill_returned)
Linear: on every run, a query is followed later by a return — needs fairness if the router can be starved.

## Key Takeaways
1. CTL = A/E glued to X/F/G/U; no free mixing.
2. LTL has no E; implicit A on infinite traces.
3. Classify safety (G ¬bad) vs liveness (F / AF) *before* picking the logic.
4. Stutter-invariant fragments (no X) survive POR.

## Connects To
- **Ch 4**: CTL labelling.
- **Ch 7**: LTL automata + fairness.
- **Cheatsheet**: Hermes formulas.
