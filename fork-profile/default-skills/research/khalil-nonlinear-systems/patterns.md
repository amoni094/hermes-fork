# Patterns — Khalil: Nonlinear Systems (Hermes Applications)

## Pattern 1: Lyapunov Stability Proof Template

**When to use:** Proving convergence of any iterative agent loop.

**Setup:** Agent state x∈Rⁿ, update rule x(k+1)=F(x(k)) or ẋ=f(x) (continuous approximation).

**Steps:**
1. Identify candidate V(x) (try V=‖e‖² where e = error = x-x*)
2. Compute V̇ = (∂V/∂x)·f(x) or ΔV=V(F(x))-V(x)
3. Show V̇ ≤ -α₃(‖x‖) for some α₃∈K → AS
4. If V radially unbounded → GAS

**Discrete analog:**
```python
def lyapunov_check(x, x_prev, target=0):
    V_now = np.sum((x - target)**2)
    V_prev = np.sum((x_prev - target)**2)
    delta_V = V_now - V_prev
    return delta_V < 0  # Lyapunov decrease condition
```

**Pitfall:** V̇≤0 (non-strict) → use LaSalle, not direct AS claim.

---

## Pattern 2: ISS Analysis for Input-Driven Systems

**When to use:** Agent receives noisy inputs, need to bound state deviation.

**Framework:** System is ISS if:
```
‖x(t)‖ ≤ β(‖x(0)‖, t) + γ(sup_s ‖u(s)‖)
```
- β∈KL: transient decay
- γ∈K: steady-state gain from input

**Check (Lyapunov-ISS):** Find V with:
```
V̇(x,u) ≤ -α₃(‖x‖)  whenever  ‖x‖ ≥ σ(‖u‖)
```
where σ∈K. Then system is ISS with gain γ related to σ.

**Hermes application:** Metacognitive harness state = (confidence_score, attempt_count).
- Input u = model output noise
- Show: harness drives confidence to [θ,1] despite noise when ‖noise‖<δ
- ISS gain γ: δ·γ gives bound on steady-state confidence error

---

## Pattern 3: Small-Gain Stability Check for Feedback Loops

**When to use:** Two subsystems in feedback (e.g., harness ↔ skill executor).

**Framework:**
```
H₁ (executor): ‖y₁‖ ≤ γ₁‖u₁‖ + β₁
H₂ (controller): ‖y₂‖ ≤ γ₂‖u₂‖ + β₂
Feedback: u₁=y₂, u₂=y₁
Stable if: γ₁·γ₂ < 1
```

**Practical computation:**
```python
def small_gain_check(gamma1, gamma2):
    """Returns True if feedback loop stable by small-gain theorem."""
    return gamma1 * gamma2 < 1

# Estimate gains from traces:
# gamma_i ≈ max(|output| / |input|) over logged sessions
```

**Hermes loop-pid.py mapping:**
- γ₁ = max error amplification by skill executor (estimate from logs)
- γ₂ = PID controller gain = Kp + Ki·T + Kd/T (from Kp,Ki,Kd in script)
- Check: γ₁·γ₂ < 1 for stability

---

## Pattern 4: LaSalle Invariance for Working Memory Convergence

**When to use:** Want to show working memory state converges without strict V̇<0.

**Framework (autonomous working-memory.py):**
1. V = "distance from target memory state" (e.g., ‖WM - WM_ideal‖²)
2. Show V̇ ≤ 0 (each WM update either reduces V or keeps it same)
3. Find E = {states where V̇=0} (e.g., WM unchanged after update)
4. Find M = largest invariant set in E
5. If M = {WM_ideal}, conclude WM→WM_ideal

**Key question:** What is the invariant set? For working memory with bounded capacity, the invariant set is the "full and stable" state.

```python
def check_lasalle_condition(wm_state, wm_prev, v_func):
    V_now = v_func(wm_state)
    V_prev = v_func(wm_prev)
    dV = V_now - V_prev
    if dV > 0:
        return "VIOLATION: V increasing"
    elif dV == 0:
        return "NEUTRAL: check if in invariant set"
    else:
        return "DECREASING: good"
```

---

## Pattern 5: Region of Attraction Estimation for Safe Operation

**When to use:** Estimating safe operating range for context compaction or lambda-tuner.

**Framework (rr_compaction_spike.py):**
- State x = (lambda, budget_fraction) ∈ R²
- Fixed point x* = (lambda_opt, budget_nominal)
- Lyapunov V = (x-x*)ᵀP(x-x*) from linearized dynamics
- ROA estimate: Ωc = {x | V(x) ≤ c} where c = min_{boundary} V

```python
import numpy as np

def estimate_roa(P, x_star, boundary_points):
    """Sublevel set estimate of region of attraction."""
    c_star = min(
        (p - x_star) @ P @ (p - x_star)
        for p in boundary_points
    )
    def in_roa(x):
        delta = x - x_star
        return delta @ P @ delta <= c_star
    return in_roa, c_star
```

**Warning:** This is only inner estimate. True ROA may be larger.

---

## Pattern 6: Backstepping for Cascaded Agent Subsystems

**When to use:** Agent system decomposes into cascade: error → action → outcome.

**Cascade:** x₁˙=f₁(x₁,x₂), x₂˙=f₂(x₂,u)

**Backstepping recipe:**
1. Design α₁(x₁) to stabilize ẋ₁=f₁(x₁,α₁), with V₁
2. Define e₂=x₂-α₁
3. Design u to stabilize e₂ subsystem, with V₂=V₁+½e₂²
4. Composite V₂ certifies full cascade

**Hermes mapping:**
- x₁ = task progress error
- x₂ = confidence (virtual control for x₁)
- u = model selection / retry action
- α₁(x₁) = target confidence needed for this error level

---

## Pattern 7: Sliding Mode for Hard Threshold Enforcement

**When to use:** Hard enforce a threshold (e.g., confidence ≥ θ_min) in finite time.

**Setup:** Agent "state" s = confidence - θ_min. Control: choose action to make ṡ≥0 or ṡ=0 when s<0.

**Sliding mode analog:**
```python
def sliding_mode_action(confidence, threshold, actions):
    """Choose action to drive confidence above threshold."""
    s = confidence - threshold
    if s < 0:  # Below sliding surface
        # Choose most confidence-increasing action
        return actions['escalate']  # β·sgn(s) analog
    else:  # On or above sliding surface
        # Normal operation
        return actions['proceed']
```

**Finite convergence:** If each action increases confidence by ≥ δ_min, threshold reached in at most (θ_min - confidence_0)/δ_min steps.

---

## Pattern 8: Discrete-Time Lyapunov for Retry Loop Analysis

**When to use:** Analyzing convergence of discrete retry loops in loop-pid.py.

**Discrete Lyapunov:** For x(k+1)=F(x(k)):
- V: Rⁿ→R positive definite
- ΔV(x) = V(F(x)) - V(x) ≤ -α₃(‖x‖) → AS

**For loop-pid.py:**
```python
# State: [error, integrator, prev_error]
# Update: PID step
# Lyapunov candidate: V = error² + Ki·integrator²

def pid_lyapunov_check(e_new, e_old, integrator_new, integrator_old, Kp, Ki):
    V_new = e_new**2 + Ki * integrator_new**2
    V_old = e_old**2 + Ki * integrator_old**2
    return V_new - V_old  # Should be negative for convergence
```

**Anti-windup connection:** Anti-windup (KSAW in script) prevents integrator from growing unboundedly — corresponds to ensuring ISS with respect to integrator saturation.

---

## Pattern 9: ISS Cascade Composition for Skill Chains

**When to use:** Multi-skill pipeline where each skill's output feeds next.

**ISS Cascade Theorem:** If:
- Skill k is ISS: ‖xₖ‖ ≤ βₖ(‖xₖ(0)‖,t) + γₖ(‖xₖ₋₁‖∞)
- Gains compose: γ₁∘γ₂∘...∘γₙ(r)<r for some r>0 (no gain blowup)

Then the cascade is ISS.

**Practical check:**
```python
def iss_cascade_gain(gains):
    """Approximate cascade gain (assumes linear gains γᵢ(r)=gᵢ·r)."""
    total = 1.0
    for g in gains:
        total *= g
    return total  # Chain is ISS if total < 1 (linear case)
```

**Note:** Non-linear gains require more careful analysis (composition of K functions).

---

## Pattern 10: Nonautonomous Stability for Time-Varying Skill Routing

**When to use:** Skill routing changes over time (e.g., due to session context).

**Framework (Theorem 4.9):**
- V(t,x) with α₁(‖x‖) ≤ V(t,x) ≤ α₂(‖x‖)
- V̇(t,x) ≤ -α₃(‖x‖)
- Conclusion: UAS (uniform in time)

**Key:** If routing changes "slowly" (slowly varying) → use frozen-time analysis (Ch. 9.4). If routing changes arbitrarily fast → need common Lyapunov function across all routing modes.
