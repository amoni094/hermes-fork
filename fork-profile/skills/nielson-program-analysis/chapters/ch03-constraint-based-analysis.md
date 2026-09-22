# Chapter 3: Constraint Based Analysis

## Core Idea

For higher-order programs the CFG is not syntax-directed: callees are *computed*. Generate subset constraints whose least solution is an abstract control-flow graph (CFA), then optionally layer dataflow on that graph.

## Frameworks Introduced

### Fun language

```
e ::= x | λx.e | e1 e2 | if e0 then e1 else e2 | …  (labelled)
```

Values are closures `(λx.e, ρ)`. Abstract values are *abstract closures* `(λx.e, ρ̂)` or, in 0-CFA, just λ-terms (environment collapsed).

### 0-CFA (context-insensitive)

Abstract cache `Ĉ: Lab → P(AbsVal)` and abstract environment `ρ̂: Var → P(AbsVal)`.

Syntax-directed constraints (sketch):

```
x^ℓ                    :  Ĉ(ℓ) ⊇ ρ̂(x)
(λx.e)^ℓ               :  Ĉ(ℓ) ⊇ { λx.e }
(e1^{ℓ1} e2^{ℓ2})^ℓ    :  ∀ (λx.e^{ℓb}) ∈ Ĉ(ℓ1).
                            ρ̂(x) ⊇ Ĉ(ℓ2) ∧ Ĉ(ℓ) ⊇ Ĉ(ℓb)
```

Plus if-branches: `Ĉ(ℓ_then) ∪ Ĉ(ℓ_else)` flows to the join label.

Least solution of the finite subset-constraint system = 0-CFA result. Always exists (finite lattice `P(AbsVal)^n`); compute by worklist on the constraint graph.

Precision: every syntactic λ that *might* flow to a call site is assumed to be called there. Over-approximation of actual call graph.

### k-CFA (Shivers)

Index `Ĉ` and `ρ̂` by a *contour* (call string) of length k. At a call, the new contour is `push(ℓ_call, κ)` truncated to k. Exponential in k; 1-CFA already expensive. Use k=0 unless a witnessed context collision pollutes a Hermes router.

### Constraint generation vs iterative dataflow

CFA is still a monotone framework on `L = P(AbsVal)^{Lab ∪ Var}`. Writing it as constraints makes the *acceptability* condition obvious: a pair `(Ĉ, ρ̂)` is acceptable if it satisfies every generated inclusion. The analysis is the *least* acceptable pair.

Adding classical dataflow: once Ĉ gives may-call edges, run RD/LV on that (approximate) CFG. Sound relative to Ĉ’s soundness.

### Theoretical properties

- **Existence**: finite complete lattice + monotone operator ⇒ Tarski.
- **Soundness**: α of collecting semantics ⊑ Ĉ (every concrete closure is represented).
- **Complexity**: 0-CFA is polynomial (cubic typical); k-CFA is EXPTIME-complete for k≥1 in general.

## Mental Models

- Bitvector DFA *assumes* the CFG. CFA *discovers* the CFG.
- 0-CFA = “one bucket per variable / label”. k-CFA = “k last calls as a key into the bucket array”.
- Constraints are just a presentation of `x ⊑ f(x)` includes.

## Anti-patterns

- **Using While-flow on a Python/JS callback**: missing edges; unsound live-var.
- **Jumping to 1-CFA “for precision”** without a collision example — cost cliff.
- **Treating Ĉ(ℓ) as must-call**: it is a *may* set. Must-CFA needs a dual (universal) constraint system and is rarely worth it.
- **Forgetting environment in closures** when language has mutable cells (need abstract store; see shape/alias).

## Worked Example — skill router

```
router = λq. (if match(q, "pdf") then ingest else audit)
router(user_query)
```

0-CFA: `Ĉ(call) ⊇ {ingest, audit}`. CFG edges from the call to both skills. Alarm “audit not reached” is *not* justified (may-analysis). Alarm “ingest may run on a non-pdf query” *is* justified if `match` is abstracted as unknown bool.

If `router` is applied in two cron contexts (nightly ingest vs gate-audit) and 0-CFA smashes them, 1-CFA with call-site contour separates the two.

## Hermes applications

- Skill router: nodes = skills; 0-CFA on first-class skill values / dynamic `skill_view(name=expr)`.
- Higher-order Hermes tools (`delegate_task` with a closure-like prompt): abstract the callee as a set of role skills.
- Do not run AE/LV on a script with callbacks until CFA has produced `flow`.

## Key Takeaways

1. No CFG ⇒ no bitvector analysis; run CFA first.
2. 0-CFA is the default; increase k only with evidence.
3. Solve subset constraints by worklist; the solution *is* the abstract call graph.
4. Compose: CFA edges + Ch 2 transfer functions.

## Connects To

- **Ch 2.4**: interprocedural dataflow on the discovered graph
- **Ch 4**: Ĉ is an abstract interpretation of the collecting semantics of Fun
- **Ch 6**: constraint worklist
