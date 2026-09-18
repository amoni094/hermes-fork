# Chapter 14 — Nonlinear Design Tools

**Pages:** 551–667  
**Lines in text:** 25483–~33000

## Overview

Five systematic design tools for nonlinear feedback control: sliding mode, Lyapunov redesign, backstepping, passivity-based control, and high-gain observers.

---

## 14.1 Sliding Mode Control

### Motivating Example
System: ẋ₁=x₂, ẋ₂=h(x)+g(x)u, g(x)≥g₀>0.

**Design:**
1. Choose sliding manifold s(x) = a₁x₁ + x₂ = 0 (on this manifold: ẋ₁=-a₁x₁, AS)
2. Design u = -β(x)sgn(s), with β(x) ≥ Q(x) + β₀ (where Q bounds h/g)
3. Lyapunov candidate V = ½s²:
   ```
   V̇ = sṡ ≤ g(x)|s|Q(x) - g(x)β(x)|s| ≤ -g₀β₀|s|
   ```
4. Finite reaching time: t_r ≤ |s(0)|/(g₀β₀)

**Chattering problem:** sgn(s) causes high-frequency switching. Mitigate with:
- Boundary layer: replace sgn(s) with sat(s/Φ) for small Φ
- Higher-order sliding modes

### General Formulation
For ẋ = f(x,t) + B(x,t)u + g(t,x) (matched uncertainty):
1. Design nominal control u₀ for s→0
2. Add discontinuous term: u = u₀ - β(x)sgn(s)·(BᵀB)⁻¹Bᵀ

**Robustness:** Motion on manifold independent of matched uncertainty g.

**Region of attraction:** Set {|s|≤c}∩{|x₁|≤c₁} is positively invariant.

---

## 14.2 Lyapunov Redesign

**Setup:** Nominal system ẋ=f(x)+Bu with known Lyapunov function V satisfying:
```
V̇_nominal = (∂V/∂x)(f+Bu₀) ≤ -α₃(‖x‖)
```
Perturbed: ẋ = f(x)+B[u+Δ(x,t)] where ‖Δ‖≤ρ(x).

**Redesign:** u = u₀ + v, where:
```
v = -(∂V/∂x·B)ᵀ · ρ(x) / ‖(∂V/∂x·B)ᵀ‖   when ‖(∂V/∂x·B)ᵀ‖ ≥ ε
```
This cancels uncertainty up to ε.

**Nonlinear damping:** Alternative — add -δ(x)‖(∂V/∂x·B)‖²·(∂V/∂x·B)ᵀ term. Guarantees UUB even without upper bound on ‖Δ‖.

---

## 14.3 Backstepping

**Key idea:** Recursive Lyapunov-based design that propagates stability through a chain of subsystems.

### Scalar Example
System: ẋ₁ = x₂ + φ₁(x₁), ẋ₂ = u + φ₂(x)

**Step 1:** Treat x₂ as virtual control. Choose α₁(x₁) = -c₁x₁ - φ₁(x₁) → V₁=½x₁² gives V̇₁=-c₁x₁²<0.

**Step 2:** Define e₂ = x₂ - α₁(x₁). Augment: V₂ = V₁ + ½e₂².
```
V̇₂ = -c₁x₁² + x₁e₂ + e₂[u + φ₂ - α̇₁]
```
Choose u = -c₂e₂ - x₁ - φ₂ + α̇₁ → V̇₂ = -c₁x₁² - c₂e₂² < 0.

**Result:** GAS of origin, explicit Lyapunov function V₂.

### General n-Step Backstepping

At each step k:
1. Introduce error eₖ = xₖ - αₖ₋₁
2. Augment: Vₖ = Vₖ₋₁ + ½eₖ²
3. Design αₖ to make V̇ₖ ≤ -cₖ‖(x₁,...,xₖ)‖² (cancel terms, add damping)
4. At final step k=n, set u=αₙ

**ISS backstepping:** Can build ISS certificates at each step → cascade ISS.

**Adaptive backstepping:** Parameters θ unknown — augment with parameter estimates and update laws.

---

## 14.4 Passivity-Based Control

**Idea:** Reshape the system's energy to achieve control objectives.

**Energy-shaping:** Find control u=α(x)+v such that closed-loop storage H_d(x) has desired minimum at x_d:
```
H_d(x) = H(x) + H_a(x)
```
where H_a is added energy.

**Damping injection:** Add v=-Kd·y to increase dissipation.

**Example (EL systems):** For Euler-Lagrange system M(q)q̈+C(q,q̇)q̇+∇V(q)=u:
```
u = ∇V(q) - ∇V_d(q) - K_d·q̇
```
Closed-loop has H_d=½q̇ᵀMq̇+V_d(q) as Lyapunov function.

---

## 14.5 High-Gain Observers

**Problem:** State feedback tools require full state. High-gain observers recover performance with output only.

**System (output feedback form):**
```
ẋᵢ = xᵢ₊₁ + φᵢ(y,u),  i=1,...,r-1
ẋᵣ = φᵣ(x,u) + gu
y = x₁
```

**Observer:**
```
x̂̇ᵢ = x̂ᵢ₊₁ + φᵢ(y,u) + αᵢ/εⁱ·(y-x̂₁)
```
with αᵢ chosen so observer polynomial Hurwitz.

**Theorem 14.5:** As ε→0, observer error → 0 exponentially. Closed-loop performance under output feedback approaches state-feedback performance.

**Peaking phenomenon:** Transient peaks in estimates when ε small. Saturate control to handle.

---

## Key Comparison

| Tool | Applicability | Robustness | Implementation |
|------|--------------|------------|----------------|
| Sliding mode | Matched uncertainty | Excellent | Simple, chattering |
| Lyapunov redesign | Matched uncertainty | Good | Moderate |
| Backstepping | Triangular structure | Excellent | Complex recursion |
| Passivity-based | Passive/EL systems | Good | Physical insight |
| High-gain observer | Observable, bounded | Good | ε tuning needed |

---

## Hermes Application: Backstepping for Retry Controller

**Map to Hermes loop-pid.py:**
- x₁ = task error, x₂ = error_rate (derivative)
- Backstepping: design virtual control for x₁ (integral), then u for x₂ (PID)
- Produces explicit Lyapunov certificate V = c₁x₁² + c₂e₂² showing convergence

**Sliding mode for harness gate:**
- Sliding variable s = confidence - θ_threshold
- Control: switch model/action based on sgn(s)
- Finite-time convergence to confidence ≥ θ
