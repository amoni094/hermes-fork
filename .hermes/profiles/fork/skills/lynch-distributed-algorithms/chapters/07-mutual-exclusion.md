# Mutual exclusion (Lectures 8–9, 11, 16, 21–22)

## Problem (shared memory)

*n* processes, one indivisible resource. Each process cycles:

```
        R (remainder)
       / \
      E   T (trying)
       \ /
        C (critical)
```

Interface (IOA): inputs `try_i`, `exit_i`; outputs `crit_i`, `rem_i`. Users preserve cyclic order; the protocol must preserve it too.

Read/write memory: a step is `read x` into local state or `write` a value determined by local state.

**Mutual exclusion (safety):** no reachable state has more than one process in *C*.

**Deadlock-freedom (liveness):** in a fair execution, if ≥1 process is in *T* and none in *C*, then later some process enters *C*. Similarly the exit region is vacated.

**Lockout-freedom (stronger liveness):** every process that enters *T* eventually enters *C*. *k*-bounded bypass: while *i* is in *T*, *j* enters *C* at most *k* times.

**No-starvation** in the notes is lockout-freedom.

## Dijkstra’s algorithm

*n*-process mutex with a shared `turn` and per-process flags, using only atomic read/write. Satisfies mutex + deadlock-freedom, **not** lockout-freedom (a fast process can bypass a slow one forever). Assertional proof in Lecture 9: invariant relating flags and `turn` to “at most one in *C*.” Time bound separate.

## Peterson’s two-process algorithm

```
shared: level[0..1] initially 0;  turn  arbitrary
pi:
  try_i
  level[i] := 1
  turn    := i
  wait until level[1-i] = 0  or  turn ≠ i
  crit_i
  exit_i
  level[i] := 0
  rem_i
```

**Mutex:** if *i* is before/in *C*, then either *j* is not in {at-wait, before-C, in-C} or `turn ≠ i`.

**Deadlock-freedom:** both cannot be stuck at wait (`turn` favors one); if the other never tries, its `level` becomes 0.

**Lockout-freedom:** 2-bounded bypass.

**Tournament:** a tree of 2-process Peterson locks; *n* processes, lockout-free, *O(log n)* crossings of 2-locks. Iterative (filter) algorithm is the other *n*-process lockout-free construction in Lecture 9.

## Burns; Lamport bakery

**Burns:** mutex with *n* bits, deadlock-free, not lockout-free; used in lower bounds.

**Bakery (Lamport):** process takes a ticket `number[i] = 1 + max_j number[j]`, then waits until it has the least (number, i) among contenders. Lockout-free. Uses unbounded tickets unless a concurrent timestamp system (CTS) is substituted (Lecture 14). With **safe** registers, bakery still works (reads overlapping writes may see garbage; the algorithm rereads).

## Number of registers

Mutex with read/write registers needs **at least *n* shared bits** in the deadlock-free case (Burns–Lynch style covering arguments). Two processes cannot mutex with one variable under the usual atomic R/W assumptions of the notes; three processes need more than two, etc.

## RMW mutex

A read-modify-write register (test-and-set, fetch-and-add, compare-and-swap) makes mutex trivial: TAS lock. Also enough for consensus (ch. 09) — strictly stronger than R/W.

## Network mutex

**Lamport logical time** (ch. 12) totally orders requests.

**Ricart–Agrawala (1981):** request to all; enter *C* after acks from all others; ack delayed if the holder has (earlier timestamp) priority. *n*−1 messages to enter, *n*−1 to exit.

**Carvalho–Roucairol:** cache permissions, fewer messages in the uncontended case.

**Burns–Lynch resource allocation; drinking philosophers:** generalize from one resource to a conflict graph. Dining philosophers is the special case of a cycle of single-resource conflicts.

## Hermes: cron WAL contention

Model WAL appenders as mutex users; the log is the resource *C*.

- Safety: at most one append in flight (no interleaved records).
- Deadlock-freedom: some waiter appends.
- Lockout-freedom: every cron job’s append completes — required if jobs have SLAs.
- Implementation: Peterson/bakery if only atomic R/W of a lock byte; TAS/CAS if the FS or DB provides RMW; else serialize via a directory lock.

Do not use a **regular** register as the lock byte: inverted reads can let two processes observe “free.”
---
