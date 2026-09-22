# Glossary — Lynch Distributed Algorithms

**Action / event.** Named IOA transition label. An *event* is one occurrence in a sequence.

**Action signature.** Disjoint sets in/out/int. External = in∪out. Local = out∪int.

**Agreement.** All (nonfaulty) decision values equal.

**Atomic object / linearizability.** Operations appear to occur at a serialization point inside their interval; the resulting sequential history meets the ADT spec.

**Atomic register.** Linearizable read/write object. Forbids new-then-old reads.

**Behavior / trace.** Subsequence of an execution consisting of external actions.

**Bivalent / univalent / 0-valent.** A finite execution is 0-valent if every extension that decides, decides 0; bivalent if both 0 and 1 remain possible. FLP engine.

**Boundmap.** In MMT timed automata, `[lower,upper]` per partition class for time between turns.

**Broadcast (notes FLP model).** Atomic send of the same message to all others.

**Byzantine.** Arbitrary process behavior, including conflicting messages.

**Commit problem.** Consensus with abort-contagious validity (any 0 ⇒ decide 0).

**Composition.** Identify outputs with matching inputs; simultaneous occurrence. Internals stay private; outputs have unique controllers.

**Coordinated attack / two generals.** Consensus with possible message loss. Impossible deterministically.

**Crash-stop / stopping failure.** Process halts; last round may send a subset of messages.

**Critical / trying / remainder / exit.** Mutex regions C, T, R, E.

**CTS.** Concurrent timestamp system: wait-free bounded labels with comparison.

**Deadlock-freedom.** If someone is trying and nobody is in C, someone later enters C.

**EIG tree.** Exponential-information-gathering tree for crash/Byzantine flooding (*f*+1 levels).

**Enabled.** An action has a transition from the current state. Inputs are always enabled (input-enabled).

**Execution.** Alternating states and actions starting from a start state.

**Fair execution.** Every partition class infinitely often takes a step or is disabled (finite: all classes disabled at the end).

**Fairness class / part(A).** Equivalence class of locally-controlled actions; one sequential component.

**FLP.** Fischer–Lynch–Paterson: no deterministic 1-crash-resilient async consensus.

**Forward simulation.** State relation showing traces of implementation ⊆ traces of spec.

**Fragment (GHS).** Connected subtree of the MST being built.

**Happens-before (→).** Transitive closure of per-process order and send-before-receive.

**Indistinguishability (α ~_i β).** Process *i* has the same local view (init + receipts). Implies identical local behavior.

**Input-enabled.** Cannot block inputs.

**Invariant.** Predicate true in all reachable states; proved by induction.

**LCR.** LeLann–Chang–Roberts ring election: forward larger UIDs; own UID returning ⇒ leader.

**Lockout-freedom.** Every trying process eventually enters C.

**Logical time.** Lamport clock assignment satisfying uniqueness, per-process increase, send < receive, finite past.

**MOE.** Minimum outgoing edge of a GHS fragment; blue-rule edge, in the MST.

**Oral messages.** Unauthenticated Byzantine model (*n*>3*f*).

**Paxos ballot.** Id `(t,i)`; majority promise + majority YES ⇒ decide.

**Preserve (a property P).** Never the first to violate prefix-closed P.

**Prefix-closed.** Every prefix of a sequence in P is in P. Safety properties.

**Regular register.** Overlapping read returns old or some overlapping write’s value; consecutive reads may invert.

**RMW.** Read-modify-write (TAS, F&A, CAS). Implements consensus; R/W does not.

**Safe register.** Overlapping read may return any domain value.

**Schedule.** Action subsequence of an execution (includes internals).

**Serialization point.** Instant inside an operation interval at which it appears to take effect.

**Serial specification.** Sequential ADT for an object.

**Stabilization.** From arbitrary states, eventually legal, and then remains legal.

**Synchronizer.** Layer implementing pulses/rounds on an async network (Awerbuch α, β, γ).

**Validity (consensus).** All inputs *v* ⇒ decide *v*. Commit validity is stronger on 0.

**Wait-freedom.** Fairness to *i* alone ⇒ *i*’s operation completes.

**Well-formedness (objects).** Per line, invoke/response alternate, starting with invoke.

**1-fair.** All but at most one process, and all channels, are fair. FLP termination assumption.
---
