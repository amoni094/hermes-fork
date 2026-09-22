# Chapter 4: Abstract Interpretation

## Core Idea

Cousot & Cousot: every static analysis is a sound approximation of a collecting semantics, connected by a Galois connection `(α, γ)`. Best transformers exist; cheaper monotone over-approximations are still sound. Infinite-height domains need widening (and optional narrowing).

## Frameworks Introduced

### Collecting semantics

Concrete domain `C`: typically `P(States)` or `P(Traces)` ordered by ⊆. The collecting semantics `f: C → C` maps a set of states to their successors (or the lfp of a transformer derived from SOS). This is the *specification*; it is not computed.

### Galois connection

```
α: C → A     γ: A → C
α(c) ⊑_A a   ⟷   c ⊑_C γ(a)
```

Consequences:

- `α`, `γ` monotone
- `c ⊑ γ(α(c))`  (extensive: abstraction loses precision, never lies by shrinking)
- `α(γ(a)) ⊑ a`  (reductive)
- `α` preserves ⊔, `γ` preserves ⊓

**Moore family**: image of `γ` is a Moore family of C (closed under ⊓, contains ⊤). Equivalent presentation of the same idea.

### Sound transformers

Best abstract transformer: `f^# = α ∘ f ∘ γ`.

Soundness (any of these equivalent under a Galois connection):

```
α ∘ f  ⊑  f^# ∘ α
f  ∘ γ  ⊑  γ ∘ f^#
f^#     ⊑  α ∘ f ∘ γ     (if f^# not chosen best)
```

Always prefer proving `α ∘ f ⊑ f^# ∘ α` on generators (elementary blocks).

### Induced operations

Given a Galois connection, *induce* abstract ⊔, tests, assignment from concrete ones via `α ∘ op ∘ γ`. This is how AE/RD arise as AI of the collecting semantics of While.

### Widening `∇ : A × A → A`

Required when `A` has infinite ascending chains (intervals, polyhedra, constant-propagation with unbounded Z).

Axioms:

1. `x ⊑ x ∇ y` and `y ⊑ x ∇ y`  (over-approximates join)
2. For any chain `x_0 ⊑ x_1 ⊑ …`, the sequence `y_0 = x_0`, `y_{i+1} = y_i ∇ x_{i+1}` is *eventually stable*.

Standard interval widening:

```
[a,b] ∇ [c,d] = [ if c < a then −∞ else a ,  if d > b then +∞ else b ]
```

**Where**: apply `∇` only at loop headers / CFG back-edges. Elsewhere use ⊔.

### Narrowing `∆`

After a post-fixpoint `x ⊒ f^#(x)` obtained with widening, recover precision:

1. `y ⊑ x  ⇒  y ⊑ x ∆ y ⊑ x`
2. Decreasing sequences using `∆` stabilise.

Interval narrowing typically trims infinities when the transformer proves a bound. **Never narrow before the widened sequence has stabilised.**

### Gate-audit lattice (Hermes)

Concrete: `P(Z)` of possible exit codes.

Flat abstract domain:

```
            ⊤
         /  |  \
       ok  cold  error
         \  |  /
            ⊥
```

```
α(∅) = ⊥
α({0}) = ok
α(C) = cold   if C ⊆ ColdStartCodes, C ≠ ∅
α(C) = error  if C ⊆ ErrorCodes, C ≠ ∅
α(C) = ⊤      otherwise (mixed / unknown)
γ(⊥) = ∅
γ(ok) = {0}
γ(⊤) = Z
```

Transfer of `;`: sequential composition is abstract composition. Transfer of `if`: join of branches. Soundness forbids concluding `ok` from `⊤`.

Severity chain alternative: `ok ⊑ cold-start ⊑ error` with ⊔ = max. Use when the audit question is “worst possible class”, not “which class”.

## Mental Models

- `α` *forgets* in a structured way; `γ` *re-embeds* the forgotten set as a worst-case concrete set.
- Widening is a *termination hack* that jumps up the lattice; narrowing walks back down without looping forever.
- If you can write a finite-height bitvector lattice, you do not need widening.

## Anti-patterns

- **Ad-hoc abstract steps without α**: cannot state soundness.
- **Widening at every node**: precision collapse to ⊤ in a few iterations.
- **Using ⊔ on intervals at a loop header**: may not terminate (`[0,0], [0,1], [0,2], …`).
- **Treating `α∘f∘γ` as required**: any larger `f^#` is still sound and often cheaper.
- **Narrowing from an unstable widen iterate**: termination proof is void.

## Worked Example — interval vs exit-code

`while [x < 10]^2 do [x := x + 1]^3` with `x` interval.

Kleene without widen: `[0,0]`, `[0,1]`, … unbounded if the bound is symbolic. With widen at 2: `[0,0] ∇ [0,1] = [0,+∞]`, then the test `x<10` *narrows* to `[0,9]` at the body and `[10,+∞]` on exit.

Exit-code analogue: a retry loop that may `exit 0` or `exit 75` (cold-start). Without widen on a counter domain the analysis may not terminate; on the *flat* exit lattice, height is 2 and Kleene is enough — join of `ok` and `cold` is `⊤`.

## Key Takeaways

1. State `C`, `A`, `α`, `γ` before writing `f^#`.
2. Prove `α∘f ⊑ f^#∘α` per block.
3. Finite height ⇒ Kleene/worklist. Infinite height ⇒ widen at back-edges, then narrow.
4. Hermes gate-audit = AI on `{⊥, ok, cold, error, ⊤}` (or the severity chain).

## Connects To

- **Ch 2**: bitvector analyses as induced AI
- **Ch B**: Tarski, Galois, Moore families
- **Ch 6**: iteration strategies with ∇
