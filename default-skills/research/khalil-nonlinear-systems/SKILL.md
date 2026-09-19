---
name: khalil-nonlinear-systems
description: >
  Knowledge base from Nonlinear Systems by Khalil. Use when applying Lyapunov stability,
  input-output stability, backstepping, feedback linearization, sliding mode control,
  Lyapunov functions for agent loop stability analysis. Source: Hassan K. Khalil,
  Nonlinear Systems, 3rd ed. (Prentice Hall, 2002), 767 pp.
tags: [control-theory, lyapunov, nonlinear-systems, stability, backstepping, feedback-linearization, sliding-mode, ISS, passivity, perturbations]
book_type: technical
depth: study
---

# Khalil — Nonlinear Systems (3rd Edition)

**Author:** Hassan K. Khalil  
**Publisher:** Prentice Hall, 2002  
**Pages:** 767  
**Core theme:** Analysis and design of nonlinear dynamical systems, with Lyapunov's method as the central thread.

---


## Model Routing

Stability analysis, Lyapunov function derivation: magistral-small-latest (mistral). Numerical simulation and verification: grok-4.6 workers via delegate_task.


## Book Structure (14 Chapters)

| Ch | Title | Key concepts |
|----|-------|-------------|
| 1 | Introduction | Nonlinear models, phenomena, common nonlinearities |
| 2 | Second-Order Systems | Phase portraits, limit cycles, Poincaré–Bendixson |
| 3 | Fundamental Properties | Existence, uniqueness, Lipschitz conditions, Gronwall |
| 4 | **Lyapunov Stability** | Lyapunov functions, LaSalle, linearization, ISS |
| 5 | **Input-Output Stability** | ℒ stability, small-gain theorem, ℒ₂ gain |
| 6 | **Passivity** | Positive real, storage functions, passivity theorem |
| 7 | Feedback Systems | Absolute stability, circle criterion, Popov criterion |
| 8 | Advanced Stability | Center manifold, region of attraction, nonautonomous |
| 9 | Stability of Perturbed Systems | Total stability, input-to-state stability extensions |
| 10 | Perturbation Theory | Averaging, Tikhonov theorem |
| 11 | Singular Perturbations | Two-time-scale, slow/fast decomposition |
| 12 | Feedback Control (intro) | Control objectives, linearization, gain scheduling |
| 13 | **Feedback Linearization** | Relative degree, zero dynamics, input-output linearization |
| 14 | **Nonlinear Design Tools** | Sliding mode, Lyapunov redesign, backstepping, passivity-based |

---

## Core Theorems (Quick Reference)

### Lyapunov Stability (Ch. 4)
**Theorem 4.1** — Let x=0 be equilibrium of ẋ=f(x), D⊂Rⁿ. If V:D→R is C¹ with:
- V(0)=0 and V(x)>0 in D\{0}
- V̇(x)≤0 in D

then x=0 is **stable**. If additionally V̇(x)<0 in D\{0}, then **asymptotically stable**.

**Theorem 4.2 (Global AS)** — If additionally V(x)→∞ as ‖x‖→∞ (radially unbounded), then x=0 is **globally asymptotically stable (GAS)**.

**Exponential Stability** — If α₁‖x‖ᵐ ≤ V(x) ≤ α₂‖x‖ᵐ and V̇ ≤ -α₃‖x‖ᵐ, then x=0 is **exponentially stable** with ‖x(t)‖ ≤ k‖x(0)‖exp(-γt).

### LaSalle's Invariance Principle (Sec. 4.2)
Let Ω be a compact positively invariant set for ẋ=f(x). Let E={x∈Ω | V̇(x)=0}. Let M be the largest invariant set in E. Then every solution starting in Ω approaches M as t→∞.

**Application:** Prove AS when V̇≤0 (not strictly), by showing M={0}.

### Input-to-State Stability — ISS (Sec. 4.9)
System ẋ=f(x,u) is **ISS** if there exist β∈KL, γ∈K such that:
```
‖x(t)‖ ≤ β(‖x(0)‖, t) + γ(sup_{s≤t} ‖u(s)‖)
```
Lyapunov-ISS condition: ∃ V with α₁(‖x‖) ≤ V ≤ α₂(‖x‖) and:
```
V̇(x,u) ≤ -α₃(‖x‖)  whenever  ‖x‖ ≥ σ(‖u‖)
```
**ISS implies BIBO**: bounded input ⟹ bounded state.

### ℒ Stability / Small-Gain Theorem (Ch. 5)
H:ℒₑⁿ→ℒₑⁿ is **finite-gain ℒ stable** if:
```
‖Hu‖_{ℒ,[0,T]} ≤ γ‖u‖_{ℒ,[0,T]} + β
```
**Small-Gain Theorem** — Interconnection of H₁ (gain γ₁) and H₂ (gain γ₂) is stable if γ₁γ₂ < 1.

### Passivity (Ch. 6)
System with storage function V≥0 is **passive** if:
```
V̇ ≤ uᵀy   (supply rate w(u,y) = uᵀy)
```
Strictly passive: V̇ ≤ uᵀy - ε‖y‖². **Passivity Theorem**: negative feedback of passive H₁ and strictly passive H₂ is stable.

### Feedback Linearization (Ch. 13)
For ẋ=f(x)+G(x)u, y=h(x), the **relative degree** r is smallest integer where:
```
Lg Lf^(r-1) h(x) ≠ 0
```
Control u=(v - Lf^r h(x)) / (Lg Lf^(r-1) h(x)) yields linear y^(r)=v.

**Zero dynamics**: Internal dynamics when y≡0. Minimum-phase ⟺ zero dynamics AS.

### Sliding Mode Control (Sec. 14.1)
Choose sliding manifold s(x)=0. Control u=-β(x)sgn(s) with β≥Q(x)+β₀ yields:
```
Ṡs ≤ -g₀β₀|s|  ⟹  |s(t)| ≤ |s(0)| - g₀β₀t
```
Reaches sliding manifold in **finite time** t_r ≤ |s(0)|/(g₀β₀). Motion on manifold is independent of matched uncertainties.

### Backstepping (Sec. 14.3)
Recursive design: for ẋ₁=x₂+φ₁(x₁), ẋ₂=u+φ₂(x):
1. Treat x₂ as virtual control; design α₁(x₁) to stabilize subsystem 1
2. Define error e₂=x₂-α₁, add Lyapunov term V₂=V₁+(1/2)e₂²
3. Design u to make V̇₂<0

Yields ISS certificates at each step.

---

## Key Class Functions

- **Class K:** α:[0,∞)→[0,∞), continuous, α(0)=0, strictly increasing
- **Class K∞:** Class K + unbounded  
- **Class KL:** β(r,s), K in r for each s, decreasing to 0 in s for each r

These characterize stability bounds in ISS and related theorems.

---

## Usage Patterns

Load `chapters/ch04-lyapunov-stability.md` for Lyapunov theorem details.  
Load `chapters/ch05-input-output-stability.md` for ℒ stability and small-gain.  
Load `chapters/ch14-nonlinear-design-tools.md` for backstepping/sliding mode.  
Load `patterns.md` for Hermes-specific application patterns.  
Load `cheatsheet.md` for formula lookup.  
Load `glossary.md` for terminology.

---

## Hermes Application Areas

| Hermes Component | Khalil Framework | Key Tool |
|-----------------|-----------------|---------|
| `loop-pid.py` retry loop | Lyapunov stability (Ch. 4) | Candidate V = error² |
| `metacognitive-harness.py` | ISS (Sec. 4.9) | Confidence as state, FOK/JOL as input |
| Skill routing (BIBO) | ℒ∞ stability (Ch. 5) | Small-gain theorem |
| `working-memory.py` convergence | LaSalle (Sec. 4.2) | Invariance principle |
| `rr_compaction_spike.py` | Region of attraction (Sec. 8.2) | Sublevel set estimate |
| Skill chain composition | ISS cascade (Sec. 4.9) | ISS composition |

See `patterns.md` and `/tmp/khalil_spikes.json` for spike proposals.
