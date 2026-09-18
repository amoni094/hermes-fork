# Chapter 7 — Feedback Systems (Absolute Stability)

**Pages:** 253–303 (renumbered in text as Ch. 7)  
**Lines in text:** ~12369–14237 (CHAPTER 7. FEEDBACK SYSTEMS sections)

## Overview

Applies passivity and Lyapunov methods to feedback systems with nonlinear components. Absolute stability asks: is the system stable for *all* nonlinearities in a given sector?

---

## 7.1 Absolute Stability

**Lur'e Problem:** Linear time-invariant plant G(s) in negative feedback with static nonlinearity ψ:R→R in sector [K₁,K₂].

**Definition:** System is **absolutely stable** if globally AS for every ψ∈[K₁,K₂].

**Sector condition:** ψ∈[K₁,K₂] means:
```
(ψ(y) - K₁y)(ψ(y) - K₂y) ≤ 0
```

**Circle Criterion:** Absolute stability when Nyquist plot of G(jω) lies entirely within (or to the right of) the circle passing through -1/K₁ and -1/K₂ on the real axis.

**Multivariable case:** For ψ∈[K₁,K₂] (matrix sector), use singular value bounds. System is absolutely stable if:
```
Z(s) = [I + K₂G(s)][I + K₁G(s)]⁻¹ is SPR
```
And condition ‖r₁r₂‖ < 1 (small-gain form) suffices when r₁r₂ < 1.

---

## 7.2 Popov Criterion

More powerful than circle criterion for time-invariant nonlinearities.

**Theorem 7.2 (Popov):** System with G(s) and ψ∈[0,K] is absolutely stable if ∃ q≥0:
```
Re[(1+jωq)G(jω)] + 1/K > 0, ∀ω∈R
```
Graphically: modified Nyquist plot (Popov plot) of jωG(jω) lies to the right of a line through -1/K with slope 1/q.

---

## 7.3 Zames-Falb Multipliers

Extension of Popov criterion using frequency-domain multipliers M(jω):
```
Re[M(jω)G(jω)] > 0
```
for multipliers in a specified class. More general than Popov; captures monotone/odd nonlinearities.

---

## Key Distinction from Passivity Chapter

- Ch. 6: Passivity for general nonlinear systems with storage functions
- Ch. 7: Absolute stability for Lur'e structure (linear + static nonlinearity), using frequency-domain conditions

Both are robust stability results valid for classes of nonlinearities.

---

## Hermes Relevance

Absolute stability framework applies when:
- A base system (linear dynamics, e.g., PID integrator) is in feedback with a nonlinear element (softmax, sigmoid, tanh-based gate)
- Need to verify stability for *all* parameter settings of the nonlinear element within bounds
- Example: loop-pid.py with tanh-shaped action selector: verify circle criterion for action = tanh(u) ∈ [-1,1]
