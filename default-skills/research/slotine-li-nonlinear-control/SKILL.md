---
name: slotine-li-nonlinear-control
description: Use when applying Slotine-Li nonlinear control theory.
tags: [nonlinear-control, lyapunov, sliding-mode, adaptive-control, stability]
---

# Slotine & Li — Applied Nonlinear Control (1991)

Prentice-Hall. The canonical graduate textbook on nonlinear control systems.
Chapters 4–7 cover the core theory used in Hermes agent loop stability analysis.


## Model Routing

Controller derivation, stability/passivity analysis: magistral-small-latest (mistral). Numerical simulation: grok-4.6 workers via delegate_task.


## Quick Decision Router

| Goal | Method | Chapter |
|------|--------|---------|
| Prove closed-loop stability | Lyapunov direct method | Ch 5 |
| Robustness to bounded disturbances | Sliding mode control | Ch 6 |
| Handle unknown plant parameters | MRAS / adaptive control | Ch 7 |
| Geometric state-space reasoning | Differential geometry | Ch 3 |
| Phase plane / limit cycles | Phase plane analysis | Ch 2 |

## Core Frameworks

### 1. Lyapunov Stability (Ch 4–5)
**Theorem (Lyapunov Direct Method):** If there exists V(x) such that:
- V(x) > 0 for all x ≠ 0, V(0) = 0  (positive definite)
- dV/dt ≤ 0 along trajectories of ẋ = f(x)  (negative semi-definite)
then the equilibrium x = 0 is **stable**. If dV/dt < 0 (strictly), it is **asymptotically stable**.

Simplest candidate for scalar error e: **V(e) = e²**, giving dV/dt = 2e·ė ≤ 0.

See: `chapters/ch05-lyapunov.md`

### 2. Sliding Mode Control (Ch 6)
**Sliding surface:** s(x) = 0 (hyperplane in state space).  
**Reaching condition:** s·ṡ < 0 (trajectories driven toward s = 0).  
Once on surface, dynamics reduce to lower-order stable system.  
Key problem: **chattering** — high-frequency switching; solution: boundary layer φ.

See: `chapters/ch06-sliding-mode.md`

### 3. Adaptive Control / MRAS (Ch 7)
**Model Reference Adaptive System (MRAS):** Reference model gives desired response;
adaptation law adjusts parameters θ̂ so error e → 0.  
Stability proven via composite Lyapunov function V(e, θ̃) = eᵀPe + θ̃ᵀΓ⁻¹θ̃.  
Fixed parameters = open-loop; adaptive parameters = closed-loop over parameter space.

See: `chapters/ch07-adaptive-control.md`

## Chapter Index

| Ch | Title | Key Results |
|----|-------|-------------|
| 2 | Phase Plane Analysis | limit cycles, Bendixson criterion |
| 3 | Fundamentals of Lyapunov Theory | stability definitions, basic theorems |
| 4 | Advanced Stability Theory | LaSalle, instability, input-output |
| 5 | Describing Functions | harmonic balance, predicting limit cycles |
| 6 | Sliding Mode Control | reaching law, chattering, boundary layer |
| 7 | Adaptive Control | MRAS, SPR lemma, parameter convergence |
| 8 | Control of Multi-Input Systems | decoupling, feedback linearization |
| 9 | Robot Control | computed torque, adaptive robot control |

*(Note: PDF numbering may differ — Ch 4–5 Lyapunov, Ch 6 Sliding, Ch 7 Adaptive is the standard ordering.)*

## Topic Index

- **Asymptotic stability** → Ch 3, Theorem 4.1
- **Barbalat's Lemma** → Ch 4 (key for proving ė → 0)
- **Boundary layer** → Ch 6, §6.4
- **Chattering** → Ch 6, §6.3
- **LaSalle invariance principle** → Ch 4, §4.2
- **Lyapunov candidate construction** → Ch 3, §3.3
- **MRAS stability proof** → Ch 7, §7.4
- **Parameter estimation** → Ch 7, §7.2
- **Reaching condition** → Ch 6, §6.2
- **Sliding surface design** → Ch 6, §6.1
- **SPR (Strictly Positive Real) lemma** → Ch 7
- **Ultimate boundedness** → Ch 4, §4.5

## Linked Files
- `chapters/ch05-lyapunov.md` — Full Lyapunov theory with worked procedure
- `chapters/ch06-sliding-mode.md` — Sliding mode design and chattering mitigation
- `chapters/ch07-adaptive-control.md` — MRAS and adaptive laws
- `cheatsheet.md` — Decision rules and stability checklist
- `glossary.md` — Symbol and term definitions
