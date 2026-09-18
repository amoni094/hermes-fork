# Slotine & Li — Glossary

## Stability Terms

**Asymptotically stable:** Stable + x(t) → 0 as t→∞. Stronger than Lyapunov stable.

**Barbalat's Lemma:** If ∫g(t)dt converges and g is uniformly continuous, then g(t)→0.
Essential tool for proving convergence in MRAS without requiring dV/dt<0 strictly.

**Equilibrium:** Point x* where f(x*)=0 (system at rest). Usually shifted to origin.

**Exponentially stable:** ‖x(t)‖ ≤ k·e^{-λt}·‖x(0)‖; fastest decay class.

**GAS (Globally Asymptotically Stable):** Asymptotically stable for all initial conditions.

**Input-to-State Stable (ISS):** Bounded input → bounded state; perturbation decays.

**LaSalle Invariance Principle:** When dV/dt ≤ 0 (semi-definite), state converges to
largest invariant set M ⊆ {x: dV/dt=0}.

**Lyapunov stable:** ‖x(0)‖<δ implies ‖x(t)‖<ε for all t. State doesn't blow up.

**Negative definite:** V̇(x) < 0 for all x≠0. Sufficient for asymptotic stability.

**Negative semi-definite:** V̇(x) ≤ 0. Sufficient for Lyapunov stability only (need LaSalle for more).

**Positive definite:** V(x) > 0 for x≠0, V(0)=0. Required property of Lyapunov candidate.

**Radially unbounded:** V(x) → ∞ as ‖x‖ → ∞. Required for global results.

**Ultimate boundedness:** ‖x(t)‖ ≤ B for t ≥ T(x(0)). Practical stability under disturbances.

## Sliding Mode Terms

**Boundary layer (Φ):** Region |s| < Φ around sliding surface. Inside, use sat instead of sign.
Trades perfect sliding for chattering elimination. Error bound: O(Φ).

**Chattering:** High-frequency switching due to sign(s) discontinuity. Harmful in practice.

**Matched uncertainty:** Disturbance d in same subspace as control input B. Sliding mode rejects this.

**Reaching condition:** s·ṡ < 0. Guarantees state converges to surface s=0 in finite time.

**Reaching phase:** Before state hits s=0. Duration bounded by t* ≤ |s(0)|/η.

**Sliding phase:** After state hits s=0 and stays there. Dynamics reduced by one order.

**Sliding surface (s=0):** Hyperplane in state space. Designed so s=0 implies stable e dynamics.

**Sliding variable (s):** s = ė + λe (2nd order), or (d/dt + λ)^{n-1}e (nth order).
s=0 on surface means error decays at rate λ.

## Adaptive Control Terms

**Adaptation gain (Γ):** Matrix controlling speed of parameter update. Larger → faster but noisier.

**Leakage (σ-modification):** Term σθ̂ in adaptation law preventing unbounded parameter drift.

**MIT rule:** dθ̂/dt = -γ·(∂J/∂θ̂) gradient descent on error cost. Simple but may be unstable.

**MRAS (Model Reference Adaptive System):** Structure with reference model + adaptation law
driving plant to match reference model behavior. Stability proven via Lyapunov.

**Parameter convergence:** θ̂(t) → θ* (true value). Requires persistent excitation.

**Persistent Excitation (PE):** Regressor φ(t) sufficiently rich: ∫φφᵀdt ≥ αI > 0 over any window.
Required for parameter convergence; tracking convergence (e→0) does not require PE.

**Projection algorithm:** Constrains θ̂ to known feasible set. Gives robust bounded adaptation.

**Regressor (φ):** Vector of state features appearing linearly in plant dynamics: ẋ = φ(x,t)·θ + Bu.

**SPR (Strictly Positive Real):** Transfer function H(s) with Re[H(jω)] > 0 ∀ω. Required
for direct MRAS stability without additional compensator (Kalman-Yakubovich-Popov lemma).

**Tracking error (e):** e = x - x_m. MRAS drives e → 0 via adaptation of θ̂.

## PID / Hermes-Specific Terms

**Anti-windup (KAW):** Back-calculation gain preventing integrator wind-up during saturation.
Hermes: KAW=0.5, appears in augmented Lyapunov function V_aw.

**Bellman residual:** |V(s) - (r + γ·V(s'))| in DP/RL. Analog of integrator error.

**Contraction mapping:** If ‖f(x)-f(y)‖ ≤ L‖x-y‖ with L<1, unique fixed point exists.
loop-pid.py contraction_a = |de_k/de_{k-1}| < 1 → convergence indicator.

**Discrete Lyapunov decrease:** ΔV = V(k+1)-V(k) < 0. Discrete analog of dV/dt < 0.
loop-pid.py lyapunov_stable=True iff all steps have ΔV < 0.

**Span seminorm:** ‖v‖_sp = max_i v_i - min_i v_i. Puterman §6.6 stopping criterion for VI.

**Windup:** Integrator accumulating error during saturation, causing overshoot on recovery.
