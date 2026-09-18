# Wald Sequential Analysis — cheatsheet

## Decision: stop vs continue

When X (data so far), do Y, because Z:

- **Fixed n already meets (α, β)** → use the current test. Sequential savings are small if n is already tiny.
- **Observations arrive one-by-one and both error rates matter** → SPRT with A ≈ (1−β)/α, B ≈ β/(1−α).
- **Composite alternative** → weighted likelihood ratio (Ch 4), not a naive plug-in MLE ratio.
- **Must not exceed n_max** → truncate; expect OC/ASN distortion (Ch 5.7).
- **Indifference zone / E(z)≈0** → expect large n; do not treat "still running" as evidence of correctness.
- **No pre-set A, B, or n_max** → do not ship. Unbounded sequential procedures have unbounded expected cost.

## SPRT loop

1. Preassign α (Type I), β (Type II), θ₀, θ₁.
2. Set A = (1−β)/α, B = β/(1−α).
3. S ← 0.
4. Observe x; S ← S + log f(x,θ₁)/f(x,θ₀).
5. If S ≥ log A: reject H₀. If S ≤ log B: accept H₀. Else goto 4.

## Error bounds (Ch 3)

| Bound | Formula |
|-------|---------|
| Tight | α/(1−β) ≤ 1/A ; β/(1−α) ≤ B |
| Crude | α ≤ 1/A ; β ≤ B |
| Constants | A ≈ (1−β)/α ; B ≈ β/(1−α) |

Driving α and β both →0 forces A→∞, B→0, ASN→∞.

## ASN (expected sample number)

```
E_θ(n) ≈ [ L(θ) log B + (1−L(θ)) log A ] / E_θ(z)
```

At θ₀: L ≈ 1−α. At θ₁: L ≈ β. Minimize ASN among tests that meet the OC — that is SPRT (App A.7).

Bisection analogue: E(steps) = log₂ N. Mean ≫ log₂ N ⇒ not bisecting.

## Three zones (Ch 2.3.1)

| Zone | Meaning | OC demand |
|------|---------|-----------|
| Prefer accept | wrong reject is costly | L(θ) ≥ 1−α |
| Indifference | either decision acceptable | none; ASN peaks |
| Prefer reject | wrong accept is costly | L(θ) ≤ β |

## Tells

- Stopping at a round number (100, 1000) with no A/B → fixed-n habit, not sequential.
- Loop with `while True` and no max n → unbounded expected cost.
- Treating every test failure the same → mixing α-failures (flakes) with β-failures (gaps).
- Many extra git-bisect steps past log₂ N → exploring, not isolating.
