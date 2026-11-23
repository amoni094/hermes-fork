# Logical time, snapshots, clocks (Lectures 21–22, 28)

## Lamport logical time

No real clocks in the async IOA network. Assign to every event (send, receive, internal, external) a time in a total order (ℕ or ℝ, plus process-id tie-breakers) such that:

1. Distinct events get distinct times.
2. Events at a single node receive strictly increasing times in occurrence order.
3. For every message, `ltime(send) < ltime(receive)`.
4. Only finitely many events have time < *t* (no accumulation).

**Reordering theorem.** Given execution α and such an `ltime`, there is an execution α′ with α↾*i* = α′↾*i* for every node *i*, in which the real order of events is the `ltime` order. Programming against logical time “looks like” programming against real time, **locally**.

Broadcast may share one logical send-time; all receives are later. Reordering still holds.

### Algorithm (Lamport clocks)

Each node has integer `clock`, increased at every local event. Logical time = `(clock, index)`.

- On send/broadcast: increment, stamp the message with the new clock.
- On receive: `clock := max(clock, stamp) + 1` (or `max(clock+1, stamp+1)`).

Properties 1–4 hold if increments are at least 1.

**Happens-before** `→` is the smallest transitive relation containing per-process order and send-before-receive. Lamport clocks satisfy `e → e′ ⇒ ltime(e) < ltime(e′)` but **not** the converse (concurrent events may still get ordered). Vector clocks (not emphasized in these notes) recover concurrency.

### Applications in the notes

- Totally ordered multicast / shared-memory simulation: execute operations in `ltime` order.
- Mutex: Ricart–Agrawala uses `(clock, i)` as the request priority (ch. 07).

## Stable property detection

A property of global states that, once true, stays true (termination, deadlock, lost token).

**Dijkstra–Scholten** termination for diffusing computations: a tree of “debts” / missing acks; root detects termination when the tree is empty.

**Chandy–Lamport snapshots:** record local state and in-flight messages along a consistent cut (no message received in the snapshot whose send is not). Implemented by a marker wave. The recorded cut is a global state that **could have** occurred; for stable properties, if the property holds in the snapshot it holds in the real present.

## Clock synchronization (Lecture 28, pointers only)

The 6.852 extra lecture cites, without full proofs:

- Lamport–Melliar-Smith (Byzantine clock sync, averaging).
- Lundelius–Lynch: *n* processes, unbounded drift-free clocks, uncertainty *ε* on delays ⇒ optimal skew *(1−1/n)ε* (cannot do better).
- Fischer–Lynch–Merritt: lower bounds with faults.

In the **MMT timed** model (ch. 14), clocks are ordinary locally-controlled classes with a boundmap on how they may advance. Synchronization is a safety bound on `|clock_i − clock_j|` plus a liveness/accuracy bound vs real time.

## Hermes

- Session events get a Lamport stamp so concurrent tool traces can be merged into a linear log without claiming real-time order.
- Gate-audit “consistent cut”: snapshot in-flight tools + files; do not include a result whose invoke is missing (would be an inconsistent cut).
- Do not use wall-clock timestamps as happens-before; NTP-skewed hosts violate condition 3 unless you also carry Lamport stamps.
---
