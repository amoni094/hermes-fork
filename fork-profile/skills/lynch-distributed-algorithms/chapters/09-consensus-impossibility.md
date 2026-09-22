# Consensus impossibility (Lectures 12, 25)

## Shared-memory read/write (Lecture 12)

Interface: `init_i(v)`, `decide_i(v)`. Agreement, validity, termination despite stopping faults.

**Theorem.** No consensus algorithm using only atomic read/write registers that tolerates even **one** stopping fault (Loui–Abu-Amara / related to FLP; notes give both “arbitrary *f*” covering and the 1-fault case).

Valency argument:

- A finite execution is **0-valent** (resp. **1-valent**) if 0 (resp. 1) is the only decision in any extension.
- **Univalent** = 0- or 1-valent; **bivalent** = both decisions still possible.

There is a bivalent initial input vector (validity + Hamming-distance-1 pair; the differing process “looks failed”). From a bivalent execution, some 1-step extension remains bivalent (otherwise a critical process/step would decide the outcome, but a crash of that process before the step, plus commutativity of R/W on different registers, yields contradiction). Hence a fair infinite execution with no decision.

**RMW is strictly stronger:** a single compare-and-swap or test-and-set register **can** implement wait-free consensus for any *n* (Herlihy hierarchy; notes Lecture 15.2.1). Mutex via TAS is easy; consensus via “first fetcher wins.”

## FLP — asynchronous networks (Lecture 25)

Fischer–Lynch–Paterson. Message passing, complete graph, **reliable FIFO** channels, even **atomic broadcast**. Deterministic I/O automata, sequential processes, at most **one** crash-stop.

**1-fair execution:** all but at most one process take fair turns; all channels fair. Crashed process still receives inputs but may stop all locally-controlled actions.

**Theorem 1.** There is no 1-resilient consensus protocol.

**0-RCP:** agreement, validity, termination in all *fair* executions (no faults).
**1-RCP:** 0-RCP plus: in 1-fair executions, every non-stopped process decides.

**Lemma.** Every 1-RCP has a bivalent initial execution.
Proof: if not, Hamming-distance-1 0-valent vs 1-valent initials differing at *i*. A 1-fair extension in which *i* takes no local steps must decide (1-resilience). The rest of the system cannot distinguish the two initials ⇒ same decision. Contradiction.

**Bivalence preservation.** From a bivalent finite execution, there is a step (or a delay of one process / one message) leading to another bivalent execution. Commutativity: if *p* and *q*’s steps do not share a message, order can be swapped with the same end state. A “deciding” step of *p* would be invisible if *p* is the one crash. Iterate forever: no decision, yet 1-fair.

**Consequences (do not violate these):**

- Reliability of channels does **not** give consensus.
- Atomic broadcast as a primitive in the **same** async crash model does not help if it is implemented from the same channels (FLP includes broadcast).
- “Eventually the network is stable” is a **partial synchrony** assumption, not asynchrony.

## Escapes (see ch. 10 and 14)

| Escape | What changes |
|---|---|
| Synchrony | *f*+1 round crash consensus; Byzantine if *n*>3*f* |
| Partial synchrony / timeouts | DLS / timed automata; Paxos liveness |
| Randomization | Ben-Or: P[terminate]=1 |
| Stronger objects | RMW, CAS, queues, consensus objects |
| Weaker liveness | 2PC weak termination; Paxos “unique originator long enough” |

## Hermes

A pool of async workers agreeing on “which skill wins” with only at-least-once message passing and one possible crash **cannot** be solved deterministically. Pick one: a timeout (partial sync), a CAS on a lock file (RMW), a random tie-break, or a single designated coordinator (and accept blocking if it dies).
---
