# Partial synchrony, timed automata, crash recovery (Lectures 26–28)

## Partial synchrony

Between lock-step sync and pure async. Processes have **some** timing information: bounds on step time, message delay, clock drift — possibly known, possibly only eventually holding (Dwork–Lynch–Stockmeyer; the extra lecture uses MMT).

Upper bounds **alone** do not shrink the set of untimed executions (they were already used for time-complexity analysis). **Lower and upper** bounds together forbid arbitrarily fast stuttering and arbitrarily slow steps, so timeouts become sound: “if I have not heard in *U* time, the other did not send (or is faulty),” provided a lower bound on the other side’s speed is also in the model — actually a timeout uses an **upper** bound on delivery+step of the other. If that upper bound is ∞ (pure async), timeouts are never safe.

## MMT timed automata (Merritt–Modugno–Tuttle; Lynch–Attiya presentation)

A **boundmap** *b* assigns to each class *C* of `part(A)` a closed interval `[bℓ(C), bu(C)] ⊆ [0,∞]` with *bℓ(C) ≠ ∞* and *bu(C) ≠ 0*.

**Timed automaton** = pair *(A, b)*.

**Timed sequence:** `s0, (π1,t1), s1, (π2,t2), …` with nondecreasing nonnegative times; infinite sequences have unbounded times.

**Admissible / timed execution:** the underlying untimed sequence is an execution of *A*, and for each class *C*:

- no two *C*-actions occur closer than *bℓ(C)* while *C* was enabled;
- *C* does not stay enabled for more than *bu(C)* without a *C*-action (unless *bu(C)=∞*).

Timed schedules/behaviors add the timestamps to traces.

**Simple mutex example:** trying class has an upper bound; one can prove an upper bound on time-to-enter, not merely eventual entry.

**Consensus in the timed model:** processes with step bounds `[c1,c2]`; question is time to agreement with *f* faults (not FLP, because the boundmap supplies the missing synchrony).

## Reliable channels from unreliable ones (Lectures 26–27)

**Stenning’s protocol:** unbounded sequence numbers, send until ack. Safety: data messages delivered in order, no extras. Liveness: if the channel is fair (or eventually delivers), the next message gets through.

**Alternating bit protocol (ABP):** 1-bit sequence numbers suffice if the channel is **FIFO** (or does not reorder). Simulation from Stenning by projecting seq numbers mod 2, with an invariant that at most one “outstanding” seq is in flight.

**Reordering channels** need more header bits or timers; bounded-header protocols that tolerate reordering are a research topic in the notes (A.1.3, B.1.1).

**Node crashes:** without durable state, ABP can duplicate or drop after reboot. Durable seq numbers, or a handshake that **forgets** old incarnations (5-packet handshake / TCP-style, Lecture 27 B.2), restore safety. This is the same issue as Paxos needing durable promises.

## Clock synchronization (pointers)

See ch. 12. In timed automata, clock-sync safety is a bound on `|c_i − c_j|`; the Lundelius–Lynch *(1−1/n)ε* bound is the fault-free delay-uncertainty limit.

## Hermes

- Cron with a timeout is a timed automaton: the timer class has `bu = T`. Sound only if the work class has a known upper bound or you accept abort-on-timeout (changing the spec).
- Gate-audit cold-start liveness: either assume fairness (async) or set `bu` on the audit class (timed). The second gives a **deadline**, the first only “eventually.”
- Crash recovery of a worker: treat like ABP+incarnation. Do not reuse in-flight request ids after reboot without a generation number (Paxos ballot / TCP ISN).
---
