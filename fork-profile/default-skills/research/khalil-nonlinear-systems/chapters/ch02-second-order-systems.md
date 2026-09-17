# Chapter 2 — Second-Order Systems

**Pages:** 35–107  
**Lines in text:** 1890–4172

## Overview

Second-order autonomous systems ẋ = f(x), x∈R² allow phase-plane visualization of qualitative behavior. This chapter develops geometric tools for understanding nonlinear dynamics before tackling general theory.

## 2.1 Qualitative Behavior of Linear Systems

For ẋ = Ax, equilibrium type determined by eigenvalues of A:
- **Stable node** — both λ real, negative
- **Unstable node** — both λ real, positive
- **Saddle** — λ real, opposite signs
- **Stable focus** — complex λ, Re<0
- **Unstable focus** — complex λ, Re>0
- **Center** — purely imaginary λ (conservative systems)

## 2.2 Multiple Equilibria

Nonlinear systems can have multiple isolated equilibria. The region of attraction of each stable equilibrium is bounded by stable manifolds of saddle points.

**Example:** Tunnel-diode circuit has 3 equilibria: two stable, one unstable (saddle).

## 2.3 Qualitative Behavior Near Equilibria

**Hartman-Grobman theorem:** Near a hyperbolic equilibrium (no eigenvalues on imaginary axis), the nonlinear phase portrait is topologically equivalent to the linear one.

## 2.4 Limit Cycles

An isolated closed orbit in the phase plane. 

- **Stable limit cycle** — nearby trajectories spiral toward it
- **Unstable limit cycle** — nearby trajectories spiral away
- **Semi-stable** — stable on one side, unstable on other

**Van der Pol:** Has unique stable limit cycle for all µ>0.

## 2.5 Poincaré–Bendixson Criterion

**Theorem:** If a trajectory remains in a compact region containing no equilibria, it must approach a closed orbit.

**Implication:** In R², no chaos possible in autonomous systems. Chaos requires n≥3 or non-autonomous 2D systems.

## 2.6 Index Theory

The **index** of a closed curve with respect to f is the total rotation of f(x) as x traverses the curve. Used to count equilibria inside limit cycles.

**Key result:** Sum of indices of all equilibria enclosed by a limit cycle = +1.

## 2.7 Bendixson's Criterion

If ∂f₁/∂x₁ + ∂f₂/∂x₂ (divergence of f) has constant sign in a simply connected region D, then there are no closed orbits in D.

## Hermes Relevance
Two-state agent loops (e.g., (error_level, integrator)) can be analyzed via phase portraits. Bendixson's criterion can rule out oscillatory (cycling) behavior in discrete-time 2D maps by analogous argument.
