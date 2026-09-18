---
name: strogatz-dynamical-systems
description: "Use when detecting limit cycles or chaos in agent loops."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [dynamical-systems, chaos, bifurcation, limit-cycles, divergence]
    related_skills: [astrom-murray-feedback, ralph-loops, autonomous-agent-loop-design, trajectory-risk-guardrail]
triggers:
  - limit cycle oscillating agent
  - bifurcation config parameter
  - chaos sensitive dependence
  - period doubling loop
  - Kuramoto multi-agent synchronization
  - agent oscillating between states
  - nonlinear dynamics Strogatz
---

# Strogatz Nonlinear Dynamics and Chaos — Hermes Applications

Source: S.H. Strogatz, *Nonlinear Dynamics and Chaos*, 3rd ed.
Book: /var/home/rainbow/books/dynamical-systems/Nonlinear Dynamics and Chaos - With Applications to Physics, Biology, Chemistry, and Engineering.pdf

## 1. Fixed Points and 2-Cycles — Loop Convergence Detection (Ch 2)

Stable fixed point = converging loop. 2-cycle (period-2 orbit) = oscillates between two states indefinitely. Detect: record a hash of (output + error message) at each iteration. If the same hash recurs within 6 iterations, the loop is on a limit cycle — halt. Breaking a cycle requires changing an input condition, not repeating the same action.

Cross-reference: astrom-murray-feedback Lyapunov rule for scalar-error detection.

## 2. Bifurcations — Config Parameter Phase Transitions (Ch 3, 8)

Bifurcation: small parameter change causes qualitative behavioral shift (saddle-node, Hopf, etc.). Hermes mapping: config thresholds (compression.threshold, top_k, retry counts) can be bifurcation parameters. Safe tuning: change one parameter at a time, max 10% of current value. If behavior oscillates after a parameter change (context fills then doesn't, retries flood then stop), a Hopf bifurcation has occurred — revert immediately.

## 3. Limit Cycles — Looping Agent Behavior (Ch 7)

Limit cycle: isolated closed orbit; system oscillates at fixed amplitude regardless of initial conditions. Hermes mapping: agent loop cycling through same state sequence (write code → test fails → revert → write same code) is a limit cycle. State-hash detection (see above) catches this. Breaking requires a qualitatively different action (different tool, different approach, added constraint).

## 4. Chaos and Sensitive Dependence (Ch 9-12)

Chaotic systems: deterministic but sensitive to initial conditions (positive Lyapunov exponent). Hermes mapping: LLM outputs at temperature > 0 exhibit sensitive dependence near decision boundaries. Mitigation: temperature=0 for decision-critical calls; use N independent samples and take consensus to reduce effective sensitivity. Do NOT interpret a single output as representative when near a decision boundary.

## 5. Kuramoto Model — Multi-Agent Synchronization (Ch 4, extended in 3rd ed)

N oscillators synchronize when coupling K > K_c. Hermes mapping: subagents sharing heavy context (high K) converge to the same answer — defeats fan-out diversity. Subagents sharing no context (K=0) produce diverse, independent outputs — good for adversarial review. Rule: for adversarial/diverse fan-outs, minimize shared context. For coordinated synthesis, provide explicit shared context only after independent phases complete.

## Transfer Conditions

Applies when: well-defined state space, measurable state at each iteration, sequential causal iterations. Do NOT apply when: state space too high-dimensional to characterize, no persistent state across iterations.

## Pitfalls

- Period-doubling route to chaos: detect at 2-cycle stage before full chaos develops
- Chaos is deterministic, not random: don't confuse with stochastic failure
- Kuramoto coupling has no direct Hermes parameter; analogy is qualitative only
