# Chapter 13 — Feedback Linearization

**Pages:** 505–550  
**Lines in text:** 23370–25482

## Overview

When a nonlinear system has special structure, exact nonlinearity cancellation via feedback yields a linear closed-loop. This chapter develops conditions and tools for full-state and input-output linearization.

---

## 13.1 Motivation

**Direct cancellation:** System ẋ = Ax + B·γ(x)[u - α(x)] can be linearized by:
```
u = α(x) + γ⁻¹(x)·v  →  ẋ = Ax + Bv  (linear)
```

**Coordinate change:** Even if direct cancellation impossible, a diffeomorphism z=T(x) may put system in linearizable form. Finding T requires Lie algebraic conditions.

---

## 13.2 Input-Output Linearization

**Setup:** SISO system ẋ=f(x)+g(x)u, y=h(x).

**Relative degree r:** Smallest integer such that:
```
Lg Lf^(r-1) h(x) ≠ 0
```
where Lie derivatives: Lf h = (∂h/∂x)f(x), Lf^k h = Lf(Lf^{k-1} h).

**Input-output linearization:**
```
y^(r) = Lf^r h(x) + Lg Lf^(r-1) h(x) · u
```
Choose: u = [v - Lf^r h(x)] / [Lg Lf^(r-1) h(x)]

This gives the linear input-output relation: y^(r) = v.

**Normal form:** With r<n, introduce new coordinates:
```
ξᵢ = Lf^(i-1) h(x),  i=1,...,r  (input-output states)
η ∈ R^(n-r)            (internal states: zero dynamics)
```
Full system:
```
ξ̇ = Aξ + Bv   (linear, Brunovsky form)
η̇ = q(ξ, η)   (zero dynamics, unobservable)
```

---

## 13.3 Zero Dynamics

**Definition:** Zero dynamics = dynamics of η when output y≡0 (equivalently, ξ≡0).

**Minimum phase:** Zero dynamics are AS at origin.

**Importance:** I-O linearization produces a well-behaved closed loop only if zero dynamics are stable. Non-minimum-phase system can have unstable internal dynamics even with y→0.

**Computation:**
```
Solve h(x)=0, Lf h(x)=0, ..., Lf^(r-1) h(x)=0 for manifold Z*
Zero dynamics: ẋ restricted to Z*
```

---

## 13.4 Full-State Linearization

**Conditions for exact linearization (Frobenius/Lie):**

System ẋ=f(x)+g(x)u is feedback linearizable iff:
1. The matrix [g, adf g, ..., adf^{n-1} g] has rank n in D
2. Distribution span{g, adf g, ..., adf^{n-2} g} is involutive in D

where adf g = [f,g] = (∂g/∂x)f - (∂f/∂x)g (Lie bracket).

When conditions hold, ∃ diffeomorphism z=T(x) such that:
```
ż = Az + Bv  (Brunovsky canonical form)
u = α(x) + β(x)v
```

---

## 13.5 State Feedback Design

After linearization (full or partial), design linear controller for (A,B) pair:
- **Stabilization:** v = -Kξ, A_c = A-BK Hurwitz
- **Tracking:** v = r^(r) - k₁ê - ... - kᵣe, where e = y - r

**Closed-loop:** Error dynamics eᵢ = y^(i) - r^(i) satisfy linear ODE with designed poles.

---

## Key Formulas

**Lie derivatives:**
```
L_f h(x) = ∑ᵢ (∂h/∂xᵢ) fᵢ(x)
L_f^k h = L_f(L_f^{k-1} h)
L_g L_f^{r-1} h(x) = (∂/∂x)[L_f^{r-1} h] · g(x)
```

**Brunovsky form (relative degree r=n):**
```
ẑ₁ = z₂
ẑ₂ = z₃
  ⋮
żₙ = v
```

**Relative degree for MIMO:** Relative degree vector [r₁,...,rₚ]; total relative degree r = Σrᵢ.

---

## Hermes Relevance

Feedback linearization concept applies to nonlinear score normalization: if a skill scorer f(x) has known nonlinear structure, an exact inverse transformation z = f⁻¹ linearizes the scoring for linear ranking downstream. Viable when f is invertible and not minimum-phase issues don't arise.
