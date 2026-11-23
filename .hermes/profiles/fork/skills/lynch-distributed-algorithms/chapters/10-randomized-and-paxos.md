# Randomized consensus and Paxos (Lectures 4, 25)

## Randomized coordinated attack (Lecture 4)

Deterministic coordinated attack is impossible. With random bits, processes can attack with probability arbitrarily close to 1 after enough rounds, at the cost of a small probability of disagreement or of violating validity. The notes treat this as the prototype: **randomness bypasses indistinguishability** because two locally identical views may still toss different coins.

## Ben-Or (asynchronous, crash or Byzantine)

Deterministic async consensus is impossible (FLP). Ben-Or: terminate with **probability 1**.

Notes version: *n ≥ 7f+1* (can be improved; this bound keeps the counting easy). Binary values. Asynchronous **phases**, each two rounds. Code for process *i* (`x` starts as *i*’s input):

```
for phase r = 1, 2, …:
  Round 1:
    broadcast first(r, x)
    wait for n−f messages first(r, ·)
    if ≥ n−2f messages have the same v then x ← v else x ← nil
  Round 2:
    broadcast second(r, x)
    wait for n−f messages second(r, ·)
    let v be a most frequent value, m its count
    if m ≥ n−2f then DECIDE v; x ← v
    else if m ≥ n−4f then x ← v
    else x ← random bit
```

**Validity.** If all nonfaulty start with *v*, round 1 already sees ≥ *n−2f* copies of *v*; round 2 decides *v* in phase 1.

**Agreement.** If *i* decides *v* at phase *r*, it saw ≥ *n−2f* `second(r,v)`. Any other nonfaulty *j* sees ≥ *n−4f* of those (counting overlap), and *n>7f* ⇒ *v* is *j*’s majority, so *j* cannot decide ¬*v*; *j* sets `x←v` and everyone decides *v* by phase *r*+1.

**Termination (probability 1).** For any phase *r*, with probability ≥ 2^{−n} all coin-tossers pick the unique “forcible” value *v* determined by the first nonfaulty process to collect *n−f* first-round messages. Then the next phase decides. Infinitely many independent phases ⇒ P[eventually decide] = 1.

Expected time is huge (2^{Θ(n)}). Cryptographic common coins improve this (Feldman–Micali); not practical as written.

## Parliament of Paxos (Lamport; notes 25.3)

Deterministic async algorithm. **Always** agreement and validity. Termination only under extra conditions. Tolerates, in practice: node stop **and recovery**, lost / reordered / duplicated messages, link failure and recovery — if ballot state is durable.

Ballots identified by `(t, i)` (local increasing *t*, originator index *i*). Five rounds:

1. Originator sends id `(t,i)` to all. Recipient **promises** not to vote YES on any smaller ballot it has not already voted on.
2. Recipient replies with all prior YES votes `(ballot, value)` for ballots < `(t,i)`. If originator hears from a **majority**, it sets the ballot’s value to the value of the **highest** such prior YES; if none, its own input.
3. Originator sends `((t,i), v)`.
4. Recipients that have not promised NO vote YES. If a majority YES, originator **decides** *v*.
5. Originator broadcasts the decision; recipients decide.

**Validity.** Decision value is some process’s input.

**Agreement.** Let *b* be the least ballot on which anyone decides, value *v*, majority *M* of YES. Any later ballot *b′* with a different value would need a majority *M′*; *M ∩ M′* contains some *i* who voted YES on *b*. *i* cannot have sent round-2 info for *b′* *before* that YES (the promise would forbid the YES). So *i* reports `(b,v)`, and no intervening different value exists by minimality ⇒ *b′* also gets *v*.

**Termination.** Two originators can livelock by restarting ballots. Guaranteed if there is a **sufficiently long interval** with a **single** originator, and a majority of processes and links operative. In practice: drop out if you see a smaller-index originator — this is a **partial-synchrony / leader-election** overlay, not pure asynchrony.

Paxos is the notes’ answer to **crash recovery**: durable promises + majority intersection replace 2PC’s single coordinator.

## Hermes

- Random tie-break in a skill router is Ben-Or-lite: safety (at most one winner after commit) must still be deterministic; only **progress** uses coins.
- Prefer Paxos/CAS-majority over 2PC when writers recover after kill −9.
- Duelling originators = two Hermes daemons both running cron election without a shared ballot file: livelock. Put ballot state on disk.
---
