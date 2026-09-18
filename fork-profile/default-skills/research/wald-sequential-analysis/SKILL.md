---
name: wald-sequential-analysis
description: "Knowledge base from Sequential Analysis by Wald. Use when applying SPRT (sequential probability ratio test), optimal stopping, sequential hypothesis testing, OC curves, and ASN to agent retry decisions, metacognitive stopping rules, and evidence accumulation in Hermes."
related_skills:
  - test-driven-development
  - systematic-debugging
  - coding-conventions
  - cover-thomas-eit
  - sipser-theory-computation
  - adaptive-agent-reasoning
---

# Wald — Sequential Analysis (1947; 2nd printing Nov 1948)

Knowledge base from Abraham Wald *Sequential Analysis*, Wiley, 1947 (2nd printing Nov 1948). 222pp scan; full OCR completed Sep 2026 from 222 rasterized pages (/tmp/wald_pages/).

Source: ~/books/statistics/wald-sequential-analysis-djvu.pdf (image-based; OCR required and completed).

Wiley. Preface dated Columbia University, March 1947. Full OCR of all 222 pages now available in /tmp/wald_ocr_full.txt.

Load [references/cheatsheet.md](references/cheatsheet.md) for decision rules; [references/glossary.md](references/glossary.md) for terms; [chapters/](chapters/) for per-chapter deep content.

## When to use this skill

Stop-or-continue decisions: hypothesis tests, property-based sampling, retries, inspection, sequential estimation. Prefer SPRT over a fixed sample size when observations arrive one (or one group) at a time and Type I/II risks are preassigned.

**Hermes-specific:** Use when deciding whether accumulated retry evidence is sufficient to declare failure (SPRT stop rule), when estimating expected number of retries before a decision (ASN), when calibrating agent error rates (OC curves), or when building sequential confidence intervals on skill performance.

---

## Core framework: sequential vs fixed-n testing

A **current (Neyman–Pearson) test** draws a preassigned n, then accepts or rejects. To hit both α and β you must choose n from the worst-case pair of hypotheses (Ch 1.3.4).

A **sequential test** after each observation m chooses one of three sets (Ch 2.1): accept H₀ (Rₘ⁰), reject H₀ (Rₘ¹), or continue (Rₘ). Sample size n is a random variable. Two operating curves fully describe a sequential test:

- **OC function** L(θ) = P(accept H₀ | θ)
- **ASN function** E_θ(n) = expected sample number at θ

Requirements on the OC (Ch 2.3.2, eq. 2:2–2:3): split the parameter space into a **preference-for-acceptance** zone, a **preference-for-rejection** zone, and an **indifference** zone. Preassign α, β < 1:

- L(θ) ≥ 1 − α in the acceptance zone
- L(θ) ≤ β in the rejection zone
- indifference: no OC constraint; this is where ASN is usually largest

Select among tests that meet the OC constraints by minimizing the ASN (Ch 2.3.3).

---

## SPRT (Ch 3) — optimal stopping for simple H₀ vs simple H₁

Observations x₁, x₂, … i.i.d. with density/mass f(x, θ). Test H₀: θ = θ₀ against H₁: θ = θ₁.

**Likelihood ratio after m observations** (eq. 3:1):

```
Λ_m = p_{1m} / p_{0m} = ∏_{i=1..m} f(x_i, θ₁) / f(x_i, θ₀)
```

**Stopping rule.** Constants 0 < B < A:

- Λ_m ≤ B → accept H₀
- Λ_m ≥ A → accept H₁ (reject H₀)
- B < Λ_m < A → take another observation

Equivalently on the log scale: stop when S_m = ∑ z_i exits (log B, log A), where z_i = log f(x_i,θ₁)/f(x_i,θ₀).

### Type I / Type II error bounds (Ch 3)

Let α = P(reject H₀ | H₀), β = P(accept H₀ | H₁). Ignoring overshoot of the boundaries:

```
α / (1 − β)  ≤  1/A     (3:12)
β / (1 − α)  ≤  B       (3:13)
```

Weaker but immediate: α ≤ 1/A, β ≤ B (3:14–3:15).

**Practical constants** (Ch 3, determination of A and B; 3:21–3:22):

```
A ≈ (1 − β) / α
B ≈ β / (1 − α)
```

These slightly overshoot the nominal (α, β): the realized (α′, β′) still satisfy α′ ≤ α / (1 − β) and β′ ≤ β / (1 − α). For small α, β the inflation is negligible. Exact A(α,β), B(α,β) are laborious; use the approximation unless the overshoot matters (discrete, large steps).

You cannot drive both α and β to 0 without sending A → ∞ and B → 0, which sends ASN → ∞.

### Expected sample number (ASN) (Ch 3, § 3.6, eq. 3:55–3:57)

Wald's identity: E(S_n) = E(n) E(z) when E(|z|) < ∞ and n is the stopping time. Hence:

```
E_θ(n) ≈ [ L(θ) log B + (1 − L(θ)) log A ] / E_θ(z)
```

with L(θ) = P(accept H₀ | θ). At the two simple points, L(θ₀) ≈ 1 − α and L(θ₁) ≈ β.

When E_θ(z) ≈ 0 (indifference / no drift), this formula blows up; ASN is then of order (log A)² / Var(z) — still finite for SPRT with finite A, B, but large. A sequential procedure **without** absorbing boundaries (or truncation) can have **unbounded expected cost**.

SPRT terminates with probability 1 (Appendix A.1) under mild conditions on z.

### OC function approximation (Ch 3.5, App A.2, eq. A:19)

For the general parametric case, the OC function satisfies:

```
L(θ) ≈ (A^h(θ) − 1) / (A^h(θ) − B^h(θ))
```

where h(θ) is the unique nonzero real root of E_θ[exp(h·z)] = 1 (the "tilted" exponent from the Wald identity, App A.2.2).

For normal mean testing (σ known), h(θ) = (θ₀ + θ₁ − 2θ)/(θ₁ − θ₀).

### Efficiency vs fixed-n (Ch 3, "Saving in the number of observations")

A fixed-n test of strength (α, β) for a normal mean needs (3:67) n = (λ₁ − λ₀)² / (θ₀ − θ₁)². SPRT matches (α, β) with a **smaller expected n** (often ~40–60% of the fixed n at θ₀ and θ₁). Appendix A.7: SPRT is most efficient among tests with the same error probabilities — it minimizes E(n) at θ₀ and θ₁.

### Truncation and grouping (Ch 5.6–5.7)

Observations in groups inflate ASN slightly; Wald gives bounds (Table 3). Truncation (hard max n = n₀) is required in practice. Effect on error bounds:

```
α(n₀) ≤ α + [G(v₂) − G(v₁)]    (3:94)
β(n₀) ≤ β + [G(r₄) − G(r₃)]    (3:95)
```

where G is the standard normal CDF and v₁,v₂,r₃,r₄ depend on n₀, E(z), σ(z), log A, log B. Untruncated SPRT is the optimality benchmark, not always the deployed procedure.

---

## Composite hypotheses and weight functions (Ch 4, App. A.8–A.9)

For composite H, replace the simple likelihood ratio by a ratio of **weighted** likelihoods ∫ f(x, θ) w(θ) dθ. Sequential t-test (mean of a normal with unknown variance) is the worked case (Ch 4.2.3, App. A.9.2). Optimum weights exist in special classes (App. A.8, A.9).

---

## Applications in Part II: specific distributions

### Chapter 5: Binomial (lot inspection)

θ = p = proportion defective. H₀: p = p₀, H₁: p = p₁ (p₁ > p₀).
Log likelihood ratio per item: z_i = x_i log(p₁/p₀) + (1−x_i) log((1−p₁)/(1−p₀))
Graphical SPRT: plot cumulative defectives vs cumulative n; accept/reject boundaries are straight lines.

### Chapter 6: Two Binomials (double dichotomies)

Sequential test of p₁ ≥ p₂; pairs of observations (one from each group).

### Chapter 7: Normal mean, σ known, one-sided

H₀: μ = μ₀, H₁: μ = μ₁ (μ₁ > μ₀). z_i = (μ₁ − μ₀)/σ² · (x_i − (μ₀+μ₁)/2).
OC and ASN have explicit formulas (Ch 7.2–7.3).

### Chapter 8: Normal σ (variance testing)

H₀: σ ≤ σ₀, H₁: σ ≥ σ₁. Modification for unknown mean.

### Chapter 9: Normal mean, two-sided

Sequential plan for H₀: μ = μ₀ vs H₁: μ ≠ μ₀ (two-sided alternative).

---

## Multi-valued decisions and sequential estimation (Part III)

Ch 10: choose among k > 2 mutually exclusive hypotheses. A sequential plan is a sequence of continuation/decision regions; selection uses a **risk function** plus ASN (Ch 10.4). Uses product-of-likelihood-ratios inequality (10:7): ∏ Λ_m ≤ A gives rejection of H_j.

Ch 11: sequential estimation by intervals/sets — stop when the interval has the required coverage and length, rather than at fixed n. Special class: stop when the confidence set based on running likelihood satisfies diameter/coverage conditions.

---

## Appendix: Mathematical foundations

**A.1 — Termination with probability 1:** Under mild conditions (E|z| > 0), the SPRT terminates with probability 1. Proof via Wald's fundamental identity (A:16): E{e^(tz) · [φ(t)]^(−n)} = 1.

**A.2 — OC bounds:** Upper and lower limits for L(θ) via the fundamental identity and boundary overshoot analysis.

**A.3 — ASN bounds:** Upper and lower limits for E_θ(n) including overshoot corrections.

**A.4 — Tabular OC/ASN:** For specific distributions (binomial, normal).

**A.7 — SPRT efficiency:** Proof that SPRT minimizes E_θ₀(n) and E_θ₁(n) among all tests of equal strength. The efficiency ratio (2:4) differs from 1 by a negligible amount.

**A.8–A.9 — Optimum weights for composite tests:** Weighted likelihood ratio construction; sequential t-test derivation.

---

## Agent / coding applications

1. **Property-based tests** — do not fix N examples. SPRT-stop when the pass/fail likelihood ratio exits (B, A). See `test-driven-development`.
2. **Flakes vs gaps** — flakes are Type I (α); coverage holes are Type II (β). Different fixes. See `test-driven-development`.
3. **Bisect / binary search** — ASN of true bisection is log₂ N. More steps means you are exploring, not bisecting. See `systematic-debugging` Phase 2.
4. **Retry/backoff** — declare A, B, max-n *before* the loop. Unbounded sequential procedures have unbounded expected cost. See `coding-conventions`.
5. **Agent retry stop decision** — accumulate evidence (successes/failures) as SPRT observations; stop retrying when Λ_m exits (B, A). See [chapters/hermes-sprt-retry.md](chapters/hermes-sprt-retry.md).
6. **Metacognitive stopping** — use SPRT on metacognitive signals (confidence, tool-call diversity, progress rate) to decide when to stop self-reflection and act.
7. **Sequential confidence intervals on skill performance** — apply Ch 11 estimation to bound skill success rate p with coverage 1−α after each observed outcome.

---

## Chapter index

| # | Title | Key ideas |
|---|--------|-----------| 
| 1 | Elements of current (fixed-n) testing | α, β, critical region, n needed for preassigned errors |
| 2 | Sequential test: general discussion | OC, ASN, three zones, selection principles, efficiency |
| 3 | SPRT: simple H₀ vs simple H₁ | Λ_m, A/B, error inequalities, ASN (3:57), OC (3:43), truncation |
| 4 | General sequential tests (composite) | Weight functions, sequential t |
| 5 | Binomial mean / lot inspection | Tabular & graphical SPRT, grouping, truncation (Table 3) |
| 6 | Two binomials (double dichotomies) | Sequential test of p₁ ≧ p₂ |
| 7 | Normal mean, σ known, one-sided | SPRT, OC, ASN explicit formulas |
| 8 | Normal σ does not exceed a given value | SPRT; unknown mean modification |
| 9 | Normal mean equals a specified value | Two-sided sequential plan |
| 10 | Multi-valued decisions | Risk function + ASN, product LR inequality |
| 11 | Sequential estimation | Interval/set estimation with optional stopping |
| App | A.1–A.9 | Termination w.p. 1; fundamental identity; OC/ASN bounds; SPRT efficiency; optimum weights |

## Topic index

- **ASN / expected sample number** → Ch 2.2.2, Ch 3.6 (3:57), Ch 5.5, App A.3–A.4
- **Error bounds α, β / Type I / Type II** → Ch 1.3, Ch 2.3.2, Ch 3 (3:12–3:15)
- **Fundamental identity (Wald's identity)** → App A.2.2 (A:16)
- **Indifference zone** → Ch 2.3.1
- **Likelihood ratio Λ_m, z_i** → Ch 3
- **OC function L(θ)** → Ch 2.2.1, Ch 3.5, Ch 5.4, App A.2, A.4
- **Optimal stopping / SPRT efficiency** → Ch 2.4.1, Ch 3, App A.7
- **Sequential t-test** → Ch 4.2.3, App A.9.2
- **Termination with probability 1** → App A.1
- **Truncation / grouping** → Ch 5.6–5.7 (Table 3, eqs 3:94–3:95)
- **Weight functions (composite)** → Ch 4, App A.8–A.9

## Scope

Full 222-page OCR completed Sep 2026 from rasterized PNG files. Chapters/ directory contains extended per-chapter content derived from OCR. Combine with `test-driven-development`, `systematic-debugging`, `coding-conventions`, and `sipser-theory-computation` (for decidability framing of stopping decisions).
