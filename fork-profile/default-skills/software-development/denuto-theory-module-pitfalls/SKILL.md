---
name: denuto-theory-module-pitfalls
version: 1.2.0
author: Hermes Agent
description: "Use when building or reviewing Denuto reasoning modules."
keywords:
- theory
- reasoning
- dung
- allen
- bayes-ball
- deontic
- active-learning
- bfs
- wasserstein
- conformal
platforms:
- linux
---

# Denuto Theory Module Pitfalls

Pitfalls for implementing and reviewing the Denuto legal-tech reasoning subsystem
(`src/reasoning/`). These are real bugs found by adversarial review — not hypothetical.
Each has a fix and a verification pattern.

See `references/bug-classes.md` for code-level patterns and canonical fixes.

## Quick-reference checklist (run ALL before claiming a module clean)

1. Allen composition table — verify by brute-force ground-truth sampling, never transcribe
2. Entropy at boundary — p=1.0 must return exactly 0.0, never negative (no eps in log)
3. SDL F(p)+F(~p) — detect as DUAL_OBLIGATION_CONFLICT via SDL duality
4. Condition string matching — normalise whitespace before ==
5. First-match classifiers — provide classify_all_X list variant; export from __init__
6. Backdoor criterion — G_x^out (cut outgoing) for d-sep test; G_x^in for do-calculus
7. Dung preferred extensions — maintain Pareto-front in-place; no mid-search pruning; no O(2^n) collection
8. Bayes-Ball collider activation — z_and_anc = Z ∪ ancestors(Z), NOT descendants; rename variable
9. Bayes-Ball via_desc blocking — observed non-collider (chain/fork node in Z) blocks in via_desc=True branch; collider activation ONLY belongs in via_desc=False branch
10. BFS for path-finding — use per-path frozenset guard, NOT global seen set (diamond graphs produce O(2^k) dequeues)
11. BFS path explosion — add max_paths cap (default 500); per-path frozenset BFS is O(n!) simple paths on dense graphs
12. Dual-module import — always import from src.reasoning.X, never bare reasoning.X
13. _nodes iteration order — use list not set for PYTHONHASHSEED-stable AC-3
14. Wasserstein W1 grid — n = max(n, 100) minimum; n=2 gives 100% error on small cohorts
15. d_separated disjointness — raise ValueError if X∩Z or Y∩Z is non-empty; d-separation undefined for overlapping sets
16. conformal_coverage_check empty guard — must match calibrate_conformal_threshold: both return -inf, empirical_coverage=1.0
17. conformal undersized calibration polarity — required_idx > n must return -inf (abstain all), not +inf; score > +inf is always False (never abstains)

## Pitfalls

### Dual-module import enum identity bug

Importing from `reasoning.temporal_engine` (no `src.` prefix) AND `src.reasoning.temporal_engine`
creates two distinct Python module instances with separate `IntervalRelation` enum classes.
Frozenset membership check `IR1.BEFORE in frozenset({IR2.BEFORE})` returns False even though
both are semantically the same enum member. Causes PYTHONHASHSEED-dependent test failures.

Fix: standardise all test imports to `from src.reasoning.X import ...`. One path across the
entire codebase. Confirm with: `grep -rn 'from reasoning\.' tests/` — should return empty.

### Allen composition table — brute-force verification required

Manually transcribed Allen tables can have >50% wrong entries at 13×13 scale. Tests written
by the same author as the table only cover the entries transcribed correctly.

Verification procedure:
1. Write ground-truth `allen_relation(a_s, a_e, b_s, b_e)` from interval boundary comparisons
2. For each (r1, r2) pair, sample 1000+ concrete float interval triples recording allen(a,c)
3. Build the correct table empirically from observations
4. Replace the static table entirely — never patch individual entries

### Dung preferred extensions — no mid-search pruning; bounded storage

Subset-dominance pruning during backtracking terminates early and misses extensions.
With A↔C (symmetric attack) and isolated B: visiting {A,B} first causes {B,C} to
never be explored.

Fix: maintain a Pareto-front list (`admissible_maximal`) in-place using `_update_maximal(s)`:
- If s is a subset of any existing entry: do NOT insert
- Otherwise: remove all existing entries that are subsets of s, then insert s
This gives O(maximal_extensions × n) storage instead of O(2^n), while still exploring every
branch (never prune on dominance during backtracking, only on conflict-freeness).

Exclude self-attacking arguments from the candidate list before the search begins.

Verify: A↔C, isolated B → [{A,B},{B,C}]; unattacked A, C→C, C→B → [{A}];
empty AF → [frozenset()]; all-self-attacking AF → [frozenset()].

### Bayes-Ball z_and_anc — ancestors(Z) not descendants(Z)

Collider V is active iff V ∈ Z OR a descendant of V is in Z. The set of nodes that can
activate a collider is Z ∪ ancestors(Z). Using descendants reverses this relationship.

Parent-of-collider failure: X→C←Y, ZZ→C. Conditioning on {ZZ}:
- Wrong: descendants({ZZ})={C} adds C to z_and_desc, opens X-C-Y path incorrectly
- Correct: ancestors({ZZ})={} so z_and_anc={ZZ}, C not added, path stays blocked

Fix: `z_and_anc = set(Z) | {anc for z in Z for anc in dag.ancestors(z)}`
Rename the variable from `z_and_desc` to `z_and_anc` throughout.
Verify all four cases: chain, fork, collider, parent-of-collider.

### Bayes-Ball via_desc=True — observed non-collider must BLOCK, not activate

Even after the z_and_anc fix, the `via_desc=True` branch fires collider activation for any
node in Z because Z ⊆ z_and_anc always holds. This treats observed chain and fork nodes as
active colliders. A serial chain Y→Z→X conditioned on Z returns d-connected (wrong).

Root cause: z_and_anc includes Z itself. The collider-activation code `if node in z_and_anc`
hits every observed node. Non-colliders in Z should BLOCK, not activate.

Correct Bayes-Ball rule (Shachter 1998 §3, Pearl 2009 §1.2):
- via_desc=True, node ∉ Z: pass upward to parents AND downward to other children
- via_desc=True, node ∈ Z: BLOCK — do not propagate (observed non-collider stops ball)
- via_desc=False, node ∉ Z: pass downward to children
- via_desc=False, node ∈ Z: BLOCK downward, BUT if node ∈ z_and_anc → collider activated, pass upward

Fix: remove the collider-activation block entirely from the `via_desc=True` branch.
Collider activation belongs ONLY in `via_desc=False`.

Verify after fix:
```
chain Y->Z->X | Z   -> True   (non-collider blocks — this was the failing case)
chain Y->Z->X | {}  -> False  (path active)
fork  Z->X,Z->Y | Z -> True
collider X->C<-Y | {} -> True
collider X->C<-Y | C  -> False  (collider activated via via_desc=False path from X or Y)
parent-of-collider | ZZ -> True
3-chain X->M->N->Y | M -> True
3-chain X->M->N->Y | N -> True
3-chain X->M->N->Y | {} -> False
```

Do NOT conflate with the z_and_anc content fix — both bugs are independent and both must
be fixed. The z_and_anc fix corrects WHICH nodes activate colliders; this fix corrects
WHICH BRANCH does the activation.

### d_separated disjointness precondition

Pearl's d-separation is only defined for disjoint sets (X, Y, Z). If Y∩Z or X∩Z is non-empty,
the algorithm silently returns wrong answers.

Fix:
```python
if x & z or y & z:
    raise ValueError(f"d_separated requires disjoint (X, Y, Z); X∩Z={x & z!r}, Y∩Z={y & z!r}")
```

### BFS for path-finding — per-path frozenset, not global seen

Global `seen` set prevents exploring the same node via multiple routes. In a diamond graph
(A→B, A→C, B→D, C→D): marking D as seen when enqueued from A causes C→D to never be explored.
Mark-on-dequeue was proposed as a fix but produces the reverse bug: both B and C enqueue D
before either is dequeued, so D appears in the queue twice — O(2^k) dequeues at k convergences.

Fix: replace global `seen` with a per-path frozenset passed as a queue element:
```python
queue: deque[tuple[str, list[str], int, frozenset[str]]] = deque(
    [(start_id, [start_id], 0, frozenset({start_id}))]
)
...
if neighbor.node_id not in path_seen:
    queue.append((neighbor.node_id, new_path, depth + 1, path_seen | {neighbor.node_id}))
```
This finds all simple paths (A→B→D AND A→C→D) while preventing cycles.

### BFS path explosion cap

Per-path frozenset BFS enumerates all simple paths up to max_hops. A 30-node dense graph
has ~14M five-hop paths from one start. `_build_graph_context()` calls `traverse()` per
clause — unbounded in time and memory.

Fix: add `max_paths: int = 500` parameter to `traverse()`. Check BEFORE popleft:
```python
while queue:
    if len(paths) >= max_paths:
        break
    current_id, path, depth, path_seen = queue.popleft()
```

### Wasserstein W1 grid resolution

The quantile-interpolation W1 estimate uses `n = max(len(u), len(v))` grid points by default.
At n=2, error is 100% (returns 50ms for true W1=25ms on [0,100] vs [50,50]).
Error converges to <5% only at n≥50; at n=100 it is <1%.

Fix: `n = max(len(u_sorted), len(v_sorted), 100)`

Cohort W1 comparison: use leave-one-out reference pool, not pooled-all. Large cohorts dominate
the pool and get artificially low W1. Fix:
```python
ref = [lat for cv, lats in cohort_latencies.items() for lat in lats if cv != cohort.cohort_value]
if not ref:
    continue
```

### conformal undersized calibration — +inf polarity is WRONG

When `required_idx = ceil((n+1)*(1-alpha)) > n`, returning `float('+inf')` makes `score > +inf`
always False — nothing ever abstains. The comment 'return +inf (abstain always)' is backwards.

Fix: return `float('-inf')`. With tau=-inf, `score > -inf` is always True → everything abstains
(fail closed). Update all tests asserting `t == float('inf')` for undersized n.

### conformal_coverage_check empty guard must match calibrate_conformal_threshold

When calibrate_conformal_threshold was fixed to return -inf for empty input, a separate early
guard in conformal_coverage_check still returned threshold=1.0, empirical_coverage=0.0.

Fix: update the coverage_check guard to match:
```python
return {
    "threshold": float("-inf"),
    "empirical_coverage": 1.0,
    "target_coverage": 1.0 - alpha,
    "coverage_gap": alpha,
}
```
Whenever the underlying threshold function is updated, grep all wrappers for their own
empty-input guards and update them in the same commit.

### Adversarial fix oscillation — a fix can introduce the bug it was meant to replace

Two consecutive adversarial passes found opposite bugs in the same BFS function:
- Pass 1: mark-on-enqueue skips indirect paths (A→B→C not explored)
- Pass 1 fix: mark on dequeue instead
- Pass 2: mark-on-dequeue causes O(2^k) duplicate dequeues at diamond nodes

The correct fix (per-path frozenset) was not the natural first fix from either finding.
When an adversarial reviewer reports a new bug in a just-fixed function, first ask:
"Is this a regression introduced by the fix, or a pre-existing bug the fix exposed?"
If it is a regression, the root design is wrong — find the structurally correct solution
rather than oscillating between two incorrect implementations.

### execute_code truncates large outputs

`execute_code` silently truncates stdout to ~1 line for scripts over ~200 lines.
Use `terminal` with a shell heredoc or `write_file` + terminal for large reconstruction scripts.

### strands collection errors are pre-existing

Tests importing from `src.pipeline.agents.compiler` (requires `strands` package) fail
collection in environments without `strands`. These are NOT regressions.

Fix: run targeted test subsets over changed files only:
`python -m pytest tests/reasoning/ tests/symbolic/ tests/run_ledger/ tests/test_aimd.py`

Confirm pre-existing: `git stash && python -m pytest tests/ --co -q 2>&1 | grep 'ERROR tests/'`
