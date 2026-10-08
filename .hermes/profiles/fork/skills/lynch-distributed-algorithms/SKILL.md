---
name: lynch-distributed-algorithms
description: "Use when reasoning about atomicity, consensus, failure."
related_skills:
  - sipser-theory-computation
  - clrs-algorithms
  - shoham-multiagent-systems
  - huth-ryan-logic
  - information-flow-control
book_type: technical
depth: study
---

# Lynch — Distributed Algorithms (I/O automata, consensus, failures)

Knowledge base from Nancy Lynch & Boaz Patt-Shamir, *Distributed Algorithms* lecture notes for MIT 6.852 (Fall 1992; MIT/LCS RSS series, January 1993). These notes are the course that became Lynch, *Distributed Algorithms*, Morgan Kaufmann, 1996. Formal model: I/O automata. Timing: synchronous, asynchronous, partially synchronous. Failures: crash-stop, omission, Byzantine. Proof: invariants, simulations, indistinguishability.

Load [cheatsheet.md](cheatsheet.md) for theorems; [glossary.md](glossary.md) for terms; [patterns.md](patterns.md) for proof and Hermes patterns; [chapters/](chapters/) for lecture-grouped detail.

---

## When to use

- Atomic writes / WAL / checkpoints: safety predicate “no partial state visible” (atomicity of objects, serialization points).
- Concurrent writers on shared state (cron WAL contention): shared register + mutex or atomic RMW/swap.
- Cold-start / gate-audit: liveness (“eventually returns”) under a fairness assumption — not guaranteed by safety alone.
- Skill-router / lock arbitration: leader election (unique winner, UID or timestamp-ballot).
- Multi-agent agreement under crash or Byzantine components: consensus + FLP barrier.
- Crash recovery, 2PC/3PC, Paxos ballots, clock/order arguments, self-stabilizing repair.

Do **not** treat “it usually works” as a liveness proof. FLP: no deterministic 1-crash-resilient consensus in fully asynchronous message-passing.

---

## Core model: I/O automaton

An I/O automaton *A* is `(sig(A), states(A), start(A), trans(A), part(A))`:

- **Action signature** `sig(A) = (in, out, int)` — pairwise disjoint. External = in ∪ out. Locally-controlled = out ∪ int.
- **Input-enabled:** every input is enabled in every state (the automaton cannot block the environment).
- **Transitions:** `trans(A) ⊆ states × acts × states`.
- **Partition** `part(A)`: countable equivalence classes of locally-controlled actions — the fairness units (one class ≈ one sequential component).

**Execution fragment:** alternating states and actions `s0, π1, s1, π2, …` with each `(si, πi+1, si+1) ∈ trans`. An **execution** starts in `start(A)`.

| Projection | What it keeps |
|---|---|
| schedule | actions only |
| behavior / **trace** | external actions only |
| fair behavior | behavior of a fair execution |

**Composition:** identify output π of one automaton with input π of others; they fire simultaneously. Restrictions: internals disjoint from others’ actions; outputs pairwise disjoint; each action belongs to finitely many components.

**Fair execution** (wrt each class *C* of `part(A)`):
1. Finite ⇒ no action of *C* enabled in the last state.
2. Infinite ⇒ infinitely many *C*-events, **or** infinitely many states where *C* is disabled.

A **problem** is a set *P* of allowable external behaviors. *A* **solves** *P* if every fair behavior of *A* is in *P*.

---

## Safety vs liveness (always split)

- **Safety:** prefix-closed. “Nothing bad happens.” Mutual exclusion, agreement, atomicity, well-formedness. Proved by **invariants** (induction on reachable states) or **forward simulations**.
- **Liveness:** “something good eventually happens.” Termination, lockout-freedom, wait-freedom, “gate-audit returns.” Requires **fairness** (or a timed boundmap). Safety proofs never imply liveness.

**Invariant assertion:** predicate *I* true in all reachable states. Prove: true in `start`; preserved by every transition.

**Forward simulation** *f* ⊆ states(*A*) × states(*B*) (same external signature):
1. Start states of *A* relate to start states of *B*.
2. If `s --π--> s'` in *A* and `(s,u) ∈ f`, there is a finite fragment of *B* from *u* to some `u'` with `(s',u') ∈ f` whose **external** projection equals that of π.

Then fair behaviors of *A* ⊆ fair behaviors of *B*. Use for hierarchical refinement (implementation ≤ spec).

**Modular rule:** if each component **preserves** prefix-closed *P* (it is never the first to violate *P*), a closed composition implements *P*.

---

## Timing models

| Model | Steps | Extra power |
|---|---|---|
| **Synchronous** | lock-step rounds | flooding, *f*+1-round crash consensus, Byzantine with *n* > 3*f* |
| **Asynchronous** | arbitrary interleaving | IOA fairness only; FLP impossibility |
| **Partially synchronous** (MMT timed automata) | boundmap *b* assigns `[bℓ(C), bu(C)]` to each class | lower **and** upper bounds restrict interleavings; timeouts legal |

Logical time (Lamport clocks) is **not** real time: it induces a total order extending causality (`send < receive`, per-process order). Reordering theorem: there is an equivalent execution in which logical order = real order.

---

## Failures

| Kind | Behavior | Typical threshold |
|---|---|---|
| **Crash-stop** | process halts; may send a subset of a round’s messages | sync consensus in *f*+1 rounds |
| **Omission / lost messages** | messengers fail (coordinated attack) | **impossible** even for 2 nodes |
| **Byzantine** | arbitrary state and messages | *n* > 3*f* necessary and sufficient (sync, oral messages) |
| **Crash + recovery** | Paxos-style: durable ballot state | agreement always; termination if a unique originator + majority live “long enough” |

**Coordinated attack / two generals:** agreement + weak validity with possible message loss is impossible (indistinguishability chain from all-1/all-delivered to a 0-decision execution).

---

## Consensus — the barrier and the escapes

Interface: `init_i(v)` / `decide_i(v)`.

- **Agreement:** no two different decision values.
- **Validity:** if all inputs = *v*, decide *v* (variants exist; commit validity is stronger on 0).
- **Termination:** fair (or 1-fair) executions decide.

**FLP (Fischer–Lynch–Paterson):** no deterministic 1-resilient consensus protocol in asynchronous reliable networks (even with atomic broadcast, complete graph, FIFO). Proof: bivalent initial execution exists; bivalence can be preserved by delaying one process (valency + commutativity of disjoint steps).

**Escapes from FLP:**
1. **Synchrony** (or partial synchrony / timeouts).
2. **Randomization** (Ben-Or: terminate with probability 1; notes use *n* ≥ 7*f*+1).
3. **Stronger objects** than read/write: RMW/compare-and-swap **can** implement consensus; read/write **cannot** (even 1 crash).
4. **Weaker termination** (Paxos, 2PC): agreement+validity always; liveness only under extra conditions (unique leader, majority up).

**Paxos (notes “Parliament of Paxos”):** ballots `(t,i)`; originator collects majority history, chooses value of highest prior YES (else own init), then majority YES ⇒ decide. Agreement by intersecting majorities. Duelling originators can livelock.

**Commit:** validity “any 0 ⇒ must abort.” 2PC: weak termination (coordinator crash blocks). 3PC: extra phase so the coordinator does not decide commit until others know the intent — strong termination in the crash model of the notes.

---

## Shared memory: mutex, registers, atomicity

**Mutex regions:** Remainder → Trying → Critical → Exit. Safety: ≤1 in *C*. Liveness: deadlock-freedom (someone enters) vs lockout-freedom (each trying process enters) vs *k*-bounded bypass.

Peterson (2-process): `level[i]:=1; turn:=i; wait until level[j]=0 or turn≠i`. Tournament lifts to *n*.

**Atomic object:** (1) preserves well-formedness (invoke/response alternate per line); (2) **atomicity:** serialization points inside each completed operation’s interval so the sequential spec is met; incomplete ops may be omitted or completed after invoke; (3) fairness ⇒ responses. **Wait-freedom:** fairness to *i* alone ⇒ *i*’s invocation returns (no helping required from others).

Register hierarchy (single-writer first):

```
safe  --read overlapping write may return garbage
  ↓
regular -- overlapping read returns old or new (can invert consecutive reads)
  ↓
atomic  -- linearizable; no new-then-old
```

Safe binary SR/SW registers **suffice** (wait-free constructions) to build multi-reader multi-writer *k*-ary atomic registers.

Hermes mapping: an atomic file write is a serial spec “write then read sees whole value”; a safety invariant *I* ≡ “no reader observes a torn buffer.”

---

## Hermes applications (mandatory)

1. **Atomic writes → IOA safety.** Formalize “no partial state visible” as: every trace, after hiding internals, is a prefix of the serial write/read spec. Prove *I* by induction on transitions; internals (fsync, rename) are `int` actions not in the trace.
2. **Cron WAL contention → concurrent writers on a register.** Many fair classes writing one object. Mutex (critical section around WAL append) or atomic RMW/swap (compare-and-set of the log head). Regular registers are **not** enough if a reader must not see inverted entries.
3. **Gate-audit cold-start → liveness.** Spec is “eventually `result` output.” Needs a fairness assumption on the audit class (or a timed upper bound). A safety-only audit that may wait forever for a lock is **not** a solution.
4. **Skill router → leader election.** Unique winner among competing routes. LCR/HS if there is a total order on IDs; Paxos/ballot if processes may crash. Safety: at most one leader in any reachable state. Liveness: some leader under fairness (or unique originator).

---

## Decision procedure

1. Name the **model**: sync / async / timed; shared memory vs messages.
2. Name **failures**: none / crash / omission / Byzantine / recovery.
3. Split the claim into **safety** (invariant or simulation) and **liveness** (fairness or boundmap).
4. If the claim is async crash-resilient consensus with read/write or messages only → **impossible** (FLP / Loui-Abu-Amara). Change model, add randomness, or weaken termination.
5. If the claim is atomicity of a write → pick serialization points; check overlapping readers.
6. If the claim is “eventually” → exhibit the fair class that must take steps; do not cite a safety invariant.

---

## Chapter map

| File | Lectures | Contents |
|---|---|---|
| [chapters/01-models-and-io-automata.md](chapters/01-models-and-io-automata.md) | 1, 12–13 | timing models, IOA, executions, traces, fairness, composition |
| [chapters/02-safety-liveness-proofs.md](chapters/02-safety-liveness-proofs.md) | 1, 9, 13 | invariants, simulations, modular/hierarchical proofs |
| [chapters/03-leader-election.md](chapters/03-leader-election.md) | 1–2, 17–18 | LCR, Hirschberg–Sinclair, Peterson ring, lower bounds |
| [chapters/04-sync-network-algorithms.md](chapters/04-sync-network-algorithms.md) | 2–3 | BFS, shortest paths, MST, MIS |
| [chapters/05-failures-and-byzantine.md](chapters/05-failures-and-byzantine.md) | 4–6 | coordinated attack, crash-stop, Byzantine *n*>3*f* |
| [chapters/06-commit-protocols.md](chapters/06-commit-protocols.md) | 7 | 2PC, 3PC, message lower bounds |
| [chapters/07-mutual-exclusion.md](chapters/07-mutual-exclusion.md) | 8–9, 11, 16, 21–22 | Dijkstra, Peterson, bakery, Burns, Ricart–Agrawala |
| [chapters/08-atomic-objects-and-registers.md](chapters/08-atomic-objects-and-registers.md) | 10, 14–17 | atomic objects, snapshots, safe/regular/atomic, CTS |
| [chapters/09-consensus-impossibility.md](chapters/09-consensus-impossibility.md) | 12, 25 | RW consensus impossible; FLP |
| [chapters/10-randomized-and-paxos.md](chapters/10-randomized-and-paxos.md) | 4, 25 | randomized coordinated attack, Ben-Or, Paxos |
| [chapters/11-async-networks-synchronizers.md](chapters/11-async-networks-synchronizers.md) | 18–20 | GHS MST, Awerbuch synchronizers |
| [chapters/12-logical-time-and-clocks.md](chapters/12-logical-time-and-clocks.md) | 21, 28 | Lamport time, snapshots, clock sync pointers |
| [chapters/13-self-stabilization.md](chapters/13-self-stabilization.md) | 23–24 | Dijkstra, local checking/correction, reset |
| [chapters/14-partial-synchrony.md](chapters/14-partial-synchrony.md) | 28, A–B | MMT timed automata, Stenning/ABP, crash recovery |

---

## Anti-patterns

- Proving only an invariant and claiming the algorithm “completes.”
- Assuming a unique leader in async crash-prone systems without a ballot/election protocol.
- Using regular-register semantics where linearizability is required (inverted reads).
- Treating 2PC as strongly terminating.
- Claiming async deterministic consensus “because messages are reliable.” FLP assumes reliable FIFO channels.
- Confusing crash-stop (*f*+1 rounds, any *n*>*f*) with Byzantine (*n*>3*f*).
