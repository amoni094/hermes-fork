# Chapter 2: Data Flow Analysis

## Core Idea

Specify a property lattice and a monotone transfer function per block; the analysis is the least (or greatest) solution of the dataflow equations on `flow(S*)`. Four bitvector instances cover almost all local script audits.

## Frameworks Introduced

### Available Expressions (AE) — forward, must, ∩

An expression `a` is *available* at `ℓ` if every path from `init` to `ℓ` evaluates `a`, and no variable of `a` is redefined after the last evaluation.

```
gen_AE([x:=a]^ℓ)  = { a' ∈ AExp_* | a' subexpr of a ∧ x ∉ FV(a') }
kill_AE([x:=a]^ℓ) = { a' ∈ AExp_* | x ∈ FV(a') }
gen_AE([b]^ℓ)     = { a' ∈ AExp_* | a' subexpr of b }
kill_AE([b]^ℓ)    = ∅
gen_AE([skip]^ℓ)  = ∅
kill_AE([skip]^ℓ) = ∅
```

Lattice `(P(AExp_*), ⊇)`, ⊔ = ∩, ⊥ = AExp_*, ι = ∅ at `init`.

Use: CSE, redundant `$(cmd)` in bash, skip re-hashing an unchanged file.

### Reaching Definitions (RD) — forward, may, ∪

A definition `(x,ℓ)` *reaches* `ℓ'` if some path from `ℓ` to `ℓ'` does not redefine `x`.

```
gen_RD([x:=a]^ℓ)  = { (x,ℓ) }
kill_RD([x:=a]^ℓ) = { (x,ℓ') | B^{ℓ'} assigns x } ∪ { (x,?) }
gen_RD(other)     = ∅
kill_RD(other)    = ∅
```

Lattice `(P(Var_* × Lab_*), ⊆)`, ⊔ = ∪, ⊥ = ∅, ι = {(x,?) | x ∈ FV(S*)}.

Use: **dead write** — `(x,ℓ)` in RD_exit(ℓ) but killed before any use; **uninit** — `(x,?)` reaches a use.

Hermes bottleneck scanner: dead writes of env vars, flags, cache keys.

### Very Busy Expressions (VB) — backward, must, ∩

`a` is *very busy* at `ℓ` if every path from `ℓ` to exit evaluates `a` before any `x ∈ FV(a)` is redefined.

```
gen_VB([x:=a]^ℓ)  = { a' ∈ AExp_* | a' subexpr of a }
kill_VB([x:=a]^ℓ) = { a' ∈ AExp_* | x ∈ FV(a') }
gen_VB([b]^ℓ)     = { a' ∈ AExp_* | a' subexpr of b }
kill_VB([b]^ℓ)    = ∅
```

Lattice reversed as AE. `F = flow^R`, `E = final(S*)`, ι = ∅.

Use: code motion / hoist loop-invariant work that is definitely used (must).

### Live Variables (LV) — backward, may, ∪

`x` is *live* at `ℓ` if some path from `ℓ` uses `x` before redefining it.

```
gen_LV([x:=a]^ℓ)  = FV(a)
kill_LV([x:=a]^ℓ) = { x }
gen_LV([b]^ℓ)     = FV(b)
kill_LV([b]^ℓ)    = ∅
gen_LV([skip]^ℓ)  = ∅
kill_LV([skip]^ℓ) = ∅
```

Lattice `(P(Var_*), ⊆)`, ι = ∅ at exits (nothing live after the program unless you model the environment as a use).

Use: **unused import** — imported name never live; **dead store**; register pressure.

If a cron script's last act is `export FOO`, treat `FOO` as live at `final` (environment is a use). Otherwise LV will flag the export as dead — which is correct *inside* the process and wrong *across* process boundary. That is an interprocedural / observational specification choice, not a bug in LV.

### Monotone frameworks (2.2)

Instance: `(L, ℱ, F, E, ι, f)` with each `f_ℓ` monotone on complete lattice `L`.

```
Analysis_∘(ℓ) = ι                                   ℓ ∈ E
              = ⨅ { Analysis_•(ℓ') | (ℓ',ℓ) ∈ F }    otherwise
Analysis_•(ℓ) = f_ℓ(Analysis_∘(ℓ))
```

The associated functional `F_MF` on `L^{Lab}` is monotone; Knaster–Tarski gives lfp (and gfp). Kleene iteration from ⊥ computes lfp when height is finite.

**MOP** (meet over all paths): `⨅ { f_{π}(ι) | π path from E to ℓ }`.
**MFP**: lfp of the equation system.

If every `f_ℓ` is *distributive* (`f(x ⊔ y) = f(x) ⊔ f(y)`), then MFP = MOP. Bitvector gen/kill *are* distributive. Arbitrary monotone `f_ℓ` only guarantee MFP ⊑ MOP.

### Interprocedural analysis (2.4)

- **Context-insensitive**: one RD/LV map per procedure; call = ⊔ over all callers. Cheap; polluted.
- **Call strings** of length k: context = last k call sites. Exact at k=∞ on acyclic call graphs; approximate by clamping.
- **Functional approach**: transfer function of a procedure is a monotone map `L → L`; cache it; at a call, apply the map to the caller’s abstract state. Sharper on recursive procedures.

Hermes cron→script→library: start context-insensitive; if a library helper is called from “ok path” and “error path”, bump to call-string k=1 so exit-code lattice does not smash.

### Shape / alias (2.5)

Abstract heap: allocation sites as nodes; edges = selector (field, env key, file path). **May-alias**: two names can denote the same summary node. **Must-alias**: they do on every path.

Use: two scripts locking the same file; `PATH` mutation aliasing `command -v`; clipboard vs config path.

Conservative may-alias over-approximates interference; must-alias under-approximates (use for must-kill of a location).

## Mental Models

- May = “∃ path”. Must = “∀ paths”. Join operator tells you which.
- Backward analyses ask the *future*; they need `flow^R` and `final`.
- Interprocedural is the same monotone framework on a larger graph, plus a policy for pairing call/return.

## Anti-patterns

- **Union for AE/VB**: a must-fact that holds on only one predecessor is not definite.
- **Forgetting `(x,?)` in RD**: silent uninit.
- **LV without env uses**: exports look dead.
- **Inlining all calls into one CFG without cloning**: return-flow mixing (unmatched call/return).
- **Must-alias used as may-alias**: missed interference.

## Worked Example — dead write + unused import

```
[import os]^1
[import sys]^2
[x := 0]^3
[x := 1]^4
[use(x)]^5
```

RD: `(x,3)` is killed at 4 before any use ⇒ dead write at 3.
LV: `os` never generated as a use ⇒ `os` not live at 1 ⇒ unused import. `sys` same. `x` live at 4, not at 3 after kill.

## Key Takeaways

1. Pick the cell of the 2×2 table (fwd/bwd × may/must) *from the English question*.
2. Write `gen`/`kill`; prove monotonicity (automatic for bitvectors).
3. Solve MFP with the worklist; do not enumerate paths.
4. At procedure boundaries, state the context policy.

## Connects To

- **Ch 4**: bitvector analyses are abstract interpretations of collecting semantics
- **Ch 6**: worklist
- **Ch 3**: when properties are sets of closures, not bitvectors
