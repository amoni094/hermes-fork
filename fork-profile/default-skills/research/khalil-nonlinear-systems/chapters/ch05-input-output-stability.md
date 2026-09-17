# Chapter 5 — Input-Output Stability

**Pages:** 195–240  
**Lines in text:** 9219–10727

## Overview

Complements state-space stability with an input-output view. System treated as black-box operator H mapping signals. Introduces ℒ stability and the small-gain theorem — foundational for analyzing feedback interconnections.

---

## 5.1 ℒ Stability

**Signal spaces:**
- ℒ_p^m: functions u:[0,∞)→Rᵐ with finite p-norm
- ℒ_∞^m: bounded signals, ‖u‖_{ℒ∞} = sup_t ‖u(t)‖ < ∞
- ℒ_2^m: square-integrable, ‖u‖_{ℒ2} = (∫₀^∞ uᵀu dt)^{1/2} < ∞

**Extended space** ℒₑ: signals whose truncations uᵣ belong to ℒ for every T<∞. Allows unstable systems.

**Definition 5.1 (ℒ stable):** H:ℒₑ→ℒₑ is ℒ stable if:
```
‖(Hu)ᵣ‖_ℒ ≤ α(‖uᵣ‖_ℒ) + β
```
for class K function α and constant β≥0.

**Finite-gain ℒ stable:** H is finite-gain ℒ stable if:
```
‖(Hu)ᵣ‖_ℒ ≤ γ‖uᵣ‖_ℒ + β
```
The infimum of valid γ is the **ℒ gain** of H.

**ℒ∞ stability = BIBO stability:** bounded input u(t) ⟹ bounded output H(u)(t).

---

## 5.2 ℒ Stability of State Models

**Theorem 5.1:** System ẋ=f(x,u), y=h(x,u) with f(0,0)=0. If x=0 is exponentially stable and h,f satisfy growth conditions, then system is finite-gain ℒ stable.

**ℒ₂ gain:** For stable system with storage function V satisfying:
```
V̇ ≤ -α₃(‖x‖) + γ²/4 ‖u‖² - ‖y‖²
```
System has ℒ₂ gain ≤ γ (H_∞ framework).

---

## 5.3 ℒ₂ Gain for Time-Invariant Systems

For linear time-invariant system with transfer matrix G(s), ℒ₂ gain = ‖G‖_∞ = sup_ω σ_max[G(jω)].

For nonlinear systems, ℒ₂ gain computation uses Hamilton-Jacobi inequality:
```
(∂V/∂x)f(x,u) + ½γ⁻²‖y‖² - ½‖u‖² ≤ 0
```
When this holds, system has ℒ₂ gain ≤ γ.

---

## 5.4 Small-Gain Theorem

**Setup:** Feedback interconnection of H₁:ℒₑ→ℒₑ (gain γ₁) and H₂:ℒₑ→ℒₑ (gain γ₂):
```
e₁ = u₁ - H₂(e₂)
e₂ = u₂ + H₁(e₁)
```

**Theorem 5.6 (Small-Gain Theorem):** If both H₁ and H₂ are finite-gain ℒ stable with gains γ₁ and γ₂ respectively, and:
```
γ₁γ₂ < 1
```
then the feedback interconnection is finite-gain ℒ stable.

**Interpretation:** Loop gain < 1 ⟹ stable feedback. Nonlinear generalization of Nyquist stability.

### Application Pattern
```
H₁ = plant/system    (gain γ₁)
H₂ = controller/feedback  (gain γ₂)
Requirement: γ₁γ₂ < 1 for stability
```

**Example 5.13:** For two ISS systems in feedback, small-gain theorem gives ISS of interconnection when γ₁∘γ₂ does not dominate identity.

---

## 5.5 Connection to Lyapunov Stability

**Theorem 5.4:** If system ẋ=f(x,u), y=h(x,u) is ISS, it is finite-gain ℒ∞ stable.

More precisely:
- ISS (input-to-state stable) ⟹ finite-gain ℒ∞ stable
- For ℒ₂: need additional gain bounds on output map h

The Lyapunov-ISS condition gives a constructive way to verify ℒ stability.

---

## Key Formulas

**ℒ₂ gain bound via storage function:**
```
V̇(x) + ½‖y‖²_ℒ2 ≤ ½γ²‖u‖²_ℒ2 + V(x(0)) - V(x(T))
→ ‖y‖_ℒ2 ≤ γ‖u‖_ℒ2 + √(2V(x(0)))
```

**Small-gain condition for cascade:**
```
System 1: ‖y₁‖ ≤ γ₁‖u₁‖ + β₁
System 2: ‖y₂‖ ≤ γ₂‖u₂‖ + β₂
Interconnected (u₁=y₂, u₂=y₁): stable if γ₁γ₂ < 1
```

---

## Hermes Application: Skill Routing as ℒ∞ System

Model skill router as operator H:
- Input u = query embedding (bounded in practice)
- Output y = selected skill + parameters (bounded if router is stable)

**BIBO guarantee:** Show ‖y‖ ≤ γ‖u‖ + β for finite γ.

If router uses softmax over finite skill list: trivially bounded output → ℒ∞ stable.

If router is a learned/scoring function: Lipschitz analysis on scoring function gives γ = Lipschitz constant.

**Small-gain check for retry loop:**
- H₁ = skill executor (input: task, output: error signal)  
- H₂ = harness controller (input: error, output: action/retry)
- Stable if γ_executor × γ_controller < 1
