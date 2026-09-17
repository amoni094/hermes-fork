# Slotine & Li — Nonlinear Control Cheatsheet

## Method Selection Decision Tree

```
Is plant model fully known?
├── YES → Is model linear? 
│         ├── YES → PID / LQR / pole placement
│         └── NO  → Feedback linearization (Ch 8) or Lyapunov-based nonlinear control
└── NO  → Are parameter bounds known?
          ├── YES → Sliding mode control (Ch 6): robust to bounded uncertainty
          └── NO  → Adaptive control / MRAS (Ch 7): identify parameters online

Is finite-time convergence required?
├── YES → Sliding mode (guaranteed reaching time t* ≤ |s(0)|/η)
└── NO  → Lyapunov asymptotic stability is sufficient

Is chattering acceptable?
├── YES → Standard sliding mode with sign(s)
└── NO  → Boundary layer (sat(s/Φ)) or higher-order sliding mode (STA)
```

## Stability Checklist (Lyapunov)

- [ ] V(x) > 0 for x ≠ 0, V(0) = 0
- [ ] dV/dt ≤ 0 along trajectories (compute ∂V/∂x · f(x))
- [ ] If dV/dt ≤ 0 only (semi-definite): apply LaSalle — find largest invariant set in {dV/dt=0}
- [ ] For global results: V radially unbounded (V → ∞ as ‖x‖ → ∞)
- [ ] For practical stability: dV/dt ≤ -α‖x‖² + γδ² (ultimate bound = O(δ))

## Stability Checklist (Sliding Mode)

- [ ] Sliding surface s(x) = 0 chosen so s=0 is stable
- [ ] Reaching condition: s·ṡ < 0 (or ‖(1/2)d/dt(s²)‖ ≤ -η|s|)
- [ ] Controller gain k ≥ uncertainty bound F(x)/b_min + η
- [ ] If chattering: add boundary layer of width Φ
- [ ] Document ultimate bound: ‖e‖ ≤ O(Φ) on sliding surface

## Stability Checklist (Adaptive / MRAS)

- [ ] Reference model A_m is Hurwitz (all eigenvalues stable)
- [ ] Lyapunov equation AᵀP + PA = -Q has solution P ≻ 0
- [ ] Adaptive law: θ̂̇ = -Γ·φ·Bᵀ_m·Pe (derived from V̇ cancellation)
- [ ] V = eᵀPe + θ̃ᵀΓ⁻¹θ̃ gives V̇ = -eᵀQe ≤ 0
- [ ] Apply Barbalat: e ∈ L∞ ∩ L₂ and ė ∈ L∞ → e → 0
- [ ] For θ̂ → θ: verify persistent excitation of regressor φ

## Key Inequalities

| Name | Inequality | When Used |
|------|-----------|-----------|
| AM-GM | ab ≤ (a²+b²)/2 | Bounding cross terms in V̇ |
| Young's | ab ≤ εa² + b²/(4ε) | Completing the square |
| Gronwall | V̇ ≤ αV + β → V(t) ≤ e^{αt}V(0) + β(e^{αt}-1)/α | Bounding solutions |
| Cauchy-Schwarz | |∫fg| ≤ ‖f‖₂‖g‖₂ | Bounding integrals |

## Barbalat's Lemma (Quick Reference)

**Conditions:** (1) lim_{t→∞} ∫₀ᵗ g(τ)dτ exists and finite, (2) g uniformly continuous  
**Conclusion:** g(t) → 0  

**Sufficient for (2):** ġ bounded  
**Use in MRAS:** V̇ = -eᵀQe → ∫‖e‖² dt finite; if ë bounded → e → 0

## Hermes loop-pid.py Connections

| loop-pid.py command | Slotine theory |
|--------------------|----------------|
| `lyapunov-check` | Ch 5: V=e²+(Ki/Kp)·I², checks ΔV<0 (discrete Lyapunov decrease) |
| `gain-check` | Ch 6: gain margin ↔ sliding mode gain k ≥ F/b_min |
| `span-check` | Ch 5: span seminorm stopping ↔ LaSalle: e stable when ‖e‖ small |
| `line-search` | Ch 5: Lyapunov descent direction in PID parameter space |
| Anti-windup KAW | Ch 6: Saturation → boundary layer; Ch 5: augmented V with windup term |
| `step` CONVERGED | LaSalle: largest invariant set reached; Bellman residual < ε |

## Quick Symbol Reference

| Symbol | Meaning |
|--------|---------|
| V(x) | Lyapunov function candidate |
| dV/dt, V̇ | Time derivative along trajectories |
| s(x) | Sliding variable (s=0 is surface) |
| η | Reachability margin (s·ṡ ≤ -η|s|) |
| Φ | Boundary layer thickness |
| θ, θ̂, θ̃ | True, estimated, error parameter |
| Γ | Adaptation gain matrix |
| φ | Regressor vector |
| PE | Persistent excitation |
| SPR | Strictly positive real |
