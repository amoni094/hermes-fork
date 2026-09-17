# Chapters 10–11 — Perturbation Theory and Singular Perturbations

**Pages:** 401–483 (Ch. 10) and 424–484 (Ch. 11)  
**Lines in text:** ~(Ch.10 inferred ~18000-19766), Ch.11: 19767–21722

---

# Chapter 10 — Perturbation Theory and Averaging

## Overview
Asymptotic methods for systems with small parameter ε. Provides approximation tools without solving exactly.

## 10.1 Perturbation Method

System: ẋ = f(t,x,ε), with ε small.

**Regular perturbation:** If f is smooth in ε, expand solution as:
```
x(t,ε) = x₀(t) + εx₁(t) + ε²x₂(t) + ...
```
x₀ satisfies the unperturbed equation (ε=0), xᵢ satisfy linear variational equations.

**Validity:** Approximation valid on finite time intervals [0,T], error O(ε).

## 10.2 Averaging Method

System: ẋ = εf(t,x,ε), periodic in t with period T.

**Averaged system:** x̄˙ = εf_av(x̄) where:
```
f_av(x) = (1/T)∫₀ᵀ f(t,x,0) dt
```

**Theorem 10.4 (Averaging):** If x̄=0 is AS equilibrium of averaged system, and ε is small, then:
1. ∃ ε* such that for ε<ε*, original system has a unique periodic solution near origin
2. Periodic solution is AS
3. ‖x(t) - x̄(t)‖ = O(ε) on [0,1/ε]

**Vibrational control:** High-frequency oscillations can stabilize otherwise unstable systems via averaging.

---

# Chapter 11 — Singular Perturbations

## 11.1 Standard Model

**Singular perturbation model:**
```
ẋ = f(t, x, z, ε)     (slow dynamics, n-dim)
εż = g(t, x, z, ε)    (fast dynamics, m-dim)
```

Setting ε=0 reduces dimension: 0 = g(t,x,z,0) → z = h(t,x) (quasi-steady-state).

**Reduced (slow) model:** ẋ = f(t, x, h(t,x), 0)

**Boundary-layer (fast) model:** In stretched time τ=t/ε:
```
dz/dτ = g(t, x, z, 0)  with x, t frozen
```

## 11.2 Two-Time-Scale Behavior

**Tikhonov's Theorem (11.1):** On finite interval [0,T]:
```
x(t,ε) = x̄(t) + O(ε)
z(t,ε) = h(t, x̄(t)) + ẑ(t/ε) + O(ε)
```
where ẑ(τ)→0 exponentially (boundary layer correction decays fast).

**Conditions:**
1. Boundary-layer system GAS uniformly in (t,x)
2. Reduced system well-posed

## 11.3 Infinite-Time Interval

**Theorem 11.3:** If both reduced system and boundary-layer system are UAS, then:
- Solutions approximate on [0,∞): x(t,ε)=x̄(t)+O(ε), ∀t≥0
- Periodic solutions persist for small ε

## 11.5 Stability via Lyapunov

**Theorem 11.4:** If:
- V_s(t,x): Lyapunov function for reduced system (AS)
- V_f(t,x,z): Lyapunov function for boundary layer (AS, uniformly in x,t)

Then composite V = (1-d)V_s + dV_f satisfies Lyapunov conditions for full system (for appropriate d>0, ε small).

---

## Hermes Application: Two-Time-Scale Agent Systems

**Fast/slow decomposition for agent loops:**
- **Slow dynamics:** Session-level state (task progress, memory state)
- **Fast dynamics:** Per-turn token budget, compaction decisions

If fast dynamics (compaction) settle quickly relative to session progress:
- Use Tikhonov: approximate fast = quasi-steady-state
- Analyze session stability using reduced slow model
- Boundary layer correction bounded by O(ε) where ε = turn_time/session_time

**Practical implication:** Fast compaction decisions can be treated as quasi-static if they converge within O(1) turns while session evolves over O(10s) of turns.
