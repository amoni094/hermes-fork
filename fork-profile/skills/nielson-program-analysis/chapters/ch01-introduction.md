# Chapter 1: Introduction

## Core Idea

A program analysis is a *computable, sound approximation* of a semantic property. Soundness is with respect to an operational semantics of **While**; labels on elementary blocks are the analysis program points.

## Frameworks Introduced

- **Labelled While**: every assignment, `skip`, and test carries a unique label `ℓ ∈ Lab`. Analyses talk about `blocks(S)`, `init(S)`, `final(S)`, `flow(S)`, `FV(S)`, `AExp_*`.
  - When to use: any script you can lower to While (straight-line, `if`, `while`, env assignments).
  - How: parse AST → assign labels → extract CFG `flow(S*) ⊆ Lab × Lab`.
- **Static vs dynamic**: the analysis must terminate on all programs and over-approximate the collecting semantics. Completeness (no false alarms) is optional and usually abandoned.
- **Correctness criterion**: if the analysis says “P cannot happen at `ℓ`”, then no execution reaching `ℓ` exhibits P. The converse may fail (false positives).

## Key Concepts

- **Elementary block** `B^ℓ`: `[x:=a]^ℓ`, `[skip]^ℓ`, or test `[b]^ℓ`.
- **init(S)**: unique entry label. **final(S)**: set of labels from which control may leave S.
- **flow(S)**: intra-procedural CFG edges. `flow^R` reverses them for backward analyses.
- **AExp_***: non-trivial arithmetic expressions occurring in S (not a lone variable or constant, depending on presentation — PPA uses non-trivial subexpressions).
- **FV**: free variables of an expression or statement.
- **Soundness vs completeness**: sound ⇒ missed bugs are forbidden; extra alarms allowed.

## Mental Models

- Think of the CFG as the *control skeleton* and the lattice as the *property algebra*. Neither alone is an analysis.
- Use labels, not source lines: one line can lower to several blocks (`if` test + two arms).
- Prefer a coarse sound analysis over a precise unsound one when the consumer is a gate (exit-code audit, unused-import fail).

## Anti-patterns

- **Unlabelled AST walks**: “this assignment looks unused” without `flow` and a transfer function — not an analysis.
- **Executing the script to see properties**: that is testing, not program analysis; loops and cold-start paths are missed.
- **Demanding completeness**: constant propagation and dead-code are not complete on Turing-complete scripts.

## Reference Tables

| Syntactic form | init | final | flow (sketch) |
|---|---|---|---|
| `[x:=a]^ℓ` / `[skip]^ℓ` | `{ℓ}` | `{ℓ}` | ∅ |
| `S1; S2` | `init(S1)` | `final(S2)` | `flow(S1) ∪ flow(S2) ∪ (final(S1)×{init(S2)})` |
| `if [b]^ℓ then S1 else S2` | `{ℓ}` | `final(S1) ∪ final(S2)` | `{(ℓ, init(S1)), (ℓ, init(S2))} ∪ flow(S1) ∪ flow(S2)` |
| `while [b]^ℓ do S` | `{ℓ}` | `{ℓ}` | `{(ℓ, init(S))} ∪ flow(S) ∪ (final(S)×{ℓ})` |

## Worked Example

Script fragment:

```
[x := 1]^1; while [x < 10]^2 do [x := x + 1]^3
```

- `init = 1`, `final = {2}`
- `flow = {(1,2), (2,3), (3,2)}`
- This CFG is the input to every Ch 2 analysis. RD will show `(x,1)` reaching 2 on the first iteration and `(x,3)` thereafter; LV will show `x` live at 2 and 3.

Hermes: a cron wrapper `PATH=...; run.sh` is `S1; S2` with flow edge from the assignment block into the call (later: interprocedural).

## Key Takeaways

1. Lower the script to labelled While (or an honest superset) before inventing transfer functions.
2. `flow` is data; the lattice is the specification of *what* you compute.
3. Soundness is a theorem about `α` and the semantics, not a vibe.
4. False alarms are the price of termination; record the approximation that caused them.

## Connects To

- **Ch 2**: instantiates flow with AE/RD/VB/LV
- **Ch A**: natural and structural operational semantics the analyses are sound for
- **Hermes bottleneck scanner**: AST → labels → flow
