# Ch 5 — Lyapunov Stability Theory (Slotine & Li)

## Stability Definitions

Let ẋ = f(x), x ∈ ℝⁿ, f(0) = 0 (equilibrium at origin).

- **Stable (Lyapunov sense):** ∀ε>0 ∃δ>0 s.t. ‖x(0)‖<δ ⟹ ‖x(t)‖<ε ∀t≥0
- **Asymptotically stable:** stable AND x(t) → 0 as t → ∞
- **Exponentially stable:** ‖x(t)‖ ≤ k·‖x(0)‖·e^{-λt} for constants k,λ>0
- **Globally asymptotically stable (GAS):** asymptotically stable for all x(0)

## Lyapunov's Direct Method

### Definition: Lyapunov Function
V: ℝⁿ → ℝ is a **Lyapunov function candidate** if:
1. V(0) = 0
2. V(x) > 0 for x ≠ 0  (positive definite)
3. V(x) → ∞ as ‖x‖ → ∞  (radially unbounded, needed for global results)

### Theorem 4.1 (Lyapunov Stability)
If V(x) is positive definite and:
- dV/dt ≤ 0 along trajectories → equilibrium is **stable**
- dV/dt < 0 along trajectories → equilibrium is **asymptotically stable**
- dV/dt < 0 and V radially unbounded → **globally asymptotically stable**

### Computing dV/dt
$$\dot{V}(x) = \nabla V(x) \cdot f(x) = \sum_{i=1}^n \frac{\partial V}{\partial x_i} f_i(x)$$

## Standard Lyapunov Candidates

### Quadratic (Scalar Error)
For scalar error e:
```
V(e) = e²           (simplest valid choice, positive definite)
dV/dt = 2e·ė        (need 2e·ė ≤ 0)
```
This is **asymptotically stable** iff e and ė have opposite signs consistently.

### Quadratic (Vector)
```
V(x) = xᵀPx         where P = Pᵀ ≻ 0  (symmetric positive definite)
dV/dt = xᵀ(AᵀP + PA)x  for linear system ẋ = Ax
```
**Lyapunov equation:** AᵀP + PA = -Q determines P given Q ≻ 0.

### PID Loop (Hermes loop-pid.py)
The composite candidate used in loop-pid.py:
```
V(k) = e(k)² + (Ki/Kp)·integrator(k)²         [normal steps]
V_aw(k) = e(k)² + (Ki/Kp)·integrator(k)² + KAW·(u_raw - u)²  [saturated]
```
ΔV = V(k+1) - V(k) < 0 is the **discrete-time analog** of dV/dt < 0.

**SLOTINE-CH5 annotation:** The current loop-pid.py checks discrete ΔV < 0 step-by-step,
which is the valid discrete Lyapunov decrease condition. The continuous analog would be
dV/dt = 2e·ė ≤ 0. Both are correct formulations in their respective domains.

## How to Apply Lyapunov's Method (Procedure)

1. **Choose V(x):** Start with V = xᵀPx or V = Σ eᵢ². Physical energy works well.
2. **Compute dV/dt:** Differentiate along f(x).
3. **Check sign:** Is dV/dt ≤ 0? Try to show it is negative (semi-)definite.
4. **If dV/dt = 0 on a set:** Apply LaSalle's invariance principle.
5. **Conclude:** Match conditions to stability theorem.

## LaSalle's Invariance Principle

When dV/dt ≤ 0 (only semi-definite), LaSalle extends the conclusion:

**Theorem (LaSalle):** Let Ω = {x : V(x) ≤ c} be compact and positively invariant.
If dV/dt ≤ 0 in Ω, then x(t) → M as t→∞, where M is the **largest invariant set** within
{x ∈ Ω : dV/dt = 0}.

**Application:** Even if dV/dt = 0 on a set E, check whether ẋ = 0 forces x = 0 within E.
If yes, then x → 0 (asymptotic stability) despite dV/dt only being semi-definite.

## Barbalat's Lemma (Key Tool for Adaptive Control)

If g(t) is uniformly continuous and ∫₀^∞ g(t)dt exists and is finite, then g(t) → 0.

**Use:** If V̇ = −e²g(t) and V is bounded below, integrate: ∫e²g dt < ∞. If e is
uniformly continuous, then e → 0. (Critical for proving MRAS convergence in Ch 7.)

## Practical / Ultimate Boundedness

For systems with bounded disturbances d(t), ‖d‖ ≤ δ:

**Theorem (Practical Stability / UB):** If V̇ ≤ -α‖x‖² + γδ² for constants α,γ>0,
then solutions are ultimately bounded: ‖x(t)‖ ≤ β for some finite β depending on δ.

**Interpretation for loop-pid.py:** Non-zero exogenous error sources (model mismatch,
stochastic task complexity) mean lyapunov_stable=True is a strong condition; practical
stability (ΔV bounded below by small ε) may be the realistic goal.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| V not positive definite | Verify V(0)=0 and V(x)>0 for x≠0 |
| dV/dt ≤ 0 but not checking LaSalle | Apply LaSalle; find largest invariant set |
| V defined locally, claiming global stability | Need V radially unbounded |
| Discrete ΔV>0 at some steps, claiming stable | Each violation is a true instability signal |
| Confusion of stability vs convergence | Stability ≠ x→0; asymptotic stability does |
