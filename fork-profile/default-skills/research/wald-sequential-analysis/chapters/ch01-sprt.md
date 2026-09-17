# Chapter 1 & 3: SPRT — Sequential Probability Ratio Test

Source: Wald, *Sequential Analysis* Ch 1–3 (full OCR, Sep 2026).

---

## Setup (Ch 1 foundations)

i.i.d. observations x₁, x₂, … from distribution f(x, θ). Simple hypotheses:
- H₀: θ = θ₀
- H₁: θ = θ₁

**Fixed-n baseline (Ch 1.3.4):** To achieve both α and β with a fixed sample size n, you must solve for n = n(α, β) — the minimum n such that the most powerful test of size α has power ≥ 1 − β. This n can be large, especially when the two hypotheses are close.

**Sequential alternative:** Replace fixed n with a stopping rule based on accumulated evidence.

---

## SPRT Definition (Ch 3.1, eq. 3:1–3:6)

After m observations, compute the **probability ratio**:

```
Λ_m = p_{1m} / p_{0m}
     = ∏_{i=1}^{m} f(x_i, θ₁) / f(x_i, θ₀)
```

Choose constants 0 < B < 1 < A. At each step m:

| Condition | Action |
|-----------|--------|
| Λ_m ≥ A  | Stop → reject H₀ (accept H₁) |
| Λ_m ≤ B  | Stop → accept H₀ |
| B < Λ_m < A | Continue sampling |

**Log-sum form (eq. 3:4–3:6):** Let z_i = log[f(x_i, θ₁) / f(x_i, θ₀)]. Then S_m = z₁ + … + z_m and:

- S_m ≥ log A → reject H₀
- S_m ≤ log B → accept H₀
- log B < S_m < log A → continue

The log form is computationally preferred: S_m is a running sum, updated by adding one term per observation.

---

## Error Bounds (Ch 3.2–3.3, eq. 3:12–3:15)

Exact relations (without overshoot approximation):

```
α / (1 − β) ≤ 1/A      →   A ≥ (1 − β) / α        (3:12)
β / (1 − α) ≤ B        →   B ≤ β / (1 − α)         (3:13)
```

Simpler bounds: α ≤ 1/A, β ≤ B (eqs 3:14–3:15).

**Practical choice (Ch 3, determination of A and B):**

```
A ≈ (1 − β) / α
B ≈ β / (1 − α)
```

The realized (α′, β′) satisfy α′ + β′ ≤ α + β — the actual error sum is no larger than the nominal. For α, β both small (< 0.1), the approximation error is negligible.

**You cannot drive both errors to 0** without A → ∞, B → 0, ASN → ∞.

---

## Termination (App A.1)

**Theorem (A.1):** Under mild regularity (E|z| > 0 and z non-degenerate), the SPRT terminates with probability 1. Proof via Wald's fundamental identity:

```
E{ exp(t · S_n) · [φ(t)]^(−n) } = 1    (A:16)
```

where φ(t) = E[e^(tz)] is the moment generating function of z and n is the stopping time.

**Practical note:** The termination guarantee is asymptotic. In finite applications, always set a truncation limit n₀ (see ch03-truncation.md).

---

## Worked example: Bernoulli (Ch 5 / p.50)

x ∈ {0,1}, P(x=1) = p, H₀: p = p₀, H₁: p = p₁ (p₁ > p₀).

```
z_i = x_i · log(p₁/p₀) + (1 − x_i) · log((1−p₁)/(1−p₀))
```

Cumulative S_m = (# successes) · log(p₁/p₀) + (m − # successes) · log((1−p₁)/(1−p₀)).

Boundaries: log B, log A. Graphically, plot (m, cumulative defectives) and draw two parallel lines — a classic acceptance-sampling chart.

---

## SPRT optimality (Ch 2.4.1, App A.7)

Define efficiency of test S at θ_j as n_j*(α,β) / E_{θ_j}(n|S), where n_j* is the minimum possible E(n) over all tests of strength (α,β).

**Theorem (App A.7):** For SPRT S₀, the ratios

```
E_{θ₀}(n|S₀) / n₀*(α,β)   and   E_{θ₁}(n|S₀) / n₁*(α,β)
```

can exceed 1 by only a negligible quantity. As θ₁ → θ₀, both ratios → 1. SPRT is the practically optimal test.

**Implication for Hermes:** Among all binary stopping rules for agent retry, an SPRT-based rule has the minimum expected sample count at both hypotheses — it stops fastest on average while meeting the error rate budget.
