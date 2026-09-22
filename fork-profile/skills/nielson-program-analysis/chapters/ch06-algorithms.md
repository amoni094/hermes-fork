# Chapter 6: Algorithms

## Core Idea

Existence of lfp (Tarski) is not an algorithm. Compute MFP with chaotic iteration or a worklist; on infinite-height domains, insert widening at back-edges then narrowing. Constraint systems from Ch 3 use the same worklist on a different graph.

## Frameworks Introduced

### Chaotic iteration

From ⊥ (or ι at E, ⊥ elsewhere), repeatedly replace any `Analysis_∘(ℓ)` by the right-hand side of its equation until stability. Correct because the functional is monotone on a complete lattice of finite height ⇒ no infinite strictly ascending chain.

Slow if you recompute everything; still the reference specification.

### Worklist algorithm (dataflow)

```
for ℓ in Lab:
    Analysis_∘(ℓ) := (ι if ℓ ∈ E else ⊥)
W := F                          # all flow edges
while W ≠ ∅:
    pick (ℓ, ℓ') from W
    if f_ℓ(Analysis_∘(ℓ))  ≰  Analysis_∘(ℓ'):
        Analysis_∘(ℓ') := Analysis_∘(ℓ') ⊔ f_ℓ(Analysis_∘(ℓ))
        W := W ∪ { (ℓ', ℓ'') | (ℓ', ℓ'') ∈ F }
```

Then `Analysis_•(ℓ) = f_ℓ(Analysis_∘(ℓ))`.

Termination: each `Analysis_∘(ℓ)` only increases, finite height ⇒ finite updates.

Complexity: O(|F| · h · c) where h = lattice height, c = cost of ⊔ and f. Bitvectors: h ≤ |D|, c = word operations.

### Round-robin / reverse postorder

Iterate blocks in reverse postorder (forward analyses) or postorder (backward). Fewer iterations than chaotic on reducible CFGs. Still widen at loop headers.

### Constraint worklist (CFA / subset)

Nodes = constraint variables (`Ĉ(ℓ)`, `ρ̂(x)`). Edge u→v if a constraint `v ⊇ f(u, …)`. When u grows, re-evaluate constraints that mention u.

Same termination story: finite `P(AbsVal)`.

### Widening iteration

```
y := ⊥
loop:
    x := f^#(y)
    if x ⊑ y: break           # post-fixpoint
    y := y ∇ x                # only at widen points; ⊔ elsewhere
```

Then narrowing:

```
loop:
    x := f^#(y)
    if y ⊑ x: break
    y := y ∆ x
```

### MOP vs MFP in the implementation

Do not attempt MOP by unrolling loops. If you need path-sensitivity, clone blocks by a finite predicate abstraction (still MFP on a larger graph), or use a finite call-string k.

## Mental Models

- Worklist = “only recompute what a join just dirtied”.
- Reverse postorder = cheap static schedule of the same idea.
- Widening points = cut set of the back-edges; one per natural loop is enough.

## Anti-patterns

- **Starting AE from ∅ as lattice ⊥**: on the reversed lattice ⊥ is `AExp_*`. The *extremal value* ι is ∅; other nodes start at ⊥ = AExp_* for chaotic, or equivalently use the worklist init above (ι at E, ⊥ elsewhere). Mixing these is the classic off-by-lattice bug.
- **Worklist that forgets to add successors after a join**: unsound under-approximation.
- **Unbounded k in call strings**: non-termination / explosion; clamp.
- **Parallel chaotic updates without monotonic ⊔**: need ⊔ of old and new, not overwrite with a non-monotone patch.

## Worked Example — LV worklist

CFG: 1→2→3, 2→2 (loop test). LV backward so F = reverse edges: 3→2, 2→1, 2→2.

Init: LV_exit(3)=∅ = ι, others ⊥=∅ (may-analysis). Process reverse edges until stable. After `[use x]^3`, `x` flows to 2 and 1.

Hermes: implement this on a Python AST walker; do not recompute the whole script per iteration.

## Key Takeaways

1. Algorithm = worklist on the flow graph or the constraint graph.
2. Init: ι at extremal labels, ⊥ elsewhere; update by ⊔.
3. Finite height ⇒ done. Else widen at back-edges, then narrow.
4. Distributivity ⇒ MFP is path-exact (MOP); do not pretend otherwise.

## Connects To

- **Ch 2**: equations being solved
- **Ch 3**: constraint graph
- **Ch 4**: ∇ / ∆
- **Ch B**: why lfp exists
