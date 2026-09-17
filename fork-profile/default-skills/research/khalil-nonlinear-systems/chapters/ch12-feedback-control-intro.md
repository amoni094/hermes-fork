# Chapter 12 — Feedback Control (Introduction)

**Pages:** 485–505  
**Lines in text:** 21723–23369 (labeled "Chapter 1 / Feedback Control" in OCR)

## Overview

Bridges analysis (Chs. 1–11) and design (Chs. 13–14). Covers classical feedback control ideas: linearization about operating points, integral control, gain scheduling, and how nonlinear analysis informs design.

---

## 12.1 Control Objectives

Standard objectives:
- **Stabilization:** Drive x→0 or x→x_d
- **Tracking:** x(t) follows reference r(t) with bounded error
- **Disturbance rejection:** Minimize effect of w on output y
- **Robustness:** Maintain objectives under plant uncertainty

**Nonlinear challenge:** Each objective may require different tools; no single procedure covers all.

---

## 12.2 Linearization and Gain Scheduling

**Linearize about equilibrium (x₀, u₀):**
```
δẋ ≈ A·δx + B·δu
A = ∂f/∂x|_{x₀,u₀},  B = ∂f/∂u|_{x₀,u₀}
```
Design linear controller for (A,B), apply nonlinearly near operating point.

**Limitation:** Valid only locally. Fails for large deviations.

**Gain scheduling:** Parameterize controllers as function of operating condition p(x):
```
u = α(x) = α_{p(x)}(x)  (lookup table of linear controllers)
```
**Stability caveat:** Stability of each frozen controller ≠ stability under varying p. Need analysis of switching dynamics or sufficiently slow scheduling.

---

## 12.3 Integral Control

**Output regulation:** Add integrator for tracking:
```
ζ̇ = e = y - r
u = -K₁x - K₂ζ
```
Eliminates steady-state error if closed-loop is stable.

**Nonlinear integral control (Theorem 12.3):** If nominal system is AS and output h is locally Lipschitz, adding integral action preserves local stability and achieves zero steady-state error for constant references.

---

## 12.4 Overview of Nonlinear Design Tools

| Tool | Key Idea | Ch. |
|------|----------|-----|
| Feedback linearization | Cancel nonlinearities exactly | 13 |
| Sliding mode | Force trajectory to manifold | 14.1 |
| Lyapunov redesign | Add robustifying term to nominal control | 14.2 |
| Backstepping | Recursive Lyapunov construction | 14.3 |
| Passivity-based | Exploit energy structure | 14.4 |
| High-gain observers | Recover state-feedback performance | 14.5 |

---

## Hermes Relevance

Linearization → gain scheduling mirrors Hermes model routing: different "gains" (models) at different operating points (task types). Stability of switching between models requires analysis beyond each model in isolation.
