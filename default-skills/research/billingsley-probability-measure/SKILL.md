---
name: billingsley-probability-measure
category: research
description: Use when applying weak convergence or measure theory.
triggers:
  - weak convergence
  - Portmanteau theorem
  - Radon-Nikodym
  - measure theory
  - uniform integrability
  - EMA convergence
  - logprob scoring
  - stability gate
  - demotion rate bounding
  - absolutely continuous measure
  - convergence in probability
  - almost sure convergence
---

# Billingsley — Probability and Measure (3rd ed.)

Patrick Billingsley, Wiley, 1995. The definitive graduate reference for rigorous probability and measure theory. Chapters 1–7 build probability on measure-theoretic foundations; Part III (Secs 25–30) covers weak convergence on metric spaces.

See references/ for per-section deep dives and the cheatsheet.

---


## Model Routing

Measure-theoretic derivation (weak convergence, martingales, CLT proofs): magistral-small-latest (mistral). Implementation: grok-4.6 workers via delegate_task.


## Core Frameworks

### Portmanteau Theorem (Sec 25, Thm 25.8)
Five equivalent conditions for weak convergence μ_n ⇒ μ on a metric space:
1. ∫f dμ_n → ∫f dμ for all bounded continuous f
2. lim sup μ_n(F) ≤ μ(F) for all closed F
3. lim inf μ_n(G) ≥ μ(G) for all open G
4. μ_n(A) → μ(A) for all μ-continuity sets A (μ(∂A) = 0)
5. F_n(x) → F(x) at every continuity point x of F (real-line case)

**Operational rule:** Condition 5 is the cheapest to check empirically — evaluate CDF at a finite grid avoiding mass points.

### Weak Convergence Stability Gate (Billingsley §25 + Hermes extension)
Maintain a ring of 5 Laplace success rates: p_1 … p_5 (circular buffer, newest overwrites oldest).

```
weakly_stable = max(p_1..p_5) - min(p_1..p_5) < 0.03
```

- Declare **weakly_stable** → skip re-routing for this task_type.
- **Never inherit** stability across task_types: a new task_type resets the ring (new task_type = discontinuity in the empirical CDF).
- Threshold 0.03 = one half of a typical Laplace noise scale; tighter than Kolmogorov–Smirnov 5% critical value at n=5.

### Radon-Nikodym Theorem (Sec 32, Thm 32.2)
If ν ≪ μ (ν absolutely continuous w.r.t. μ), then there exists a unique (μ-a.e.) density dν/dμ ∈ L¹(μ) such that ν(A) = ∫_A (dν/dμ) dμ for all measurable A.

**Failure mode:** If μ has atoms (point masses), ν may not be absolutely continuous → dν/dμ undefined at atoms.

### Convergence in Probability vs Almost Sure (Sec 25)
- **In probability (Lᵖ):** X_n →^p X iff P(|X_n − X| > ε) → 0 for all ε > 0.
- **Almost surely:** X_n →^{a.s.} X iff P(lim_{n→∞} X_n = X) = 1. Requires stationarity or mixing conditions not guaranteed in general.
- EMA (exponential moving average) is a geometric-weighted sum: converges in probability but NOT almost surely unless the score sequence is stationary.

### Uniform Integrability (Sec 25, Thm 25.12)
A family {X_n} is uniformly integrable (UI) iff:
- sup_n E[|X_n|] < ∞, AND
- ∀ε>0 ∃δ>0: P(A)<δ ⟹ sup_n E[|X_n| 1_A] < ε

**Vitali convergence:** X_n →^p X with {X_n} UI ⟺ X_n → X in L¹.

---

## Hermes Applications

| Theorem | Hermes Component | Implementation Note |
|---|---|---|
| Portmanteau (Thm 25.8) | RR demotion scorer | Bound false-positive demotion rate via Cond. 5: check empirical CDF at continuity points only |
| Stability Gate (§25) | jev-decision-patterns router | Ring p_1..p_5; weakly_stable = range < 0.03; reset on new task_type |
| Radon-Nikodym (Thm 32.2) | jev-compaction EMA update | Atom-detection guard: if score ≡ 0.5 for ≥3 consecutive turns, flag atom, skip EMA derivative |
| Conv. in prob. vs a.s. (§25) | EMA score tracker | Document that EMA has in-probability guarantee only; add stationarity check |
| Uniform Integrability (Thm 25.12) | logprob score ingestion | Clamp logprob scores to [−20, 0] before EMA; overflow violates UI and makes L¹ convergence fail |

### Stability Gate — Reference Implementation
```python
from collections import deque

class WeakStabilityGate:
    def __init__(self):
        self._rings = {}  # task_type -> deque(maxlen=5)

    def update(self, task_type: str, p: float) -> bool:
        """Returns True iff weakly_stable after update."""
        if task_type not in self._rings:
            self._rings[task_type] = deque(maxlen=5)
        ring = self._rings[task_type]
        ring.append(p)
        if len(ring) < 5:
            return False
        return max(ring) - min(ring) < 0.03
```

### Atom-Detection Guard (Radon-Nikodym)
```python
def ema_update(ema: float, score: float, alpha: float,
               history: list, atom_thresh: int = 3) -> float:
    history.append(score)
    recent = history[-atom_thresh:]
    if len(recent) == atom_thresh and len(set(recent)) == 1:
        # atom detected — Radon-Nikodym density undefined
        return ema  # skip update
    score = max(-20.0, min(0.0, score))  # UI clamp
    return alpha * score + (1 - alpha) * ema
```

---

## Chapter Index

| Chapter / Section | Title | Key Results |
|---|---|---|
| Ch 1 (Secs 1–7) | Probability | Kolmogorov axioms, σ-algebras, extension theorem |
| Ch 2 (Secs 10–17) | Measure | Lebesgue measure, outer measure, Carathéodory |
| Ch 3 (Secs 18–22) | Integration | MCT, DCT, Fubini, Lᵖ spaces |
| Ch 4 (Secs 23–24) | Random Variables | Distribution functions, independence |
| Ch 5 (Secs 25–30) | Convergence of Distributions | Portmanteau, tightness, CLT, Skorokhod |
| Sec 25 | Weak Convergence | Portmanteau Thm, Helly, conv. in prob., UI |
| Sec 26 | Characteristic Functions | Inversion, continuity theorem |
| Sec 27 | CLT | Lindeberg, Lyapunov |
| Sec 28 | Infinitely Divisible Distributions | Lévy-Khintchine |
| Sec 29 | Limit Theorems in Rᵏ | Multivariate CLT |
| Sec 30 | Brownian Motion | Donsker's theorem |
| Ch 6 (Secs 31–35) | Derivatives + Conditioning | Radon-Nikodym, conditional expectation |
| Sec 32 | Radon-Nikodym | Thm 32.2, Lebesgue decomposition |
| Sec 33 | Conditional Expectation | Definition via R-N, properties |
| Ch 7 (Secs 36–38) | Stochastic Processes | Martingales, optional stopping |

---

## Topic Index

- **Absolute continuity**: Sec 32 → Radon-Nikodym
- **Almost sure convergence**: Sec 22 (a.s. = pointwise a.e.), Sec 25
- **Atoms / point masses**: Sec 32 (failure of R-N), Sec 10 (Lebesgue decomposition)
- **Borel σ-algebra**: Sec 1, Sec 10
- **Characteristic functions**: Sec 26
- **Conditional expectation**: Sec 33
- **Convergence in Lᵖ**: Sec 21, Sec 25 (UI + in-prob → L¹)
- **DCT / MCT**: Sec 16
- **EMA / geometric weights**: apply Sec 25 (conv. in prob.)
- **Fubini**: Sec 18
- **Helly selection theorem**: Sec 25
- **Independence**: Sec 4
- **Kolmogorov extension**: Sec 7
- **Lebesgue decomposition**: Sec 32
- **Martingales**: Sec 35–36
- **Outer measure / Carathéodory**: Sec 11
- **Portmanteau theorem**: Sec 25 (Thm 25.8)
- **Radon-Nikodym**: Sec 32 (Thm 32.2)
- **Skorokhod representation**: Sec 29
- **Tightness / Prokhorov**: Sec 25, Sec 29
- **Uniform integrability**: Sec 25 (Thm 25.12)
- **Weak convergence**: Sec 25 (definition + Portmanteau)
