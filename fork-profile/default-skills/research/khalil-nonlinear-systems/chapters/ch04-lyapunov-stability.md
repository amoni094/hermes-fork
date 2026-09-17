# Chapter 4 — Lyapunov Stability

**Pages:** 111–194  
**Lines in text:** 5263–9218

## Overview

The central chapter of the book. Lyapunov's direct method provides stability certificates without solving differential equations. Covers autonomous and nonautonomous systems, LaSalle invariance, linearization, and ISS.

---

## 4.1 Autonomous Systems

System: ẋ = f(x), f(0) = 0, x∈Rⁿ

**Definition 4.1:** Equilibrium x=0 is:
- **Stable:** ∀ε>0, ∃δ>0: ‖x(0)‖<δ ⟹ ‖x(t)‖<ε ∀t≥0
- **Asymptotically stable (AS):** Stable + x(t)→0 as t→∞
- **Unstable:** Not stable

**Theorem 4.1 (Lyapunov Stability Theorem):**  
Let V:D→R be C¹ with V(0)=0 and V(x)>0 on D\{0}.
- If V̇(x) = (∂V/∂x)f(x) ≤ 0 on D → x=0 is **stable**
- If V̇(x) < 0 on D\{0} → x=0 is **asymptotically stable**

**Theorem 4.2 (Global AS):**  
Same conditions + V(x)→∞ as ‖x‖→∞ → **globally asymptotically stable (GAS)**

**V(x) is called a Lyapunov function** when conditions are met.

### Common Lyapunov Function Choices

| System type | Candidate V |
|-------------|-------------|
| Linear ẋ=Ax | V=xᵀPx (P=Lyapunov eq. solution) |
| Energy-based | V=kinetic+potential energy |
| Quadratic | V=‖x‖² |
| Polynomial | V=sum of even monomials |
| Composite | V=max(Vᵢ) or sum of subsystem Lyapunov functions |

### Instability Theorem (Chetaev)
If ∃ region where V>0 and V̇>0, then x=0 is unstable.

---

## 4.2 LaSalle's Invariance Principle

**Theorem 4.4:** Let Ω be compact, positively invariant for ẋ=f(x). Let V be C¹ with V̇≤0 on Ω. Let E={x∈Ω | V̇(x)=0}. Let M be the largest invariant set in E. Then every solution in Ω converges to M as t→∞.

**Usage:** Prove AS when V̇≤0 (not strict):
1. Find V̇=0 set E
2. Show only trajectory staying in E is x=0 → M={0}
3. Conclude x→0

**Example (pendulum with friction):** V=E(x)=kinetic+potential. V̇=-bx₂²≤0. E={x₂=0}. On E: ẋ₂=-asin(x₁)=0 → x₁=0. Hence M={0}.

---

## 4.3 Linear Systems and Linearization

**Linear case:** ẋ=Ax. V=xᵀPx satisfies:
```
AᵀP + PA = -Q  (Lyapunov equation)
```
x=0 is AS ⟺ A is Hurwitz ⟺ ∃P>0 solving Lyapunov eq. for any Q>0.

**Theorem 4.7 (Linearization):** Let A=∂f/∂x|_{x=0}.
- If A is Hurwitz → x=0 is AS (locally)
- If A has eigenvalue with Re>0 → x=0 is unstable

**Limitation:** If A has eigenvalues on imaginary axis, linearization is inconclusive → use center manifold (Ch. 8).

---

## 4.4 Class K and KL Functions

- **Class K:** α:[0,∞)→[0,∞), continuous, α(0)=0, strictly increasing
- **Class K∞:** Class K + α(r)→∞ as r→∞
- **Class KL:** β(r,s), class K in r for each s, decreasing to 0 as s→∞

**Why needed:** Characterize stability bounds in a coordinate-free, nonlinear-compatible way.

```
AS ⟺ ‖x(t)‖ ≤ β(‖x(0)‖, t) for some β∈KL
```

---

## 4.5 Nonautonomous Systems

System: ẋ = f(t,x), f(t,0)=0

**Definition 4.6:** Equilibrium x=0 is:
- **Uniformly stable:** δ independent of t₀
- **Uniformly asymptotically stable (UAS):** Uniformly stable + uniform convergence

**Theorem 4.9:** If ∃ V(t,x) with:
```
α₁(‖x‖) ≤ V(t,x) ≤ α₂(‖x‖)
V̇(t,x) ≤ -α₃(‖x‖)    (all αᵢ ∈ K)
```
→ x=0 is **UAS**

**Exponential stability:** If αᵢ(r)=cᵢrᵐ:
```
‖x(t)‖ ≤ k‖x(0)‖exp(-γ(t-t₀))
```

---

## 4.6 Linear Time-Varying Systems

ẋ = A(t)x. Stability determined by Φ(t,t₀) (state transition matrix), not eigenvalues of A(t). Linearization: if A(t)=∂f/∂x|_{x=0} is uniformly bounded and exponentially stable, nonlinear system is locally exponentially stable.

---

## 4.7 Converse Theorems

**Converse Lyapunov Theorem (Theorem 4.14):** If x=0 is exponentially stable, ∃ Lyapunov function V with:
```
c₁‖x‖² ≤ V(x) ≤ c₂‖x‖²
V̇(x) ≤ -c₃‖x‖²
‖∂V/∂x‖ ≤ c₄‖x‖
```

**Importance:** Guarantees existence of Lyapunov function — the hard part is *finding* it.

---

## 4.8 Boundedness and Ultimate Boundedness

**Uniform ultimate boundedness (UUB):** Solutions eventually enter a compact set Ω and stay there. Useful when V̇ < 0 outside some ball.

**Theorem 4.18 (UUB):** If V̇ ≤ -W(x) for ‖x‖≥µ and W continuous positive definite, then x is UUB.

---

## 4.9 Input-to-State Stability (ISS)

System: ẋ = f(x,u)

**Definition 4.7 (ISS):** System is ISS if ∃ β∈KL, γ∈K:
```
‖x(t)‖ ≤ β(‖x(0)‖, t) + γ(sup_{s∈[0,t]} ‖u(s)‖)
```

**Lyapunov-ISS (Theorem 4.19):** System is ISS if ∃ V with:
```
α₁(‖x‖) ≤ V ≤ α₂(‖x‖)
V̇ ≤ -α₃(‖x‖)  when  ‖x‖ ≥ σ(‖u‖)
```
for σ∈K.

**ISS gain function γ:** measures how input u affects steady-state.

**ISS Cascade:** If subsystem 1 is ISS and subsystem 2 is ISS with bounded state, the cascade is ISS.

**Key property:** ISS ⟹ BIBO (bounded input bounded output in state sense). ISS ⟹ 0-GAS (GAS when u=0).

---

## Exercises / Key Results for Hermes

1. **Loop-PID:** Model error e(t) as state; V=e² → V̇=2eė. For PID update: ė=-Kp·e - Ki·∫e - Kd·ė. Show V̇<0 → convergence certificate.

2. **ISS for skill chains:** Each skill Sᵢ processes input xᵢ, outputs xᵢ₊₁. If each is ISS with gain γᵢ, chain is ISS with gain γ₁∘γ₂∘...∘γₙ (when γ-composition is class K).

3. **UUB for metacognitive harness:** Model confidence state c∈[0,1]. Show c eventually enters [θ,1] (θ=threshold) under harness control.
