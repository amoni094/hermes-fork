# Appendix B–C: Partial Orders, Lattices, Fixed Points, Induction

## Core Idea

The entire book sits on one theorem: a monotone map on a complete lattice has least and greatest fixed points (Knaster–Tarski). Finite height or continuity gives an algorithm (Kleene). Induction/coinduction justify reasoning *about* those points.

## Frameworks Introduced

### Partial orders

A poset `(L, ⊑)` : reflexive, antisymmetric, transitive.

- **Chain**: totally ordered subset.
- **Ascending chain condition (ACC)**: no infinite strictly increasing chain = finite height if L is finite; more generally well-founded height.
- **CPO**: every ω-chain has a least upper bound.

### Complete lattices

Every subset X ⊆ L has ⊔X (join) and ⊓X (meet). Then:

```
⊥ = ⊔∅ = ⊓L
⊤ = ⊓∅ = ⊔L
```

Powersets `P(D)` : `(⊆, ∪, ∩, ∅, D)` and the reverse `(⊇, ∩, ∪, D, ∅)` are the two lattices of bitvector analysis.

**Product**: L^n with pointwise order — the space of analysis assignments `Lab → L`.

**Monotone function space**: `{ f: L → L | x ⊑ y ⇒ f(x) ⊑ f(y) }` is a complete lattice pointwise. Transfer functions live here.

### Galois connections (order-theoretic)

Adjunction `α ⊣ γ`: `α(c) ⊑ a ⇔ c ⊑ γ(a)`. α is the left adjoint (preserves ⊔), γ the right adjoint (preserves ⊓).

### Knaster–Tarski

f: L → L monotone, L complete lattice.

```
Fix(f)  = { x | f(x) = x }   is a complete lattice
lfp(f)  = ⊓ { x | f(x) ⊑ x }     (least pre-fixpoint)
gfp(f)  = ⊔ { x | x ⊑ f(x) }     (greatest post-fixpoint)
```

### Kleene

If f is **continuous** (preserves ⊔ of ω-chains):

```
lfp(f) = ⊔ { f^n(⊥) | n ∈ N }
gfp(f) = ⊓ { f^n(⊤) | n ∈ N }    (for co-continuity)
```

If L has finite height, every monotone f is eventually stable under Kleene — continuity not required.

### Distributivity

f distributive: `f(x ⊔ y) = f(x) ⊔ f(y)`. Bitvector gen/kill:

```
f(S) = (S \ K) ∪ G
```

distributes over ∪ (and the reversed form over ∩). Hence MFP = MOP.

### Induction (App C)

To show P(lfp(f)): show P(⊥) and P(x) ⇒ P(f(x)) when P is admissible (closed under ⊔ of chains), or show P holds of all pre-fixpoints.

**Park induction**: if f(x) ⊑ x then lfp(f) ⊑ x.

### Coinduction

To show gfp(f) R y: show y ⊑ f(y) (y is a post-fixpoint). Used for greatest solutions (must-properties on reverse lattices, infinite traces).

## ASCII lattice diagrams

Bitvector may (`P(D)`, ⊆), |D|=2 {a,b}:

```
        {a,b} = ⊤
        /     \
      {a}     {b}
        \     /
          ∅ = ⊥
```

Must (same sets, order reversed): ⊤ = ∅, ⊥ = {a,b}.

Flat exit-code:

```
            ⊤
         /  |  \
       ok  cold  error
         \  |  /
            ⊥
```

Severity chain:

```
error
  |
cold-start
  |
 ok
  |
  ⊥
```

## Mental Models

- Join ⊔ = combination operator of the analysis (∪ for may, ∩ for must).
- Bottom = “no information yet” in the *iteration* order, which is the lattice order. For must, that is the *full* set.
- Tarski = existence. Kleene/worklist = computation. Park = proof.

## Anti-patterns

- **Calling any bounded poset a complete lattice** — need all subsets, not just pairs (finite lattices are complete, so bitvectors are fine).
- **Iterating from ∅ for AE** as if ∅ were ⊥ — it is ⊤ on the reversed lattice. Use ι at E and ⊥ elsewhere as in Ch 6.
- **Claiming Tarski gives an algorithm** on intervals without widening.

## Worked Example — Tarski for LV

L = P(Var)^Lab, f the monotone dataflow functional. lfp(f) = LV. Park: any annotation that is a pre-fixpoint (closed under gen/kill) *over-approximates* LV. A hand-written live set that is not the lfp is still sound if it is a pre-fixpoint — but coarser.

## Key Takeaways

1. Complete lattice + monotone f ⇒ lfp/gfp exist.
2. Finite height ⇒ worklist terminates.
3. Reverse the powerset for must.
4. Park induction: pre-fixpoints over-approximate the lfp.

## Connects To

- Every chapter uses this appendix.
- **Ch 4** widening is the escape hatch when ACC fails.
