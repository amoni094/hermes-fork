# Ch 2-3 — PAC Learning, ERM, Agnostic PAC

> Covers Chapters 2 (A Gentle Start), 3 (A Formal Learning Model), 4 (Uniform Convergence), 6 (VC Dimension), 7 (Nonuniform Learnability).

## 2.1 Statistical Learning Framework

- **Domain** X, **Label set** Y (typically {0,1} or {-1,+1})
- **Distribution** D over X×Y (unknown to learner)
- **Hypothesis class** H: set of candidate predictors h: X → Y
- **True risk**: L_D(h) = Pr_{(x,y)~D}[h(x) ≠ y]
- **Empirical risk**: L_S(h) = (1/m) ∑_i 1[h(x_i) ≠ y_i] over sample S of size m

## 3.1 PAC Learning (Realizability Assumption)

Assume ∃ h* ∈ H with L_D(h*) = 0 (realizable).

**PAC learnable**: H is PAC learnable if ∃ algorithm A and polynomial m(ε,δ) such that for any ε,δ ∈ (0,1) and any D with a realizable h*:
```
Pr_{S~D^m}[L_D(A(S)) > ε] ≤ δ    whenever m ≥ m(ε,δ)
```

**Sample complexity for finite H** (ERM):
```
m ≥ (1/ε) · (ln|H| + ln(1/δ))
```

## 3.2 Agnostic PAC Learning (No Realizability)

No assumption on H. Learner competes against best h ∈ H:
```
L_D(A(S)) ≤ min_{h∈H} L_D(h) + ε    with probability ≥ 1-δ
```

**Uniform convergence** is sufficient: if |L_S(h) - L_D(h)| ≤ ε/2 for all h ∈ H simultaneously, then ERM is agnostic PAC learner.

## 4.1-4.2 Uniform Convergence

**Finite H** (Corollary 4.6): For any δ ∈ (0,1):
```
Pr[ ∃h∈H: |L_S(h) - L_D(h)| > ε ] ≤ 2|H|·exp(-2mε²)
```

Setting δ = 2|H|·exp(-2mε²), solving for m:
```
m ≥ (1/(2ε²)) · ln(2|H|/δ)
```

## 6.2-6.4 VC Dimension

**Shattering**: H shatters C ⊆ X if {h|_C : h∈H} = all labelings of C.

**VC dimension**: VCdim(H) = max size of shattered set.

**Fundamental Theorem** (Theorem 6.7): H is PAC learnable iff VCdim(H) < ∞.

**Sample complexity** (agnostic, VCdim d = VCdim(H)):
```
C₁·(d + ln(1/δ))/ε² ≤ m_H(ε,δ) ≤ C₂·(d·ln(1/ε) + ln(1/δ))/ε²
```

Standard simplified form:
```
m ≥ (1/ε²) · (d·ln(1/ε) + ln(1/δ))
```

**Examples**:
- Threshold functions on R: VCdim = 1
- Intervals on R: VCdim = 2
- Halfspaces in R^d: VCdim = d+1
- Finite class H: VCdim ≤ log₂|H|

## 7.1-7.3 Structural Risk Minimization (SRM) & MDL

**Nonuniform learnability**: H = ∪_n H_n (nested), w(n) = 2^{-n} (weight).

**SRM rule**: A(S) = argmin_{h∈H_n} [L_S(h) + complexity_penalty(n, m, δ)]

**MDL / Occam's Razor** (Corollary 7.2): For any prefix-free code w: H → {0,1}*:
```
L_D(A(S)) ≤ min_{h∈H} [ L_S(h) + |h|·ln2/(2m) ] + √(ln(1/δ)/(2m))
```
where |h| is the code length of h. Shorter descriptions → stronger guarantees.

## Hermes Applications

| PAC Concept | Hermes Application |
|-------------|-------------------|
| Sample complexity bound | m ≥ (1/ε²)·(d·ln(1/ε) + ln(1/δ)) examples needed before trusting recall quality |
| ERM | Choose route type that minimizes empirical routing error on recent decisions |
| Uniform convergence | Route quality generalizes from seen to unseen query types when m is sufficient |
| VC dimension | Number of distinct route-type distinguishing features limits generalization |
| SRM | Prefer simpler routing rules (fewer patterns) that still fit training data |
| MDL / Occam | Shorter routing rules get implicit regularization bonus |
