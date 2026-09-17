# Chapter 9 — Stability of Perturbed Systems

**Pages:** 355–400  
**Lines in text:** 15874–19766

## Overview

Studies robustness: if a system is stable, how does it behave under perturbations g(t,x)? Connects Lyapunov stability to ISS and total stability. Critical for real-world systems with modeling uncertainty.

---

## 9.1 Vanishing Perturbations

System: ẋ = f(t,x) + g(t,x) where g(t,0)=0 (perturbation vanishes at equilibrium).

**Theorem 9.1:** If ẋ=f(t,x) is exponentially stable (with Lyapunov V satisfying c₁‖x‖²≤V≤c₂‖x‖², V̇≤-c₃‖x‖²) and ‖g(t,x)‖≤γ‖x‖ with γ < c₃/(2c₄), then the perturbed system is exponentially stable.

**Interpretation:** Small Lipschitz perturbations preserve exponential stability. Exponential stability is *robust*.

---

## 9.2 Nonvanishing Perturbations

System: ẋ = f(t,x) + g(t,x) where g may not vanish at origin.

**Ultimate Boundedness:** Solutions ultimately bounded in set depending on ‖g‖.

**Theorem 9.2:** If unperturbed system is AS with Lyapunov V and ‖g(t,x)‖≤δ for all t,x, then:
```
‖x(t)‖ ≤ β(‖x(0)‖, t) + σ(δ)
```
for some β∈KL, σ∈K. Steady-state error bounded by function of perturbation size.

---

## 9.3 Input-to-State Stability (ISS) Revisited

ISS (introduced in 4.9) is the *right* framework for perturbed systems:

**Theorem 9.3:** If ẋ=f(x,u) is ISS, then for any bounded input u(t), state x(t) is ultimately bounded.

**ISS + cascade stability:** If subsystem ẋ₁=f₁(x₁,x₂) is ISS (with x₂ as input) and subsystem ẋ₂=f₂(x₂) is GAS, then cascade is GAS — provided ISS gain doesn't cause finite escape.

---

## 9.4 Slowly Varying Systems

System: ẋ = f(t,x) where f varies slowly: ‖∂f/∂t‖ ≤ ε.

If frozen-time system ẋ=f(t₀,x) is exponentially stable uniformly in t₀, and ε is small enough, then slowly varying system is exponentially stable.

---

## 9.5 Discrete-Time Stability

For discrete-time systems x(k+1) = F(k, x(k)):
- **Lyapunov condition:** ΔV = V(k+1, F) - V(k,x) ≤ -α₃(‖x‖) → AS
- **Discrete ISS:** ‖x(k)‖ ≤ β(‖x(0)‖, k) + γ(sup_j ‖u(j)‖)

**Direct analog of continuous theory** — all theorems carry over with ΔV replacing V̇.

---

## Key Result: Total Stability

**Definition:** Equilibrium x=0 is **totally stable** if for any ε>0, ∃δ>0 such that for all ‖g‖<δ and ‖x(0)‖<δ, ‖x(t)‖<ε for all t≥0.

**Theorem 9.5:** Uniform asymptotic stability ⟹ total stability.

---

## Hermes Application

**Metacognitive harness as perturbed system:**
- Nominal: harness with fixed FOK/JOL dynamics → AS
- Perturbation: noisy confidence estimates, model variation
- Theorem 9.2: bounded noise → bounded state error
- Quantify: if ‖noise‖ ≤ δ, steady-state confidence error ≤ σ(δ)

**Discrete-time ISS for skill chain:**
```
x(k+1) = F(x(k), u(k))  where u(k) = tool output noise
Discrete ISS: |x(k)| ≤ β(|x(0)|, k) + γ·sup_j|u(j)|
```
