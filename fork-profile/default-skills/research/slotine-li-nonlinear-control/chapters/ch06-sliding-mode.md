# Ch 6 — Sliding Mode Control (Slotine & Li)

## Core Idea

Design a **sliding surface** s(x) = 0 in state space. Force the system onto this surface
in finite time (reaching phase), then constrain motion on the surface (sliding phase).
On the surface, dynamics reduce to a lower-order, nominally stable system.

Benefits:
- **Robust to matched uncertainties** (disturbances in the range of control input)
- **Finite-time reaching** guaranteed
- **Order reduction:** n-th order system becomes (n−1)-th order on surface

## Sliding Surface Design

### General Form
For tracking error e = x - xd:
```
s = (d/dt + λ)^{n-1} e        (Slotine §6.1)
```
where λ > 0 is a bandwidth parameter. For 2nd-order (n=2):
```
s = ė + λe
```
On the surface s = 0: ė = -λe → e decays exponentially with rate λ.

### Physical Interpretation
s = 0 defines a hyperplane. Once the state hits this plane, the controller keeps it there.
The sliding phase dynamics are determined entirely by the surface design, not the plant.

## Reaching Condition

**Condition:** s · ṡ < 0  (state is always moving toward s = 0)

**Strong form (η-reachability):**
```
(1/2) d/dt(s²) ≤ -η|s|        η > 0
```
This guarantees reaching in **finite time** t_reach ≤ |s(0)|/η.

### Reaching Control Law
For system ẍ = f(x,t) + b(x,t)u with uncertainty:
```
u = -(1/b̂)[f̂ + ẍd - λė + k·sign(s)]
```
where k must be large enough to overcome uncertainty bounds.

## Chattering Problem

**Chattering:** High-frequency switching of sign(s) causes:
- Mechanical wear in actuators
- Excitation of unmodeled high-frequency dynamics
- Numerical issues in simulation

**Root cause:** Discontinuous sign(s) requires infinite switching bandwidth.

### Boundary Layer Solution (Slotine §6.4)

Replace sign(s) with a continuous saturation inside boundary layer Φ:
```
u = -(1/b̂)[f̂ + ẍd - λė + k·sat(s/Φ)]
```
where:
```
sat(s/Φ) = s/Φ    if |s| < Φ
            sign(s) if |s| ≥ Φ
```

**Trade-off:** Boundary layer converts perfect sliding to **practical stability** — error
is ultimately bounded within O(Φ). Smaller Φ → less chattering but smaller bound.

## Uncertainty Handling

Assume:
```
f(x,t) = f̂(x,t) + Δf(x,t)     with |Δf| ≤ F(x)
b(x,t) ∈ [b_min, b_max]
```

**Sufficient gain:** k ≥ F(x)/b_min + η guarantees reaching condition despite uncertainty.
This is **robust** — exact knowledge of f not needed, only its bounds.

## Lyapunov Proof of Sliding Mode

Choose V = (1/2)s²:
```
V̇ = s·ṡ
```
Reaching condition s·ṡ ≤ -η|s| = -η√(2V):
```
d/dt(√(2V)) ≤ -η
```
Integrating: √(2V(t)) ≤ √(2V(0)) - ηt → reaches zero in finite time t* ≤ √(2V(0))/η.

## Comparison with PID / Lyapunov

| Aspect | Lyapunov | Sliding Mode |
|--------|----------|--------------|
| Nominal stability | Proven via V(x) | Proven via Lyapunov of s |
| Robustness to uncertainty | Requires bounding | Explicit bounds via k |
| Chattering | Not applicable | Key limitation |
| Convergence | Asymptotic (often) | Finite-time to surface |
| Hermes relevance | loop-pid.py stability | Discrete: s = e_k + λ·Δe |

## Discrete-Time Sliding Mode (for Agent Loops)

Continuous → discrete analog for Hermes loop-pid.py:
```
s_k = e_k + λ·(e_k - e_{k-1})      (discrete sliding variable)
Reaching: s_k · (s_k - s_{k-1}) < 0  (discrete reaching condition)
```
If s_k oscillates across zero with bounded amplitude → sliding achieved in practice.

## Higher-Order Sliding Mode (HOSM)

To avoid chattering, drive s, ṡ, s̈, ..., s^{(r-1)} to zero simultaneously.
r = 1: standard sliding mode
r = 2: twisting algorithm, super-twisting algorithm (STA)
STA is smooth and widely used: requires only s, not ṡ.
