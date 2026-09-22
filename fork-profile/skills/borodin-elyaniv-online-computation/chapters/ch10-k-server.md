# Chapter 10: The k-Server Problem

## Core Idea
k servers live in a metric space M. A request is a point `r ∈ M`; some server must move to `r`; cost is distance moved. The **k-server conjecture**: there is a k-competitive algorithm on every metric. WFA is **(2k−1)-competitive** (Koutsoupias–Papadimitriou), matching the DET lower bound k up to factor 2.

## Key Concepts
- **Configuration:** a multiset of k points (server locations). Distance between configurations = min-cost matching (min-weight bipartite matching).
- **Request:** a point; after service, at least one server occupies it.
- **Paging = k-server on a uniform metric** (all distances 1): moving a server = eviction+load.
- **Double Coverage (DC)** on a line (or tree): the two servers adjacent to the request both move toward it at equal speed until one serves; others idle. **k-competitive** on lines and trees.
- **Balancing algorithms:** keep the cumulative distance each server has traveled roughly equal (or greedy + balance). Work on restricted metrics; not a general (2k−1) solution.
- **Work function** `w_t(C)`: min cost to serve the first t requests and end in configuration `C`.
- **WFA for k-server:** move to a configuration `C` that contains the request and minimizes `w_t(C) + d(C_{t−1}, C)`.
- **k-server conjecture.** `R = k` on every metric. Open in general at the time of the book (still open in full generality; WFA is 2k−1).
- **Failed generalizations (§10.8).** Natural strengthenings of the conjecture (e.g. certain weighted servers / MTS-style) are false — do not “generalize k-server” carelessly.

## Frameworks and Methods
- **Lower bound k.** Metric with k+1 points. Cruel: request the unique uncovered point. OPT moves at most 1 for every k of ALG’s moves (OPT can sit on a good k-set). Same as paging LB.
- **Potential for DC on a line.** Sum of server-to-server matching to OPT plus offsets; DC’s move decreases the potential enough to pay k·ΔOPT.
- **WFA analysis.** Quasiconvexity of work functions; extended cost; potential combining `w(C_ALG)` and a sum over configurations. Yields 2k−1.
- **2-server Euclidean.** An efficient 3-competitive algorithm (§10.5) without full WFA machinery.

## Key Results and Theorems

**Deterministic LB.** Every DET k-server algorithm is at least **k-competitive** on some metrics (in fact on any metric with ≥ k+1 points, in the strong sense of the paging reduction).

**DC on a line/tree.** Double Coverage is **k-competitive**.

**2-server Euclidean.** 3-competitive efficient algorithm.

**WFA.** The k-server work function algorithm is **(2k−1)-competitive** on every metric space.

**Conjecture.** WFA (or something) is k-competitive on every metric. Proven for k=2, for lines/trees, for some special metrics; 2k−1 is the general theorem in this book.

## Key Equations
- Service cost: `d(s_i, r)` for the chosen server i, then `s_i ← r`.
- Config distance: `d(C,C') = min_{matchings π} ∑ d(C_j, C'_{π(j)})`.
- Work function: `w_t(C) = min_{C' ∋ r_t} [ w_{t−1}(C') + d(C', C) ]` with C containing r_t after service (precise form: min cost of a move that serves r_t then relocates to C).
- WFA: `C_t = argmin_{C ∋ r_t} [ w_t(C) + d(C_{t−1}, C) ]`.

## Worked Example
k=2 on a line, servers at 0 and 10, request at 3. DC: left server moves 3→3, right moves 3 toward 3 (to 7). If the next request is at 8, the right server is closer. Ratio stays ≤ 2.

## Hermes application
**Skill router as k-server:** k loaded skills = servers; query = request point in a metric of embedding/relatedness. Moving a server = loading a new skill (evicting another). Use:
- **DC** if skills are ordered on a line (e.g. a single specialty axis);
- **WFA** if k is tiny and the metric is arbitrary;
- **paging MARK/LRU** if the metric is essentially uniform (all skill-switch costs equal).

Do not expect ratio 1. The DET lower bound k says a k-slot skill cache cannot match hindsight OPT better than k in the worst case.

## Anti-patterns
- **Greedy nearest-server** as a general k-competitive algorithm. False on general metrics (unbounded or large ratio).
- **Quoting k-competitiveness of WFA.** The theorem is 2k−1, not k.
- **Infinite-server / no eviction.** Then the problem is not k-server.
