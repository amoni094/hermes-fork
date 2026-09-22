---
name: nielson-program-analysis
description: Use when deriving static analysis of scripts.
version: 1.0.0
author: Hermes Agent
license: MIT
related_skills:
  - sipser-theory-computation
  - clrs-algorithms
  - systematic-debugging
  - hermes-fork-bottleneck-audit
  - information-theory-for-agents
book_type: technical
depth: study
triggers:
  - static analysis of scripts
  - dataflow analysis
  - abstract interpretation
  - monotone framework
  - live variables
  - reaching definitions
  - available expressions
  - control flow analysis
  - widening narrowing
  - type and effect systems
metadata:
  hermes:
    tags: [static-analysis, dataflow, abstract-interpretation, lattices, cfa]
    related_skills:
      - sipser-theory-computation
      - clrs-algorithms
      - systematic-debugging
      - hermes-fork-bottleneck-audit
---

# Principles of Program Analysis
**Author**: Flemming Nielson, Hanne Riis Nielson, Chris Hankin | **Year**: 1999 (Springer) | **Chapters**: 6 + 3 appendices

Formal toolkit for deriving static analyses. Use it to *construct* a correct analysis (lattice + flow + monotone transfer functions + fixed point), not to hand-wave "the script looks unused".

Source PDF (`~/Downloads/Principles of Program Analysis.pdf`) is a 482-page scan with no text layer; this skill reconstructs the book's frameworks from canonical PPA 1999 content. Synthesized — not a transcription.

Load [cheatsheet.md](cheatsheet.md) for decision rules; [patterns.md](patterns.md) for named analyses; [glossary.md](glossary.md) for terms; chapter files on demand.

<!-- why: compaction keeps the first ~5k tokens; Hermes applications and the four classical analyses must stay above the fold -->

## When to Use

- Deriving a static check over Hermes scripts, skills, cron jobs, or gate predicates
- Formalising a bottleneck scanner as dataflow over an AST/CFG
- Auditing skill-router invocation chains as control-flow graphs
- Abstractly interpreting exit codes, effects, or alias sets
- Choosing may vs must, forward vs backward, MFP vs MOP, widening vs Kleene

Don't use for: runtime tracing (use observability skills); informal code review without a lattice (use requesting-code-review).

## Hermes applications (instantiate the book here)

### 1. Bottleneck scanner → intraprocedural dataflow on script ASTs

Build `flow(S*)` from the script AST (assignments, `if`, `while`, function calls as unknown `skip` until Ch 2.4).

| Check | Analysis | Catches |
|---|---|---|
| Dead write | **Reaching definitions** (fwd, may, ∪) | def at `ℓ` never reaches a use; write killed before read |
| Unused import / binding | **Live variables** (bwd, may, ∪) | name not in `LV_entry` of program — dead on arrival |
| Redundant recompute | **Available expressions** (fwd, must, ∩) | `a` ∈ AE_entry(ℓ) ⇒ CSE / skip re-eval |
| Hoistable invariant | **Very busy expressions** (bwd, must, ∩) | `a` very busy at loop header ⇒ code motion |

Completion: every CFG node has `Analysis_∘` / `Analysis_•`; every alarm cites `(gen, kill, ℓ)`.

### 2. Skill router → control-flow graph of invocation chains

Treat `skill_view(name)` / chained skills as calls. Nodes = skills; edges = `related_skills` ∪ body `skill_view` ∪ trigger overlap. Run **0-CFA** (Ch 3) if dispatch is higher-order (router closure selects a skill at runtime). k-CFA when the last k call sites change the target.

Alarm if the CFG has an unreachable required skill, or a cycle with no widening/fuel (non-termination of the *router*, not the analysis).

### 3. Gate-audit → abstract interpretation on the exit-code lattice

Concrete exits: integers. Abstract domain (flat):

```
            ⊤  (unknown / mixed)
         /   |   \
       ok  cold  error
         \   |   /
            ⊥  (unreachable)
```

Galois: `α({0}) = ok`, `α({cold-start codes}) = cold`, `α({n | n≠ 0})` join as needed, `α(∅) = ⊥`, more than one constructor ⇒ `⊤`.

Transfer: a gate is sound iff `α ∘ F ⊑ F^# ∘ α`. Join at merge points. Do not treat `⊤` as `ok`.

Severity chain (optional, when only worst-case matters): `ok ⊑ cold-start ⊑ error`.

### 4. Cron → script → library → interprocedural analysis

Call graph: cron entry → wrapper → library. Context-insensitive = one abstract summary per function (cheap, polluted). Context-sensitive = call-string length k or functional approach (Ch 2.4). Alias / shape at interproc boundaries if scripts share files or env vars (may-alias of `PATH`, lockfiles).

## Core frameworks

### While (the metalanguage)

```
a ::= n | x | a1 + a2 | a1 * a2 | a1 - a2
b ::= true | false | a1 = a2 | a1 < a2 | ¬b | b1 ∧ b2
S ::= [x := a]^ℓ | [skip]^ℓ | S1; S2
    | if [b]^ℓ then S1 else S2 | while [b]^ℓ do S
```

Labels mark elementary blocks. `init(S)`, `final(S)`, `flow(S) ⊆ Lab × Lab`, `blocks(S)`.

### Four classical bitvector analyses (Ch 2.1)

Transfer always `f_ℓ(S) = (S \ kill(B^ℓ)) ∪ gen(B^ℓ)`.

| | Direction | Combine | Lattice order ⊑ | ⊥ | Extremal ι |
|---|---|---|---|---|---|
| **AE** available expr | forward | ∩ (must) | ⊇ | AExp_* | ∅ |
| **RD** reaching def | forward | ∪ (may) | ⊆ | ∅ | {(x,?) | x ∈ FV} |
| **VB** very busy expr | backward | ∩ (must) | ⊇ | AExp_* | ∅ |
| **LV** live vars | backward | ∪ (may) | ⊆ | ∅ | ∅ |

Forward: `F = flow(S*)`, `E = {init(S*)}`, `∘` = entry, `•` = exit.
Backward: `F = flow^R(S*)`, `E = final(S*)`, `∘` = exit, `•` = entry.

Equations:

```
Analysis_∘(ℓ) = ι                          if ℓ ∈ E
              = ⨅ { Analysis_•(ℓ') | (ℓ',ℓ) ∈ F }   otherwise
Analysis_•(ℓ) = f_ℓ(Analysis_∘(ℓ))
```

### Monotone framework (Ch 2.2)

A 6-tuple `(L, ℱ, F, E, ι, f)`:

- `L` complete lattice of properties (finite height ⇒ termination of Kleene)
- `ℱ` space of monotone transfer functions `L → L`, closed under composition and containing `id`
- `F` flow (fwd or reverse)
- `E` extremal labels
- `ι ∈ L` extremal value
- `f: Lab → ℱ` assigns `f_ℓ`

**Distributive** framework: each `f_ℓ` preserves ⊔. Then **MFP = MOP**. Otherwise MFP ⊑ MOP (MFP is the safe computable under-approximation in the lattice order).

Never compute MOP by enumerating paths through loops. Compute MFP with the worklist (Ch 6).

### Knaster–Tarski + Kleene

Monotone `f: L → L` on a complete lattice:

```
lfp(f) = ⨅ { x | f(x) ⊑ x }
gfp(f) = ⨆ { x | x ⊑ f(x) }
```

If `f` is continuous (preserves ⋃ of chains): `lfp(f) = ⋃_n f^n(⊥)`.

Iterate from `⊥` for least (may-analysis start); from `⊤` for greatest when the lattice is reversed (must).

### Abstract interpretation (Cousot & Cousot, Ch 4)

Galois connection `(C, α, γ, A)`:

```
α(c) ⊑_A a   ⟷   c ⊑_C γ(a)
```

equivalently `id_C ⊑ γ∘α` and `α∘γ ⊑ id_A`.

Best transformer: `f^# = α ∘ f ∘ γ`. Any `f^#` with `α ∘ f ⊑ f^# ∘ α` is **sound**.

**Widening** `∇`: `x,y ⊑ x ∇ y`, and increasing iterates with `∇` stabilise (even on infinite-height lattices, e.g. intervals).
**Narrowing** `∆`: `y ⊑ x ⇒ y ⊑ x ∆ y ⊑ x`, used *after* widening to regain precision without breaking termination.

Anti-pattern: widening at every node. Widen only at loop headers / back-edges.

### Control-flow analysis (Ch 3)

For higher-order `Fun`: 0-CFA = one abstract closure set per labelled term (context-insensitive). k-CFA indexes by the last k call sites. Generate subset constraints; solve by worklist on the constraint graph.

Use 0-CFA for skill-router closures; bump k only when context collision is witnessed.

### Type and effect systems (Ch 5)

Judgement `Γ ⊢ e : τ & φ` — term has type `τ` and latent/actual effect `φ`. Function types `τ1 --φ--> τ2`. Subeffecting `φ ⊑ φ'` before subsumption. Inference = constraint generation + unification / set-union.

Map Hermes effects: `{read, write, net, spawn, exit}` as `φ`.

## Decision rules (always)

1. If the question is "can this fact *possibly* hold?" → **may**, join `∪`, start `⊥=∅`.
2. If "does this fact *definitely* hold?" → **must**, join `∩`, lattice order reversed.
3. If information flows to successors → **forward**. If it depends on the future → **backward**.
4. If the lattice has infinite height (intervals, constants with ⊤) → **widen** at back-edges, then **narrow**.
5. If higher-order / first-class skill values → **CFA**, not bitvector DFA.
6. If call/return matters → interprocedural (call strings or functional); do not smash all callers into one summary unless you accept pollution.
7. Soundness beats precision. A true alarm may be extra; a missed dead-write is a failed analysis.

## Chapter Index

| # | Title | Key frameworks |
|---|---|---|
| [ch01](chapters/ch01-introduction.md) | Introduction | While, labels, flow, soundness vs completeness |
| [ch02](chapters/ch02-data-flow-analysis.md) | Data Flow Analysis | AE, RD, VB, LV, monotone frameworks, interproc, shape/alias |
| [ch03](chapters/ch03-constraint-based-analysis.md) | Constraint Based Analysis | Fun, 0-CFA, k-CFA, subset constraints |
| [ch04](chapters/ch04-abstract-interpretation.md) | Abstract Interpretation | Galois, collecting semantics, widen/narrow |
| [ch05](chapters/ch05-type-and-effect-systems.md) | Type and Effect Systems | annotated types, effects, inference |
| [ch06](chapters/ch06-algorithms.md) | Algorithms | worklist, chaotic iteration, MFP |
| [chA](chapters/chA-while-semantics.md) | App A: Semantics | NS, SOS, collecting semantics |
| [chB](chapters/chB-lattices-fixed-points.md) | App B–C: Orders | complete lattices, Tarski, induction |

## Topic Index

- **alias / shape / points-to** → ch02
- **available expressions** → ch02, cheatsheet
- **CFA / 0-CFA / k-CFA** → ch03
- **Galois connection** → ch04, chB
- **interprocedural / call strings** → ch02
- **live variables** → ch02
- **monotone framework** → ch02, ch06
- **MOP vs MFP** → ch02, ch06
- **reaching definitions** → ch02
- **Tarski / Kleene** → chB, ch02
- **type and effect** → ch05
- **very busy expressions** → ch02
- **widening / narrowing** → ch04
- **worklist** → ch06

## Supporting Files

- [glossary.md](glossary.md) — terms
- [patterns.md](patterns.md) — named analyses and recipes
- [cheatsheet.md](cheatsheet.md) — decision tables

## Common Pitfalls

- Using `∪` for a must-analysis (optimistic unsoundness).
- Forgetting extremal `ι` (AE must start with ∅ at `init`, not ⊥ of the reversed lattice).
- Widening everywhere; or narrowing before a stable widen post-fixpoint.
- Treating MFP as path-exact when transfer functions are not distributive.
- 0-CFA on a context-sensitive bug (polluted closures ⇒ false callees).
- Conflating may-alias with must-alias in lock/file reasoning.

## Verification Checklist

- [ ] Lattice stated: carrier, ⊑, ⊔, ⊥, ⊤, height finite?
- [ ] Direction + may/must justified by the question asked
- [ ] `gen`/`kill` or `f_ℓ` monotone (prove or cite bitvector form)
- [ ] Extremal labels and `ι` set
- [ ] Solver: worklist / Kleene / widen-narrow; termination argument
- [ ] Soundness: `α∘f ⊑ f^#∘α` or MFP ⊑ MOP story
- [ ] Each alarm maps to a concrete program point `ℓ`
