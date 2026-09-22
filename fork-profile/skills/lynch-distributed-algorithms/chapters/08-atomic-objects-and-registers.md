# Atomic objects and registers (Lectures 10, 14–17)

## Atomic objects

Architecture: *n* user lines into an object; concurrency **across** lines, sequential **per** line.

Interface: invocations are inputs (`read_i`, `write_i(v)`, `insert_i`, …); responses are outputs (`read-respond_i(v)`, `write-respond_i`, …). Finer atomicity than a single shared-variable step — operations have duration.

**Property 1 — well-formedness.** On each line *i*, invocations and responses alternate, starting with an invocation. Users preserve this; the object must preserve it. Process *i* takes steps only while an invocation is active on line *i*.

**Serial specification *S*.** A sequential object: a state machine mapping a sequence of invocations to responses (ordinary ADT). Example for a R/W register initially 0:

```
read1, read-respond1(0), write2(8), write-respond2, read1, read-respond1(8)
```

**Property 2 — atomicity (linearizability).** For every well-formed (finite or infinite) execution, one can choose:

1. For each **completed** operation, a **serialization point** inside its active interval (between invoke and response).
2. A subset *T* of **incomplete** operations, each given a serialization point after its invoke and a matching response.

Shrinking those operations to their serialization points (and discarding incomplete ops not in *T*) yields a sequence in *S*.

Incomplete operations may be treated as if they happened or as if they never happened — but if a later read sees the value, the write must be in *T*.

**Property 3 — liveness.** Fairness ⇒ every invocation gets a response.

**Wait-freedom.** Fairness to process *i* **alone** (others may stall) ⇒ *i*’s invocation returns. Composition of wait-free objects remains wait-free (Lecture 14). Stronger than deadlock-freedom; incomparable with lockout-freedom of mutex (mutex cannot be wait-free for the *critical section* itself — the resource is exclusive).

## Atomic snapshots

Read an array of *n* registers “at once” (a point in the trace). Unbounded algorithm: collect twice, retry on change, use sequence numbers. Bounded-register constructions exist (Afek et al. style; notes Lecture 10.2.3).

## Lemma for showing atomicity (multi-writer)

A standard sufficient condition (Lecture 15): order operations by last-writer timestamps so that

- the order extends real-time precedence (if *op1* finishes before *op2* starts, *op1* < *op2*);
- reads return the value of the last preceding write in that order.

Then serialization points exist.

## Concurrent timestamp systems (CTS)

Abstract object issuing labels that can be compared, with bounded domains, wait-free. Used to replace unbounded bakery tickets and to build multi-writer registers from single-writer ones (Israeli–Li / Dolev–Shavit style; notes Lecture 14–15).

## Safe, regular, atomic registers (Lamport)

Single-writer (writes never overlap). Any non-overlapping read returns the latest completed write (or initial value). They differ **only** when a read overlaps writes:

| Class | Overlapping read may return |
|---|---|
| **safe** | *any* value in the domain (garbage) |
| **regular** | the value before the overlapping writes, or the value of one of them (no garbage; **new-then-old** allowed across consecutive reads) |
| **atomic** | as if the read and writes linearized; forbids new-then-old |

```
  W0 ---- W1 ---- W2 ---- W3 ---- W4
              R1==============
                   R2====
```

Regular: *R1* may return any of W0…W4; *R2* any of W1…W3. Consecutive regular reads may invert.

## Construction ladder (wait-free)

Start from **safe binary single-reader single-writer** registers, build:

1. (prior) safe *k*-ary, etc.
2. Binary **regular** from binary **safe** (write a flag; read twice).
3. *K*-ary regular from binary regular (unary or binary encoding with care).
4. 1-reader *K*-ary **atomic** from regular (sequence numbers / Kirousis–Spirakis–Tromp / Lamport).
5. Multi-reader atomic from 1-reader.
6. Multi-writer atomic using CTS or snapshot (Lecture 15).

Modularity: each layer is an IOA satisfying the next spec; wait-freedom composes.

## Hermes: atomic writes

Serial spec of a file object:

```
write(v) → ack;  read → v          # after a completed write
read overlapping write → old or new, never a mix of bytes
```

Implementation via `write tmp; fsync; rename` is a simulation: the rename is the serialization point. Internal `int` actions (copying bytes) are hidden; traces never contain a “partial file” read if rename is atomic on that FS.

**Cron WAL with concurrent writers** is a **multi-writer register** (or a queue object). Regular semantics can invert two appends — not acceptable for a log. Need atomic/linearizable append: mutex around the write, or CAS of the head pointer (RMW).
---
