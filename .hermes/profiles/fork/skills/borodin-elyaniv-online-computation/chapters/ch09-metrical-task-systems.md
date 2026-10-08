# Chapter 9: Metrical Task Systems

## Core Idea
A **metrical task system (MTS)** is N states with a metric `d` on states. Each request is a *task* (a cost vector over states). ALG may move (pay `d`) then process the task (pay the state’s task cost). Unifies paging, k-server (as a special configuration metric), and many configuration-search problems. The **work function algorithm (WFA)** is (2N−1)-competitive, matching the lower bound.

## Key Concepts
- **States** `{1,…,N}` with metric `d` (triangle inequality, `d(x,x)=0`, symmetric).
- **Task** `r`: `r(x) ≥ 0` is the processing cost in state `x`.
- **ALG cost** for a step: `d(s_{t−1}, s_t) + r_t(s_t)`.
- **Traversal / work-function-free algorithms.** Traversal is `8(N−1)`-competitive: move along an Euler-style tour of a spanning tree, repeating until the task is “cheap enough.”
- **Cruel adversary.** Always issue a task that is cheap only in states ALG is not in (or infinitely expensive in ALG’s state). Used for the 2N−1 lower bound.
- **Work function** `w_t(x)`: minimum cost of serving the first t tasks and **ending in** state `x`. Satisfies
  ```
  w_t(x) = min_y  w_{t−1}(y) + d(y,x) + r_t(x)
  ```
  (process in `x` after moving from `y`).
- **WFA:** from current state `s`, move to a state `x` minimizing `w_t(x) + d(s,x)` (with a tie-breaking rule that actually *goes* to a minimizer of `w_t`). Intuition: go where OPT could be, paying the metric.

## Frameworks and Methods
- **Potential for WFA.** Typically `Φ = w(s) + ∑_x w(x)` or a variant; amortized cost ≤ 2N−1 times the increase of `min_x w(x)` (which tracks OPT).
- **Lower bound 2N−1.** Cruel tasks on a uniform metric (or a simplex of states): force ALG to traverse while OPT sits; then migrate OPT; repeat. Each cycle ALG pays ~2(N−1) vs OPT 1, plus a last move → 2N−1.
- **Uniform MTS randomized.** On a uniform metric, randomized algorithms achieve `Θ(log N)` vs OBL (analogous to MARK / Harmonic).
- **Polylog randomized MTS.** A randomized algorithm that is polylog(N)-competitive for *any* metric MTS vs OBL (§9.6); exponentially better than DET’s Θ(N).

## Key Results and Theorems

**Traversal.** There is a deterministic `8(N−1)`-competitive MTS algorithm.

**Lower bound.** Every deterministic MTS algorithm is at least **(2N−1)-competitive**.

**WFA for MTS.** The work function algorithm is **(2N−1)-competitive** (optimal among DET).

**Randomized uniform MTS.** `Θ(log N)` vs OBL.

**Randomized general MTS.** Polylog(N) vs OBL (not vs ADOFF — ADOFF again equals DET).

## Key Equations
- Step cost: `d(s,s') + r(s')`.
- Work function recurrence: `w_t(x) = r_t(x) + min_y [w_{t−1}(y) + d(y,x)]`.
- WFA choice: `s_t ∈ argmin_x [ w_t(x) + d(s_{t−1}, x) ]`.
- OPT cost after t tasks: `min_x w_t(x)` (minus initial, depending on start state).

## Worked Example
N=2 states, `d=1`, tasks that cost 0 in one state and ∞ in the other (forced moves). WFA moves iff the work function says OPT has already paid for being in the other state. Ratio 3 = 2·2−1. Ski-rental-like.

## Hermes application
Choosing among N **configurations** (prompt template, tool set, memory profile) with a switching cost is MTS. Use **WFA** if N is small (track `w(x)` for each config). If N is huge (all skills), do not run WFA on the full simplex — reduce to k-server (Ch. 10) or experts/FTRL (Ch. 14) with switching costs.

## Anti-patterns
- **Ignoring the metric** and treating tasks as experts without switch cost. That is a different problem (and FTRL without switching cost is not MTS).
- **Quoting polylog randomized MTS vs an adaptive user.** OBL only.
- **Computing w_t incorrectly** by adding `r_t` in the *old* state. Process after the move.
