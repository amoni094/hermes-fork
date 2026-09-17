---
name: astrom-murray-feedback
description: "Use for stable agent loops, runaway detection, retries."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [control-theory, stability, feedback, agent-loop, lyapunov, sensitivity]
    related_skills: [ralph-loops, autonomous-agent-loop-design, agent-runtime-loop-patterns, puterman-mdp, boyd-convex-optimization]
triggers:
  - agent loop stability
  - runaway iteration detection
  - Lyapunov
  - sensitivity waterbed effect
  - gain margin phase margin
  - integral windup retry cap
  - PID feedback control
  - feedforward vs feedback planning
---

# Astrom-Murray Feedback Systems — Hermes Applications

Source: K.J. Astrom & R.M. Murray, *Feedback Systems*, 2nd ed. (2020).
Book: /var/home/rainbow/books/control/astrom-murray-feedback-systems.pdf

## 1. Lyapunov Stability — Runaway Loop Detection (Ch 4)

If V(x) (a positive-definite scalar error metric) is non-decreasing over 3 consecutive iterations, the loop has no Lyapunov certificate — halt and report the stall. Do not keep iterating. Exception: if the metric is intentionally non-monotone (exploration phase), use a 5-step window requiring >20% improvement over the window. Pre-condition: define the error metric before the loop starts.

## 2. Sensitivity and Waterbed Effect (Ch 12)

S + T = 1 (sensitivity + complementary sensitivity). Bode integral: reducing sensitivity at one failure mode increases it elsewhere. Rule: identify the highest-cost failure mode, tune timeout/retry for that, accept increased sensitivity in less-costly modes. Do not chase every individual failure with a tighter timeout — it will create a new failure mode elsewhere.

## 3. Integral Windup — Retry Queue Cap (Ch 11)

Integrator accumulates while saturated, then overshoots when saturation clears. Analogy: retry queue grows unbounded while blocked, floods resource when unblocked. Rule: hard cap at 3 retries per tool call regardless of wait time; exponential back-off (2x previous gap) is the anti-windup equivalent. Wire into agent-runtime-loop-patterns.

## 4. Gain and Phase Margin — Agent Coupling Robustness (Ch 10)

G_m > 6 dB, phi_m > 30 deg for robust design. Hermes analogy: high inter-agent coupling (Agent B depends heavily on Agent A's raw output) = low gain margin = fragile fan-out. Mitigation: add a validation/normalization step between coupled agents. A fan-out where all downstream agents depend on one upstream agent has near-zero gain margin — that agent is a single point of failure; flag in SCOPE field of Node Prompt Contract.

## 5. Feedforward vs Feedback — Planning vs Reactive Execution (Ch 1-2)

Feedforward: preemptive, fast, requires accurate model. Feedback: reactive, robust to model error, slower. Mapping:
- Well-understood repeatable tasks → feedforward (plan fully upfront, parallel-frontier dispatch)
- Novel or uncertain tasks → feedback (check each step, ordered-dependency dispatch)
- Hybrid: feedforward for known parts, feedback gates at uncertainty checkpoints

## Transfer Conditions

Applies when: measurable scalar error signal, clear target equilibrium, sequential iterations with feedback. Do NOT apply when: error is purely categorical, agents run fully in parallel with no inter-agent feedback, no defined target state.

## Pitfalls

- Lyapunov requires the error metric defined before the loop, not discovered mid-loop
- Waterbed arguments are aggregate system properties, not per-call
- Integral windup analogy breaks if retry queue is truly unbounded (no saturation point)
- Gain/phase margin: the agent-coupling analogy is structural, not frequency-domain exact
