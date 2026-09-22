# Models and I/O automata (Lectures 1, 12–13)

Source: Lynch & Patt-Shamir, MIT 6.852 Fall 1992 notes (basis of Lynch, *Distributed Algorithms*, 1996).

## Why several models

There is no single accepted model covering all of distributed computing. Shared memory ≠ message passing; lock-step ≠ asynchronous. Lynch organizes first by **timing**, then by **IPC**, then by **problem**, then by **failures**.

## Timing

**Synchronous.** Components take steps simultaneously. Execution proceeds in rounds: in round *k*, every non-failed process (1) applies `msgs(i)` to its state, (2) sends those messages to neighbors, (3) receives the round’s incoming messages, (4) applies `trans` to obtain the next state. Lost or delayed messages are *not* in the basic sync model; they are added as a failure mode.

**Asynchronous.** Separate components take steps in arbitrary order. No bound relating one process’s speed to another’s. Fairness (below) is the only progress assumption.

**Partially synchronous (timing-based).** Restrictions on relative timing exist but execution is not lock-step. Processes may have clocks, timeouts, and lower/upper bounds on step or delivery time. Formalized later as **timed automata / MMT boundmaps** (ch. 14). Upper bounds *alone* do not change the set of untimed executions; **lower and upper** bounds together restrict interleavings.

IPC split: **shared memory** (processes + variables) vs **message-passing** (nodes + channels).

## Informal synchronous network

Graph *G = (V,E)*, |V|=*n*. Process *i* is a state machine:

- `states(i)`, nonempty `start(i)`
- `msgs(i): states(i) × out-nbrs(i) → M ∪ {null}`
- `trans(i)` maps (state, incoming message tuple) to a new state

Dummy output nodes are sometimes used for “leader” or “decide” actions.

## I/O automaton (Lynch–Tuttle)

Universal set of **actions**. An occurrence of an action in a sequence is an **event**.

**Action signature** *S* = ordered triple of disjoint sets:

```
in(S), out(S), int(S)
ext(S)   = in(S) ∪ out(S)
local(S) = out(S) ∪ int(S)
acts(S)  = in ∪ out ∪ int
extsig(S) = (in(S), out(S), ∅)
```

- Inputs: not under *A*’s control (environment).
- Outputs: under *A*’s control **and** externally observable.
- Internals: under *A*’s control, hidden.

**I/O automaton** *A*:

1. `sig(A)` — action signature
2. `states(A)` — not necessarily finite
3. `start(A) ⊆ states(A)`, nonempty
4. `trans(A) ⊆ states(A) × acts(sig(A)) × states(A)`
5. **Input-enabling:** ∀ state *s*, ∀ input π, ∃ *s′* with `(s, π, s′) ∈ trans(A)`
6. `part(A)` — equivalence relation on `local(sig(A))` with at most countably many classes

`(s, π, s′)` is a **step**. π is **enabled** in *s*. Input-enabling means the module cannot refuse environment actions.

### Executions, schedules, traces

**Execution fragment:** finite `s0, π1, s1, …, πn, sn` or infinite `s0, π1, s1, …` with each consecutive triple a step.

**Execution:** fragment beginning in a start state. `execs(A)`, `finexecs(A)`.

**Reachable state:** last state of a finite execution.

**Schedule** `sched(α)`: the action subsequence of execution (fragment) α.

**Behavior / trace** `beh(α)`: the **external** action subsequence.

Sets: `scheds(A)`, `behs(A)`, and finite variants.

Traces are the interface: two automata with the same fair traces are indistinguishable to the environment.

## Composition

Identify output π of one component with input π of every component that has π as input; they occur **simultaneously**. Components without π stutter.

Restrictions (strongly compatible collection):

1. Internals of *A* disjoint from actions of *B* (internals are unobservable).
2. Outputs of distinct components disjoint (at most one controller per action).
3. Each action belongs to only finitely many components (needed for countable products / dynamic process creation).

The composition’s signature is determined by the component signatures. Composition is associative (up to isomorphism) and has good **projection** properties: a schedule of the composition projects to a schedule of each component; conversely, compatible component schedules fuse to a composition schedule.

Each component partition class remains a class of the composition — fairness is preserved under composition.

## Fairness

Each class *C* of `part(A)` is a fairness unit (one sequential “task” or process).

Execution α is **fair** iff for every class *C*:

1. If α is finite, no action of *C* is enabled in the last state.
2. If α is infinite, either α contains infinitely many events from *C*, or infinitely many states in which *C* is disabled.

Intuition: infinitely often the scheduler offers *C* a turn; either *C* takes a step or *C* has nothing to do.

`fairexecs(A)`, `fairscheds(A)`, `fairbehs(A)`.

**Compositionality of fairness (notes Propositions 9–11):** fair executions of the composition project to fair executions of components; compatible fair component executions fuse. Therefore one may reason about fair behavior **modularly**.

This is **not** wait-freedom. Ordinary IOA fairness is fairness to **all** classes. Wait-freedom is fairness to **one** process implying that process’s operations complete (ch. 08).

## Problem specification

A problem is a set *P* of sequences over an external signature. Automaton *A* **implements / solves** *P* if `fairbehs(A) ⊆ P` (sometimes finite behaviors for safety-only specs).

Typical split:

- Safety part of *P* is **prefix-closed**.
- Liveness part talks about fair (or timed-admissible) infinite behaviors.

**Preserves *P*:** module *M* is never the first to violate prefix-closed *P*. If the environment has not yet broken *P*, *M*’s next output does not break *P*. Used to state well-formedness of objects and mutex users.

## Shared-memory systems as IOA

Two presentations:

1. **Instantaneous memory.** A read or write of a variable is a single locally-controlled step of a process. The memory is not a separate automaton.
2. **Object model.** Memory cells are automata with invoke/response interface (`read_i`, `read-respond_i(v)`, …). Concurrency of operations on different lines is explicit. Atomicity is a property of traces (ch. 08).

There is a modular transformation from instantaneous-access systems to systems using atomic objects, preserving external behavior (Lecture 13).

## Hermes notes

- A Hermes **tool call** is an output; the **tool result** is an input. Input-enabling: the agent cannot refuse the result, only choose not to wait (liveness is separate).
- A **skill** composed of plugins should be modeled as compatible IOA: disjoint outputs, internals hidden, fairness per worker class.
- Traces, not internal queues, are what correctness claims should quantify over.
---
