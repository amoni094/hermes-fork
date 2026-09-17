# Chapter 6 — Passivity

**Pages:** 241–278  
**Lines in text:** 10728–12368

## Overview

Passivity is a power-based stability concept: a passive system cannot generate more energy than it stores. Provides a natural framework for stability of feedback interconnections without requiring precise gain knowledge.

---

## 6.1 Memoryless Functions

**Passivity for memoryless h:Rⁿ→Rⁿ:**
- **Passive:** uᵀh(u) ≥ 0 for all u
- **Strictly passive:** uᵀh(u) ≥ δuᵀu for some δ>0
- **Sector [α,β]:** (h(u)-αu)ᵀ(h(u)-βu) ≤ 0

Sectors describe bounds: h is between two linear functions αI and βI.

---

## 6.2 State-Space Systems

**Definition 6.3 (Passive):** System ẋ=f(x,u), y=h(x,u) with f(0,0)=0, h(0,0)=0 is **passive** if ∃ continuously differentiable storage function V(x)≥0 with V(0)=0 such that:
```
V̇(x,u) ≤ uᵀy    for all (x,u)
```
i.e., power extracted ≤ supply rate.

**Strictly passive:** V̇ ≤ uᵀy - ε‖y‖² (output strict)  
**Input strict passive:** V̇ ≤ uᵀy - δ‖u‖²

**Lossless:** V̇ = uᵀy (no dissipation)

---

## 6.3 Positive Real Functions

**Positive real (PR):** Transfer matrix Z(s) is PR if:
1. Z(s) has no poles in Re(s)>0
2. Z(jω)+Z*(jω) ≥ 0 for all ω∈R

**Strictly PR (SPR):** Z(jω)+Z*(jω) > 0 (positive definite).

**Lemma 6.1 (Kalman-Yakubovich-Popov):** Z(s)=C(sI-A)⁻¹B+D is SPR iff A is Hurwitz and:
```
Z(jω) + Z*(jω) > 0, ∀ω, and lim_{ω→∞} ω²[Z(jω)+Z*(jω)] > 0
```

**Connection:** Passive system ⟺ positive real transfer function (for linear systems).

---

## 6.4 Passivity Theorems

**Theorem 6.1 (Passivity Theorem):** Negative feedback of passive H₁ and strictly output passive H₂:
```
y₁ = H₁(u₁),  y₂ = H₂(u₂)
u₁ = -y₂ + e₁,  u₂ = y₁ + e₂
```
is ℒ₂ stable.

**Proof sketch:** Total storage V=V₁+V₂. V̇ ≤ e₁ᵀy₁ + e₂ᵀy₂ - ε‖y₂‖² ≤ supply - dissipation.

**Corollary:** If one system is lossless and other is strictly passive → asymptotically stable.

---

## 6.5 Feedback Passivation

**Goal:** Design u=α(x)+β(x)v to make system passive with respect to new supply rate.

**Condition:** System is feedback passive if there exists α such that closed-loop storage function satisfies passivity inequality. This requires the system to have **relative degree 1** and **minimum phase** zero dynamics.

---

## 6.6 Absolute Stability (Lur'e Problem)

**Setup:** Linear plant G(s) in feedback with static nonlinearity ψ∈[α,β].

**Circle Criterion (Theorem 6.2):** System is absolutely stable (stable for all ψ∈[α,β]) if:
```
Z(s) = (1+βG(s))/(1+αG(s)) is SPR
```
Graphically: Nyquist plot of G lies to the right of circle defined by (-1/β, 0) and (-1/α, 0).

**Popov Criterion (Theorem 6.4):** Less conservative than circle criterion for time-invariant ψ.

---

## Hermes Relevance
Passivity rarely applies directly to discrete software systems, but the concept of **storage function** (bounded "energy" in a component) applies to:
- Working memory size as storage function: bounded writes → bounded state
- Skill ranker as passive map: bounded query → bounded score output
