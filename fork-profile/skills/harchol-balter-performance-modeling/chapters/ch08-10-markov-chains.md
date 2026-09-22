# Ch 8–10 — Discrete-Time Markov Chains

**Use when**: modeling slotted systems (Aloha, PageRank) or needing z-transforms of infinite-state chains.

## DTMC
Memoryless on the current state: P(X_{n+1}=j | X_n=i) = P_{ij}. Stationary π P = π, ∑π=1.

Finite irreducible aperiodic ⇒ unique limiting = stationary. Infinite-state: need **positive recurrence** (ergodic) else null-recurrent or transient (Aloha can be unstable).

## Ergodic theorem
For positive recurrent irreducible chains, time-average of f(X_n) → ∑ π_i f(i). Mean return time to i is 1/π_i.

Time-reversibility: π_i P_{ij} = π_j P_{ji}. Birth-death chains are reversible.

## z-transform for hard chains (Ch 10.3)
Generating function G(z)=∑ π_i z^i converts infinite balance equations into algebra. Used later for M/G/1 embedded chain.

## PageRank / Aloha
PageRank = stationary of a web DTMC with damping to fix dead ends. Slotted Aloha's chain can be unstable (throughput collapse as backlog grows) — a caution for retry/backoff without rate control.
