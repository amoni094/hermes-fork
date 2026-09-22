# Cheatsheet — Nielson, Nielson, Hankin (1999)

## Four classical analyses

| | AE | RD | VB | LV |
|---|---|---|---|---|
| Question | definitely computed already? | which defs may hold? | definitely used later? | which vars may be used later? |
| Direction | forward | forward | backward | backward |
| ⊔ | ∩ | ∪ | ∩ | ∪ |
| ⊑ | ⊇ | ⊆ | ⊇ | ⊆ |
| ⊥ | AExp_* | ∅ | AExp_* | ∅ |
| ι | ∅ | {(x,?)|x∈FV} | ∅ | ∅ |
| F | flow | flow | flow^R | flow^R |
| E | {init} | {init} | final | final |
| Hermes | skip recompute | dead write / uninit | hoist | unused import |

Transfer (all four): `f_ℓ(S) = (S \ kill(B^ℓ)) ∪ gen(B^ℓ)`.

### gen / kill (assignments)

```
AE  gen = non-killed subexpr of a     kill = {a' | x ∈ FV(a')}
RD  gen = {(x,ℓ)}                     kill = all other defs of x, incl (x,?)
VB  gen = subexpr of a                kill = {a' | x ∈ FV(a')}
LV  gen = FV(a)                       kill = {x}
```

Tests: gen from the boolean; kill empty (except AE/VB as above). `skip`: gen=kill=∅.

## Monotone framework

`(L, ℱ, F, E, ι, f)` with f_ℓ monotone.

```
Analysis_∘(ℓ) = ι                          ℓ ∈ E
              = ⨅ { Analysis_•(ℓ') | (ℓ',ℓ) ∈ F }
Analysis_•(ℓ) = f_ℓ(Analysis_∘(ℓ))
```

- Distributive f_ℓ ⇒ **MFP = MOP**.
- Else **MFP ⊑ MOP** (safe).

## Tarski / Kleene

```
lfp(f) = ⊓ { x | f(x) ⊑ x } = ⊔_n f^n(⊥)   (continuous / finite height)
gfp(f) = ⊔ { x | x ⊑ f(x) }
Park:  f(x) ⊑ x  ⇒  lfp(f) ⊑ x
```

## Galois / soundness

```
α(c) ⊑ a  ⟷  c ⊑ γ(a)
α ∘ f  ⊑  f^# ∘ α
f^#_best = α ∘ f ∘ γ
```

## Widen / narrow

```
x,y ⊑ x ∇ y     increasing y_{i+1}=y_i ∇ x_{i+1}  stabilises
y ⊑ x ⇒ y ⊑ x ∆ y ⊑ x     decreasing stabilises
```

Widen **only** at back-edges. Narrow **after** widen stability. Intervals: jump to ±∞ on unstable bounds.

## 0-CFA constraints

```
x^ℓ :                 Ĉ(ℓ) ⊇ ρ̂(x)
(λx.e)^ℓ :            Ĉ(ℓ) ⊇ {λx.e}
(e1^{ℓ1} e2^{ℓ2})^ℓ : ∀ λx.e^{ℓb} ∈ Ĉ(ℓ1).
                      ρ̂(x) ⊇ Ĉ(ℓ2) ∧ Ĉ(ℓ) ⊇ Ĉ(ℓb)
```

k-CFA: index by last k call sites. Default k=0.

## Worklist

Init `ι` at E, `⊥` elsewhere. While edge `(ℓ,ℓ')` dirty: if `f_ℓ(A_∘(ℓ)) ≰ A_∘(ℓ')`, join it in, dirty successors.

## Exit-code lattice (gate-audit)

```
        ⊤
     /  |  \
   ok  cold  error
     \  |  /
        ⊥
```

`α({0})=ok`. Mixed ⇒ ⊤. Do not read ⊤ as ok.

Severity chain: `ok ⊑ cold-start ⊑ error` (⊔ = worse).

## Effect algebra (Hermes)

`φ ⊆ {read, write, net, spawn, exit, skill}`, ⊔=∪. Latent on `τ1 --φ--> τ2`. Dead-code first, then infer.

## Interprocedural

| Policy | Precision | Cost |
|---|---|---|
| insensitive (one summary) | low, polluted | cheap |
| call-string k | exact if k ≥ max depth, acyclic | |Lab|^k |
| functional map L→L | good on recursion | cache of maps |

## Decision tree

1. Higher-order / unknown callee? → CFA then dataflow.
2. May or must? → ∪/⊆ or ∩/⊇.
3. Past or future? → forward or backward.
4. Infinite height? → widen at back-edges.
5. Call/return mixing? → k-CFA or call strings.
6. Extra-computational events? → effects after dead-code.
