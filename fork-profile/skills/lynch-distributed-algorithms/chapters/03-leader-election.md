# Leader election (Lectures 1–2, 17–18)

## Problem

Network of *n* processes, typically a ring or a connected graph. Each process has a unique identifier (UID) from a totally ordered universe. Exactly one process should output `leader` (safety: at most one; liveness: at least one). In anonymous rings without UIDs, deterministic election is often impossible.

Hermes analogue: skill-router arbitration — exactly one route should win.

## Synchronous ring: LCR (LeLann, Chang–Roberts)

Unidirectional ring. Each process sends its UID clockwise. On receiving *m*:

```
send := null
if status = chosen then status := reported
case
  m > own : send := m          # forward larger UID
  m = own : status := chosen   # own UID circumnavigated → leader
  else    : no-op              # discard smaller
```

Message alphabet: UIDs ∪ {`leader`}. State: `own`, `send` (UID or null), `status ∈ {unknown, chosen, reported}`.

**Correctness.** Let *i_max* be the process with maximum UID.

1. *i_max*’s UID is never discarded, so it returns after *n* hops; *i_max* outputs `leader` at round *n*+1.
2. Any other UID is discarded by a larger-UID process (at latest by *i_max*), so it never completes the circuit.

**Complexity.** Worst case Θ(*n*²) messages (UIDs increasing against the direction of travel). Best case Θ(*n*). Average over random UID placements Θ(*n* log *n*). Time: *n* rounds to elect, plus a report.

## Hirschberg–Sinclair (bidirectional ring)

Exponential-search probes in both directions: phase *k* probes distance 2^k. A process continues only if it is a local maximum in its current interval. *O(n log n)* messages, *O(n)* time.

## Lower bound (comparison-based, synchronous ring)

Comparison-based protocols (decisions depend only on order of UIDs, not their algebraic value) require Ω(*n log n*) messages in the worst case. Non-comparison tricks (bit-reversal rings, etc.) are treated as counterexamples to naive claims, not as a general *O(n)* solution when wake-up times differ.

Time lower bound: Ω(*n*) rounds in a ring (information must travel the circumference).

## General synchronous networks

Elect the maximum UID by flooding it along a spanning tree (often the BFS tree from a wake-up source), then convergecast. Time Θ(*D*) for diameter *D* once a root is known; electing the root is the same problem. Extends to BFS / shortest paths (ch. 04).

## Asynchronous rings

Same algorithms, different analysis: asynchrony does not break LCR safety (the max UID still circumnavigates; others still die at a larger node). Time is measured in longest message-delay chains.

**Peterson’s async ring election:** reduce the number of active processes by pairing; *O(n log n)* messages, unidirectional.

**Burns lower bound:** Ω(*n log n*) messages for async ring election in the comparison model.

## Safety vs liveness for routers

- Safety invariant: `|{i : status_i = chosen}| ≤ 1` in every reachable state.
- Liveness: under fairness of all processes and channels, some process enters `chosen`.

If processes may crash, LCR is not 1-resilient (the max UID may crash after being elected, or before). Use Paxos/ballots (ch. 10) when the “leader” must be re-elected after crash.

## Hermes: skill router

Model competing skills as ring or fully-connected processes with UIDs = (priority, name). Safety = at most one skill dispatched. Do not confuse with load-balancing (many winners). If dispatchers can fail, require majority-ack (Paxos) rather than LCR.
---
