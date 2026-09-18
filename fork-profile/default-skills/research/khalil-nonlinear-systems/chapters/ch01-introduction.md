# Chapter 1 — Introduction

**Pages:** 1–34  
**Lines in text:** 375–1889

## Overview

Introduces the state-space formulation ẋ = f(t,x,u), y = h(t,x,u) and motivates nonlinear analysis through physical examples. Identifies key phenomena absent from linear systems.

## 1.1 Nonlinear Models and Nonlinear Phenomena

State equation:
```
ẋᵢ = fᵢ(t, x₁,...,xₙ, u₁,...,uₚ)
y_j = h_j(t, x₁,...,xₙ, u₁,...,uₚ)
```

**Nonlinear phenomena** (absent in linear systems):
- **Finite escape time** — solution blows up in finite time (e.g., ẋ = x²)
- **Multiple equilibria** — system rests at more than one point
- **Limit cycles** — stable oscillation not predictable by linear analysis
- **Chaos** — sensitive dependence on initial conditions
- **Subharmonic resonance** — response at submultiples of forcing frequency

## 1.2 Examples

### 1.2.1 Pendulum Equation
```
ẋ₁ = x₂
ẋ₂ = -(g/l)sin(x₁) - (b/m)x₂
```
Two equilibria: (0,0) stable, (π,0) unstable saddle.

### 1.2.2 Tunnel-Diode Circuit
Current i_R = h(v_R) is nonlinear S-shaped curve. Multiple equilibria possible.

### 1.2.3 Mass-Spring System
Duffing equation: ẍ + δẋ + αx + βx³ = γcos(ωt)

### 1.2.4 Negative-Resistance Oscillator (van der Pol)
```
ẍ - μ(1-x²)ẋ + x = 0
```
Limit cycle behavior; µ controls relaxation oscillation character.

### 1.2.5 Adaptive Control
Parameter update law creates nonlinear closed-loop even for linear plant.

### 1.2.6 Common Nonlinearities
- **Saturation:** sat(u) = sign(u)·min(|u|, L)
- **Dead zone:** no output for small inputs
- **Relay/hysteresis:** jump nonlinearities
- **Coulomb friction:** sign(ẋ) term

## Key Insight
Linear systems have a single equilibrium (if A is nonsingular) and no limit cycles. The superposition principle fails for nonlinear systems — responses cannot be added.

## Hermes Relevance
Retry loops, confidence scorers, and skill routers can exhibit multiple fixed points (e.g., "always escalate" vs. "always halt"). Phase portrait analysis (Ch. 2) applies to 2D state loops.
