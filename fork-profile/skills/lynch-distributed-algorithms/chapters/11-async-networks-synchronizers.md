# Asynchronous networks and synchronizers (Lectures 17–20)

## Async model

Nodes = I/O automata; edges = fair FIFO (or fair lossy, depending on the problem) channel automata. No round structure. Time complexity: along the longest causality chain, counting each message delay as 1 (sometimes with a bound *d* on delay for analysis only — that bound is **not** in the model).

Leader election, BFS, shortest paths all have async versions (Lectures 17–18). Safety proofs look like the sync ones; liveness uses channel+node fairness.

## Broadcast–convergecast

A root floods; leaves send acks up; root knows the wave is done when its children ack. Termination detection for a **single** wave. General stable-property detection: ch. 12 (Dijkstra–Scholten, snapshots).

## GHS minimum spanning tree (Gallager–Humblet–Spira)

Async, distinct edge weights, unique MST.

Fragments (connected subtrees of the MST) at **levels**. A fragment of level *L* has at least 2^L nodes. Each fragment finds its **minimum outgoing edge** (MOE):

- Nodes `test` adjacent edges; `reject` if internal; `accept` if external.
- Convergecast the best MOE to the fragment core; `changeroot` toward that edge; `connect` across it.

Merges: if two fragments connect via an edge that is MOE of both, level increases by 1 (balanced merge). If a higher-level fragment absorbs a lower one, level stays (absorption).

**Complexity (classic):** *O(n log n)* messages? GHS is *O(|E| + n log n)* messages and *O(n log n)* time (in the async delay=1 measure). Notes §19.2.7.

**Correctness:** blue rule (MOE of a fragment is in the MST) + level accounting so that `test`/`reject` is not confused by in-flight connects. Proof is a large invariant on fragment partitions and edge states (`basic`, `branch`, `rejected`).

## Synchronizers (Awerbuch)

A **synchronizer** implements a synchronous network algorithm on top of an asynchronous network: it generates “pulses” such that a node starts pulse *p*+1 only after all pulse-*p* messages of neighbors have arrived (or are known not to exist).

**High-level:** each simulated round = one pulse; original `msgs`/`trans` run unchanged.

**α synchronizer:** after sending round messages, ack each message; when all acks in, send “safe” to neighbors; when all neighbors safe, next pulse. Time overhead *O(1)* per round; message overhead *O(|E|)* per round.

**β synchronizer:** a spanning tree; convergecast “safe” to root, broadcast “next pulse.” Message overhead *O(n)* per round; time overhead *O(n)* (tree height).

**γ / hybrid:** partition into clusters, α inside, β between cluster leaders. Tradeoff parameterized by cluster radius.

**Applications:** run sync BFS, MST, etc., on async nets, paying the overhead.

**Lower bound:** there are graphs/algorithms where any synchronizer has nontrivial message or time overhead (notes §20.3) — you cannot get sync-round speed for free.

## Hermes

- GHS-style “merge fragments” ≈ merging worktrees / agent subtasks along cheapest communication edges (don’t all-to-all).
- Synchronizer ≈ a barrier: do not start the next tool-batch until the previous batch’s results are in. α-style (pairwise acks) vs β-style (coordinator convergecast). The barrier is **liveness-sensitive**: a crashed worker without a timeout blocks all pulses (FLP-adjacent).
---
