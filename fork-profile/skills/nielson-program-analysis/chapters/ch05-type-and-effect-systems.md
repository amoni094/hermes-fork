# Chapter 5: Type and Effect Systems

## Core Idea

A type system is a static analysis whose lattice is a *syntax of types* (often with subtyping). Effect systems annotate judgements with a summary of latent computational effects. Inference generates constraints; solving them is the analysis.

## Frameworks Introduced

### Simply typed skeleton

```
Γ ⊢ n : int
Γ ⊢ x : Γ(x)
Γ ⊢ λx.e : τ1 → τ2          if  Γ[x:τ1] ⊢ e : τ2
Γ ⊢ e1 e2 : τ2              if  Γ ⊢ e1 : τ1 → τ2  and  Γ ⊢ e2 : τ1
```

Soundness: well-typed programs do not go wrong (progress + preservation wrt SOS). This is a *must* analysis of safety, not a may-analysis of reachability.

### Effect systems

Judgement `Γ ⊢ e : τ & φ` where `φ` is an effect (set, or more structured algebra).

Function types carry a *latent* effect:

```
τ  ::=  int | τ1 --φ--> τ2
φ  ::=  ∅ | {ε} | φ1 ∪ φ2 | …
```

Application *discharges* the latent effect into the actual effect of the call.

**Subeffecting**: `φ ⊑ φ'` (usually ⊆) and subsumption:

```
Γ ⊢ e : τ & φ     φ ⊑ φ'
-------------------------
Γ ⊢ e : τ & φ'
```

Subtyping of function types is *contravariant* in the argument, *covariant* in the result, *covariant* in the latent effect (or contra, depending on whether effects are permissions vs obligations — pick one and stick to it; PPA treats effects as over-approximated sets of events, covariant).

### Annotated type systems

Types decorated with the same properties dataflow would compute: e.g. `int^ℓ` with program-point annotations, or binding-time annotations, or region annotations. The type derivation *is* the analysis certificate.

### Behaviours

Effects refined to traces / CCS-like behaviours. Useful when order of effects matters (lock; use; unlock vs use; lock). Subeffecting becomes simulation / trace inclusion.

### Inference

1. Assign type/effect variables to subterms.
2. Generate equalities (unification) and inclusions (subtype / subeffect).
3. Solve: unification for `=` ; worklist on a constraint graph for `⊆`.

Decidability depends on the annotation language. Finite-set effects: polynomial. Polymorphic effects / higher-rank: watch undecidability.

## Hermes effect algebra (recommended)

```
ε ::= read | write | net | spawn | exit | skill
φ ::= P(ε)     ⊔ = ∪     ⊥ = ∅     ⊤ = all
```

- `read`: files, env, skill docs
- `write`: fs, memory files, config
- `net`: web_search / browser
- `spawn`: subagent, cron, process
- `exit`: process termination / gate
- `skill`: `skill_view` / dynamic load

Sequential composition: `φ1 ∪ φ2`. Function abstraction: latent `φ`. A gate-audit that claims “no net” must infer `net ∉ φ`.

Combine with Ch 4 exit lattice: `exit` effect *plus* abstract code `{ok, cold, error, ⊤}`.

## Mental Models

- Types = must-safety. Effects = may-summary of extra-computational events (when φ is a set union).
- Dataflow annotates *labels*. Type/effect annotates *terms* and binders. Same math (monotone constraints).
- Latent vs actual: `λ. e` has actual effect ∅ and latent effect of `e`.

## Anti-patterns

- **Putting actual I/O in the type of a lambda that is never called**: that is confusing latent with actual; unused `web_search` inside a dead branch should not taint the program effect if you run a *must*-effect (rare) or dead-code+effect combo. Default set-union effects *will* taint — compose with LV/CFA to drop dead code first.
- **Invariant function subtyping**: `τ1→τ2` is not covariant in `τ1`.
- **Unification-only solver for inclusion constraints**: will reject safe subeffecting.

## Worked Example

```
f = λp. (web_search(p); 0)
g = λp. 0
h = if cond then f else g
h("q")
```

Effect of `h`: latent `{net}` under 0-CFA (may call `f`). Actual effect of the application includes `net`. A gate “this cron is net-free” fails.

If CFA proves `cond` is constantly false, `f` is dead, `φ = ∅`. Do not claim net-free without that proof.

## Key Takeaways

1. Write the judgement form first (`Γ ⊢ e : τ & φ`).
2. Effects are a lattice; state ⊔ and ⊑.
3. Infer by constraints; solve with unification + worklist.
4. Dead code pollutes may-effects — run CFA/LV first when “no spawn/net” is a gate.

## Connects To

- **Ch 3**: CFA as a type system with set-types of closures
- **Ch 2**: effects as a forward may-analysis on a CFG
- **Ch 4**: type soundness as a Galois connection between typed and untyped collecting semantics
