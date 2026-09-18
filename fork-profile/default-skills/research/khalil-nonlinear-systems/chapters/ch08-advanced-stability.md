# Chapter 8 — Advanced Stability Analysis

**Pages:** 303–352  
**Lines in text:** 14238–15873

## Overview

Extends Chapter 4 with center manifold theory, region of attraction estimation, LaSalle-like theorems for nonautonomous systems, and stability of periodic orbits.

---

## 8.1 Center Manifold Theorem

**When linearization fails:** A has eigenvalues with zero real part.

System: ẋ = Ax + f̃(x) where A's eigenvalues split into:
- **Center:** Re(λ)=0 (s_c eigenvalues)
- **Stable:** Re(λ)<0 (s_s eigenvalues)

**Center Manifold:** An invariant manifold tangent to the center eigenspace at origin.

**Theorem 8.1:** ∃ center manifold x_s = h(x_c) where h(0)=0, ∂h/∂x_c(0)=0.

**Reduced system on center manifold:**
```
ẋ_c = A_c x_c + f_c(x_c, h(x_c))  (n_c-dimensional)
```
Stability of origin of full system ⟺ stability of origin of reduced system.

**Computation:** h(x_c) found by solving PDE:
```
∂h/∂x_c [A_c x_c + f_c(x_c, h(x_c))] - A_s h(x_c) - f_s(x_c, h(x_c)) = 0
```
Solved approximately via Taylor expansion.

---

## 8.2 Region of Attraction Estimation

**Region of attraction (ROA):** Rₐ = {x | x(t)→0 as t→∞} for AS equilibrium.

**Sublevel set estimate:** For Lyapunov function V with V̇<0 on D\{0}:
```
Ωc = {x | V(x) ≤ c} ⊂ D  →  Ωc ⊂ Rₐ
```
The largest c for which Ωc ⊂ D is an inner estimate of Rₐ.

**Algorithm to estimate ROA:**
```
1. Choose V (e.g., quadratic V = xᵀPx from linearization)
2. Find c* = min_{x∈∂D} V(x)
3. Estimate: Rₐ ⊇ {x | V(x) ≤ c*}
4. Refine: use polynomial V via SOS (sum-of-squares) optimization
```

**Zubov's method:** Exact ROA via solving PDE for V such that V=1 on boundary of ROA. Rarely tractable.

---

## 8.3 Invariance Theorems for Nonautonomous Systems

Two extensions of LaSalle for nonautonomous ẋ=f(t,x):

**Theorem 8.4 (Convergence to set):** If V(t,x)≤0 and V̇≤-W(x), then x converges to set {W(x)=0} as t→∞, provided V is bounded below.

**Theorem 8.5 (UAS):** If additionally {W=0}∩Ω = {0}, then x=0 is UAS.

**Key difference from LaSalle:** Nonautonomous systems don't have invariant sets in the same sense; convergence to a set holds but membership in M is not guaranteed.

---

## 8.4 Stability of Periodic Orbits

**Orbital stability:** Orbit γ is orbitally stable if nearby trajectories stay near γ.

**Poincaré map:** Reduce to discrete-time map on hyperplane transversal to orbit. Fixed point of Poincaré map corresponds to periodic orbit. Stability of fixed point ⟺ orbital stability.

**Floquet theory:** For periodic linear systems ẋ=A(t)x, T-periodic, characteristic multipliers determine stability.

---

## Hermes Application: ROA for Context Compaction

`rr_compaction_spike.py` scores messages for demotion. Model the scorer state (lambda parameter, budget) as x∈R².

**ROA estimation:**
```python
# V = quadratic Lyapunov fn from linearized scorer dynamics
# c* = max c such that {V≤c} ⊂ valid operating region
# → provides safe operating set for lambda parameter
```

**Center manifold:** If lambda-tuner has marginally stable mode (eigenvalue near 0), center manifold theorem gives reduced 1D analysis.
