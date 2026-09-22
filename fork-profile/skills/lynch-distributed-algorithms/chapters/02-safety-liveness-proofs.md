# Safety, liveness, invariants, simulations (Lectures 1, 9, 13)

## Safety vs liveness

**Safety.** Prefix-closed property of traces/executions. If a sequence violates it, some finite prefix already violates it. Examples: mutual exclusion, agreement, well-formed invoke/response, atomicity, “no torn write visible.”

**Liveness.** If a sequence violates it, every finite prefix can still be extended to satisfy it. Examples: eventual decision, deadlock-freedom, lockout-freedom, wait-freedom, “gate-audit eventually returns.”

Alpern–Schneider (background): every linear-time property is the intersection of a safety property and a liveness property. Lynch’s course uses automata + fairness rather than temporal logic as the primary vehicle; temporal logic is listed as the language specialized for liveness.

**Never prove liveness with an invariant alone.** Invariants are safety. Liveness needs fairness (or a timed upper bound on a class).

## Invariant assertions

An **invariant** *I* is a predicate on states true of every reachable state.

Proof by induction on executions:

1. **Base:** every `s ∈ start(A)` satisfies *I*.
2. **Inductive step:** if *I(s)* and `(s, π, s′) ∈ trans(A)`, then *I(s′)`.

Strengthen *I* until the inductive step goes through (the usual failure mode is an *I* that is true of reachable states but not inductive). Auxiliary variables are allowed in the proof automaton.

**Dijkstra mutex (assertional proof, Lecture 9):** an invariant relating `turn`, who is in trying/critical, and the shared array, implying |{i : i in C}| ≤ 1. Running-time bounds need a separate variant (potential) argument, not just *I*.

**Indistinguishability** (sync proofs): executions α ~_i β if process *i* has the same initial state and receives the same messages in the same rounds. Then *i* behaves identically in α and β. Safety lower bounds (coordinated attack, Byzantine *n*≤3*f*, FLP) are chains of indistinguishable executions that force contradictory decisions.

## Modular decomposition

Reason about a composition by reasoning about components.

Let *P* be nonempty, prefix-closed, and mention no internals of *M*. *M* **preserves** *P* if: whenever β↾Σ ∈ *P*, π ∈ out(*M*), and β↾*M* is a finite behavior of *M*, then (β π)↾Σ ∈ *P*.

**Proposition (notes):** if every *A_i* preserves *P*, the composition preserves *P*.

**Closed automaton** (no inputs): if *A* preserves *P* then finite behaviors of *A*, projected to the alphabet of *P*, lie in *P*.

**Corollary:** if the *A_i* are strongly compatible, the composition is closed, and each *A_i* preserves the finite behaviors of problem *P*, then the composition implements *P* (safety).

This is the “users preserve well-formedness, object preserves well-formedness, composition is well-formed” pattern for atomic objects.

## Hierarchical decomposition / simulation

To show implementation *A* solves spec *B* (same external signature), exhibit a relation between states.

**Forward simulation** *f ⊆ states(A) × states(B)*:

1. If *s ∈ start(A)* then ∃ *u ∈ start(B)* with *(s,u) ∈ f*.
2. If *(s, π, s′) ∈ trans(A)* and *(s,u) ∈ f*, then there is a finite execution fragment of *B* starting at *u*, ending at some *u′* with *(s′,u′) ∈ f*, whose **external** action sequence equals that of π (so internals of *A* may match a (possibly empty) sequence of internals of *B*; an external of *A* must match the same external of *B*, possibly with internals around it).

Then every (fair) behavior of *A* is a (fair) behavior of *B*.

Backward simulations and history/prophecy variables exist in the full theory (Lynch/Vaandrager); the 6.852 notes emphasize forward simulations.

**Use:** replace an instantaneous register by an atomic register object; replace a spec of consensus by Paxos; replace a high-level mutex by Peterson.

## Liveness proof pattern

1. State the fairness assumption (which classes).
2. Assume toward contradiction a fair execution in which the good event never occurs.
3. Show some class *C* is enabled from some point on and never takes a step — contradiction to fairness.
4. Or exhibit a variant that decreases every time *C* takes a step and is bounded below.

**Timed analogue:** the boundmap’s upper bound *bu(C)* forces a step of *C* within that real-time interval whenever *C* stays enabled (ch. 14).

## Hermes patterns

| Claim | Proof tool |
|---|---|
| Atomic write never shows partial state | safety invariant + serialization points |
| WAL append is linearizable | forward simulation to a serial log automaton |
| Gate-audit returns | liveness under fairness of the audit class |
| Router eventually picks one skill | leader-election liveness, not just “at most one leader” |
| Plugin cannot corrupt another plugin’s trace | composition: internals disjoint, outputs disjoint |

**Preserve vs satisfy:** a worker that **preserves** well-formed JSON (never the first to emit torn output) is the right spec when the environment may already have sent garbage. Requiring *satisfy* would be too strong.
---
