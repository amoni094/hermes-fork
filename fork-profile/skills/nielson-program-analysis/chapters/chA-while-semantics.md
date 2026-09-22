# Appendix A: While Semantics

## Core Idea

Analyses are proved sound against a semantics, not against intuition. PPA uses **natural semantics** (big-step) and **structural operational semantics** (small-step) for While; collecting semantics packages executions into sets.

## Frameworks Introduced

### Natural semantics (NS)

Judgement `⟨S, s⟩ → s'` : statement S run from store s terminates in s'.

```
⟨[x:=a]^ℓ, s⟩ → s[x ↦ A⟦a⟧s]
⟨[skip]^ℓ, s⟩ → s
⟨S1, s⟩ → s''    ⟨S2, s''⟩ → s'
--------------------------------  (seq)
⟨S1; S2, s⟩ → s'
```

If: evaluate `B⟦b⟧s`; take then or else.
While: if test false, skip; if true, body then the loop again.

NS does not mention *intermediate* labels. Good for input/output behaviour; awkward for “property at ℓ”.

### Structural operational semantics (SOS)

Judgement `⟨S, s⟩ ⇒ ⟨S', s'⟩` or `⟨S, s⟩ ⇒ s'` (terminal).

Each step corresponds to executing one elementary block. The *trace* of labels is exactly a path in `flow(S)`.

This is the right semantics for dataflow soundness: if SOS can reach `ℓ` with store s, then `α({s}) ⊑ Analysis_∘(ℓ)`.

### Stores and arithmetic

`s: Var → Z`. `A⟦·⟧s` and `B⟦·⟧s` are the obvious interpretations. No heap in core While; heap/shape is Ch 2.5.

### Collecting semantics

`CS(ℓ) ⊆ Stores` = { s | some SOS derivation reaches label ℓ with store s }.

`CS` is the lfp of a monotone transformer on `P(Stores)^{Lab}`. Every Ch 2 analysis α-approximates `CS`.

### Partial vs total correctness

NS/SOS as given describe *terminating* executions. Properties of infinite loops need a coinductive / greatest-fixpoint reading (App C). Live-variable “x is live” is about *some* continuation, including finite traces; non-termination does not make a variable live.

## Mental Models

- NS = fold the whole statement. SOS = CFG step.
- If you cannot exhibit the SOS rule your transfer function abstracts, you cannot claim soundness.

## Anti-patterns

- **Proving an analysis against NS only**, then quoting per-label facts.
- **Assuming `while` always exits** when using `final(while) = {test}` — SOS can loop; must-analyses (AE, VB) are still sound because they quantify over *existing* paths; they do not claim the loop exits.

## Worked Example

`[x:=0]^1; [x:=x+1]^2`

SOS: `⟨S, s⟩ ⇒ ⟨[x:=x+1]^2, s[x↦0]⟩ ⇒ s[x↦1]`.
RD soundness: at entry of 2, `(x,1)` ∈ RD, matching the store’s last def of x.

## Key Takeaways

1. Lower scripts to While *and* say which semantics (SOS for labels).
2. Collecting semantics is the concrete domain C of Ch 4.
3. Non-termination is a liveness/coinduction issue, not a failure of RD/AE.

## Connects To

- **Ch 1**: flow extracted from the same syntax
- **Ch 4**: α(CS(ℓ)) ⊑ Analysis(ℓ)
- **Ch B/C**: lfp vs gfp, induction vs coinduction
