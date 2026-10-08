# Self-stabilization (Lectures 23–24; Varghese)

## Idea

A system is **self-stabilizing** (Dijkstra) if, starting from an **arbitrary** global state (corruption, crash-recovery with garbage, uninitialized memory), every fair execution eventually reaches a legal set *L* and stays there.

**Door closing / domain restriction:** once in *L*, transitions stay in *L* (safety of the legal set). Stabilization is the liveness part: *eventually* *L*.

Attractive for networks: no global reset, no distinguished “initial” state after a Heisenbug.

**Criticisms (notes):** may take long; during convergence, safety does not hold; some problems (termination) sit awkwardly with “always keep running”; finite-state vs unbounded counters.

## Definitions

**Execution-based:** every execution from any state has a suffix in which a state invariant *I* holds forever.

**External-behavior-based:** every (fair) behavior from any state has a suffix that is a legal behavior of the spec. This is the IOA-friendly form: internals may be garbage as long as the **trace** eventually looks like the spec.

The notes discuss which definition is right when the environment also misbehaves; typically assume the environment becomes well-formed.

## Dijkstra’s shared-memory examples

Token-ring: *n* processes, each a counter modulo *K* (large *K*). Privileged process (token) is defined by a local predicate on self and neighbor. Exactly one privilege in legal states. From any state, fair execution reaches a unique token.

- **Local checking and correction:** a predicate *P_e* on each link/edge subsystem; global *I* = ∧ *P_e*. If every *P_e* is locally checkable (the two endpoints can see *P_e*) and locally correctable, a transformer yields a stabilizer (Local Correction Theorem).
- **Counter flushing:** a wave of increasing counters flushes old values off the ring.

## Message-passing model (notes)

Topology, links, and nodes as IOA. Links may start with garbage packets. Local predicates on **link subsystems**.

**Local Correction Theorem:** if a spec is locally checkable and locally correctable, there is a transformer (local snapshots + local resets) producing a self-stabilizing implementation. Intuition: snapshot the neighborhood; if the local predicate fails, reset that subsystem without necessarily resetting the world.

**Timer flushing:** in real networks, bound packet lifetime so old packets die; then local checking is sound.

## Stabilizing reset and synchronizers (Lecture 24)

A reset protocol that is itself self-stabilizing: from any state, eventually a global “new epoch” occurs and all nodes agree they have reset. Unbounded epoch numbers simplify the proof; bounded pulse numbers need extra wrapping care.

Application: a **self-stabilizing synchronizer** (network pulses) built on reset.

Stabilization vs termination: a terminating algorithm left in its final state is *not* stabilizing (a perturbation is not repaired). The usual fix is to keep a silent cycle that re-checks.

## Hermes

- Skill library / memory store after a killed write: do not assume start states; run a local checker (`I` = “JSON parses and schema holds”) and correct (delete/rebuild) rather than trusting the file.
- Session recovery: a reset epoch number on the session id so stale tool results (old packets) are flushed — analogue of timer/counter flushing.
- Stabilization is **liveness from illegal states**; it does not replace the safety invariant once legal.
---
