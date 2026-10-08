# Patterns — proofs and Hermes applications

## Proof patterns

### Invariant (safety)

1. Write *I* strong enough that *I* ⇒ the safety claim (e.g. `|C| ≤ 1`).
2. Check start states.
3. Check every transition; if a case fails, strengthen *I* (auxiliary variables OK).
4. Stop. Do not conclude termination.

### Forward simulation (implementation ≤ spec)

1. Same external signature.
2. Relate start states.
3. Each implementation step matches a (possibly empty) spec fragment with the same external projection.
4. Conclude `fairbehs(impl) ⊆ fairbehs(spec)`.

### Indistinguishability chain (impossibility)

1. Start from an execution that *must* decide *v* (validity).
2. Change one receipt/message/crash so some process cannot tell.
3. Agreement copies the decision across the chain.
4. Reach an execution that *must* decide ¬*v*.

Used: coordinated attack, Byzantine *n*≤3*f*, FLP valency.

### Valency (FLP / R/W consensus)

1. Show a bivalent initial execution.
2. Show bivalence is preserved by taking or delaying one step.
3. Build an infinite 1-fair execution with no decision.

### Majority intersection (Paxos, Ben-Or counts)

Any two majorities intersect. A value once decided (majority YES / *n−2f* seconds) is the only value later majorities can adopt.

### Fairness contradiction (liveness)

Assume a fair run where the good event never happens. Show a class *C* is continuously enabled and silent ⇒ not fair.

### Blue rule (MST)

The min-weight edge leaving a fragment is in every MST. GHS/sync MST are bookkeeping around this.

## Hermes application patterns

### Atomic writes → IOA safety

- Spec automaton: serial file ADT. Trace alphabet: `write(v)`, `ack`, `read`, `return(v)`.
- Hidden: buffering, fsync, tmp copy (`int` actions).
- Safety *I*: “visible path is always a complete previous `v`, never a prefix of a write.”
- Serialization point: atomic `rename` (or journal commit record).
- Proof: forward simulation from the FS implementation to the serial ADT.

### Cron WAL contention → concurrent writers

- Model: multi-writer register or queue object; each cron job is a fairness class.
- Regular-register log is wrong (inverted records). Need atomic append.
- Options matching the notes:
  - **Mutex** around append (Peterson/TAS) — exclusive *C* = the log.
  - **Atomic RMW/CAS** of the head — wait-free if CAS is wait-free.
  - **Paxos** if writers crash/recover and no single lock holder.
- Liveness: lockout-freedom if every job must append; deadlock-freedom if “someone’s append” is enough.

### Gate-audit cold-start → liveness

- Claim to prove: in every fair (or timed-admissible) execution after `audit` input, a `result` output occurs.
- Not implied by “the audit code has no infinite local loop.” Need: lock acquisition, dependency services, and the audit class itself are fair / bounded.
- If a dependency can crash, FLP-shaped blocking appears; add timeout (timed automaton) and specify abort as a legal result.

### Skill router → leader election

- Safety: at most one dispatched skill (`status=chosen` unique) — invariant.
- Liveness: some skill dispatched — fairness of router workers, or unique originator.
- UIDs = `(priority, name)`: LCR/HS if everyone is up.
- Crashes: Paxos ballot or CAS on a lock file, not LCR.
- Do not use wall-clock “first wins” without Lamport/CAS: concurrent clocks violate happens-before.

## Model-selection cheat

```
Need agreement?
  ├─ processes can crash, network async, only messages/R/W
  │    → impossible (FLP). Add timeout, coin, CAS, or weaken termination.
  ├─ crash, synchronous
  │    → flood f+1 rounds, n > f
  ├─ Byzantine, synchronous
  │    → n > 3f, f+1 rounds
  ├─ message loss (no process faults)
  │    → coordinated attack impossible
  └─ crash+recovery, majority live
       → Paxos (agreement always; liveness with unique leader)

Need exclusive access?
  → mutex (R/W or RMW). Wait-free mutex of the resource itself is impossible
    (the resource is the bottleneck); wait-free *lock-free try* is a different spec.

Need “looks sequential”?
  → atomic object / linearizability, not merely regular registers.
```

## Anti-patterns

- Safety invariant cited as a progress proof.
- 2PC called “non-blocking.”
- Async reliable network treated as enough for consensus.
- Wall-clock order treated as happens-before.
- Single coordinator without a recovery/abort path (weak termination hidden in production).
- Assuming start-state invariants after a crash (need stabilization or durable ballots).
---
