# Ch 7 — Adaptive Control (Slotine & Li)

## Motivation

Fixed-gain controllers (PID, sliding mode with fixed k) are **open-loop over the parameter space**.
If plant parameters θ are unknown or vary, performance degrades. Adaptive control closes the
loop over parameters: θ̂ adjusts online based on performance error.

**Key insight (SLOTINE-CH7):** Fixed TTL in memory systems is the exact analog of fixed-gain
control — open-loop over the "forgetting rate" parameter. MRAS-inspired adaptive TTL closes
this loop.

## Model Reference Adaptive System (MRAS)

### Structure
```
Reference model:   ẋ_m = A_m x_m + B_m r    (desired closed-loop behavior)
Plant:             ẋ = A x + B u(θ̂)         (unknown θ, estimated by θ̂)
Tracking error:    e = x - x_m
Adaptation goal:   e → 0  as  t → ∞
```

### MIT Rule (Gradient Descent on Error)
```
dθ̂/dt = -γ · (∂e/∂θ̂) · e      (γ > 0: adaptation gain)
```
Simple but may be unstable for large reference inputs.

### Lyapunov-Based Adaptive Law (Stable)
Choose composite Lyapunov function:
```
V(e, θ̃) = eᵀPe + θ̃ᵀΓ⁻¹θ̃       (θ̃ = θ̂ - θ: parameter error)
```
where P ≻ 0 satisfies A_mᵀP + PA_m = -Q (Lyapunov equation), Γ ≻ 0 (adaptation rate).

Differentiating:
```
V̇ = eᵀ(A_mᵀP + PA_m)e + 2eᵀPB_m·(θ̃·φ) + 2θ̃ᵀΓ⁻¹θ̂̇
   = -eᵀQe + 2θ̃ᵀ(Γ⁻¹θ̂̇ + φ·B_mᵀPe)
```
Setting V̇ = -eᵀQe ≤ 0 gives the **stable adaptive law**:
```
θ̂̇ = -Γ · φ · B_mᵀPe        (regression-vector · error)
```
where φ is the regressor (features of state that multiply θ).

### Stability Conclusion
- V bounded → e ∈ L∞, θ̂ ∈ L∞  (signals remain bounded)
- V̇ = -eᵀQe ≤ 0 → ∫‖e‖² dt < ∞  (error is L₂)
- By Barbalat's Lemma (Ch 4): e → 0 (tracking error converges to zero)
- **θ̂ → θ** (parameter convergence) requires **persistent excitation (PE)** of φ

## Parameter Estimation

### Persistent Excitation (PE) Condition
The regressor φ(t) is **persistently exciting** if:
```
∃T, α₁, α₂ > 0: α₁I ≤ ∫_t^{t+T} φ(s)φᵀ(s)ds ≤ α₂I    ∀t
```
Without PE: e → 0 but θ̂ may not converge to true θ.
With PE: θ̂ → θ exponentially.

**Interpretation:** The system must be sufficiently excited (rich reference input) for
parameter identification. Constant reference → poor parameter convergence.

### Gradient Descent Form
```
θ̂̇ = Γ · φ · ε        (ε: prediction error, Γ: gain matrix)
```
This is **online least-squares / recursive gradient descent** on prediction error.

## Robustness Modifications

### σ-Modification (Ioannou & Sun)
```
θ̂̇ = -Γ·φ·eᵀPB - σ·θ̂      (σ > 0: leakage term)
```
Prevents parameter drift when signals are small. Gives ultimate boundedness of θ̂.

### Projection Algorithm
Constrains θ̂ to known compact set Θ:
```
θ̂̇ = Proj(Γ·ΔV/Δθ̂)
```
Guarantees ‖θ̂‖ ≤ θ_max always; robust to disturbances.

## SPR (Strictly Positive Real) Lemma

**Kalman-Yakubovich-Popov (KYP) lemma:** Transfer function H(s) is SPR iff there exist
P,Q≻0 and L such that:
```
AᵀP + PA + LᵀL = -Q
PB = Cᵀ
```
SPR is required for direct MRAS to be provably stable. If plant is not SPR, add a
**parallel feedforward compensator** to make error dynamics SPR.

## Adaptive Control ↔ Hermes Memory TTL (SLOTINE-CH7 Application)

| Control concept | Memory TTL analog |
|-----------------|-------------------|
| Fixed-gain k | Fixed TTL (e.g. 30 days) |
| Plant parameter θ | Memory decay rate |
| Tracking error e | recall_miss_rate |
| Adaptation law θ̂̇ = -Γ·φ·e | TTL adjustment from miss rate |
| PE condition | Sufficient query diversity |
| σ-modification | TTL floor (never expire too fast) |

**Adaptive TTL rule (MRAS-inspired):**
```
TTL_new = TTL_old - Γ · recall_miss_rate       (high misses → shorter TTL)
TTL_new = TTL_old + Γ · recall_hit_rate        (many hits → longer TTL)
TTL_new = max(TTL_min, min(TTL_max, TTL_new))  (projection: keep in bounds)
```
Reference: ~/.hermes/cache/recall-misses.jsonl for miss rate signal.

## Common Mistakes in Adaptive Control

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Using MIT rule without SPR check | May be unstable | Use Lyapunov-based law |
| No PE → claiming θ̂→θ | False; only e→0 | Require rich excitation |
| No σ-modification in practice | Parameter drift | Add leakage term |
| Adaptation gain Γ too large | Parameter chattering | Reduce Γ or use projection |
| Forgetting factor without bound | Parameter wind-up | Use projection or σ |
