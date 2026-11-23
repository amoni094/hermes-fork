# Synchronous network algorithms (Lectures 2–3)

Model: connected undirected graph, lock-step rounds, reliable links unless a failure chapter says otherwise.

## Breadth-first search

From a distinguished source *s*, construct a BFS tree: parent pointers, distance layers.

Basic flooding: a node that first hears “explore” at round *k* sets parent to the sender and distance *k*, then forwards. Time *O(D)*. Messages *O(|E|)*.

**Extensions:** forest from multiple sources; rebuild after topology change; pipelined multiple BFS.

## Shortest paths

**Unweighted:** BFS distances.

**Weighted (nonnegative):** distributed Bellman–Ford. Each node *i* keeps `dist_i` (init 0 at source, ∞ elsewhere) and `parent`. Each round, send `dist` to neighbors; on receiving `d` from *j*, if `d + w(j,i) < dist_i` then update. After *n*−1 rounds, correct on graphs without negative cycles. Messages *O(n|E|)*.

Invariant: `dist_i` is always the length of some *s*–*i* path (or ∞); it is nonincreasing; after *k* rounds it is at most the shortest *k*-edge path.

## Minimum spanning tree (synchronous)

Assume distinct edge weights (otherwise break ties by endpoint UIDs). Unique MST.

**Blue rule:** the minimum-weight edge leaving a fragment (connected MST subtree) is safe to add.

Synchronous algorithm: fragments grow in phases; each fragment finds its minimum outgoing edge (MOE) by a tree convergecast, then adds it, merging fragments. *O(n)* rounds if phases are globally synchronized; communication depends on implementation.

Asynchronous analogue: GHS (ch. 11), more bookkeeping (levels, test/reject, change-root).

## Maximal independent set (MIS)

A set *S* of vertices: no two adjacent, and every vertex outside *S* has a neighbor in *S*.

Luby’s randomized synchronous algorithm (notes Lecture 3): each undecided vertex marks itself with probability 1/(2d(v)) (or similar), then a marked vertex joins MIS if no higher-priority marked neighbor exists; losers and their neighbors drop out. Expected *O(log n)* rounds.

Deterministic MIS on rings/special graphs is easier; general graphs need either randomization or more rounds.

## Hermes

- BFS ≈ collecting a frontier of tool results with increasing hop count (subagent depth).
- MST ≈ building a minimum-cost communication tree among workers (avoid redundant fan-in).
- MIS ≈ selecting a conflict-free subset of skills to run in parallel (no two that write the same file).
---
