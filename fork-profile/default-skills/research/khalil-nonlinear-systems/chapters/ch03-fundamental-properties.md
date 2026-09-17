# Chapter 3 — Fundamental Properties

**Pages:** 75–110  
**Lines in text:** 4173–5262

## Overview

Establishes mathematical foundation for state equations: when solutions exist, are unique, and depend continuously on initial conditions and parameters. Essential prerequisites for Lyapunov analysis.

## 3.1 Existence and Uniqueness

**Theorem 3.1 (Local Existence and Uniqueness):** If f(t,x) is piecewise continuous in t and satisfies the **Lipschitz condition**:
```
‖f(t,x) - f(t,y)‖ ≤ L‖x - y‖
```
for all x,y in a ball Bᵣ(x₀) and t∈[t₀,t₁], then there exists τ>0 such that ẋ=f(t,x) has a unique solution on [t₀,t₀+τ].

**Lipschitz condition** is satisfied when ∂f/∂x is bounded (sufficient condition).

**Global existence (Theorem 3.2):** If f is globally Lipschitz (or linearly bounded), solution exists for all t≥t₀.

## 3.2 Continuous Dependence on Initial Conditions

**Theorem 3.3:** Solutions depend continuously on initial conditions and parameters. If f satisfies Lipschitz, then:
```
‖x(t;x₀) - x(t;y₀)‖ ≤ ‖x₀-y₀‖ · e^{L(t-t₀)}
```
This bounds the divergence of nearby trajectories (not chaos, but controlled separation).

## 3.3 Gronwall Inequality

**Lemma (Gronwall):** If u(t) ≤ α + ∫_{t₀}^t β(s)u(s)ds, then:
```
u(t) ≤ α · exp(∫_{t₀}^t β(s)ds)
```
**Ubiquitous tool:** Used to bound trajectory errors in perturbation arguments and stability proofs.

## 3.4 Differentiability with Respect to Parameters

If f depends on parameter p, solutions x(t;p) are differentiable in p when f is C¹ in p. Sensitivity matrix S = ∂x/∂p satisfies a linear ODE.

## 3.5 Comparison Functions and Lemma

**Comparison Lemma:** If ẋ ≤ f(t,x) and ẏ = f(t,y), y(t₀) ≥ x(t₀), then x(t) ≤ y(t) for t≥t₀.

Used to bound trajectories without solving the equation exactly.

## Key Definitions
- **Locally Lipschitz:** Lipschitz on every compact set (weaker than global Lipschitz)
- **Class C¹ ⟹ locally Lipschitz** (via mean value theorem)

## Hermes Relevance
Lipschitz continuity of skill routing functions (score → action mapping) ensures that small perturbations in inputs produce bounded output changes. The Gronwall inequality is the discrete-time analog used to bound error accumulation across multi-step agent chains.
