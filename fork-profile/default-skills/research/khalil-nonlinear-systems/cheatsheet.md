# Cheatsheet — Khalil: Nonlinear Systems

## Stability Definitions

| Concept | Condition | Strength |
|---------|-----------|---------|
| Stable | ∀ε, ∃δ: ‖x(0)‖<δ ⟹ ‖x(t)‖<ε | Weakest |
| Asympt. Stable (AS) | Stable + x(t)→0 | Medium |
| Exponentially Stable | ‖x(t)‖ ≤ ke^{-γt}‖x(0)‖ | Strong |
| GAS | AS + region of attraction = Rⁿ | Global |
| ISS | ‖x(t)‖ ≤ β(‖x(0)‖,t) + γ(‖u‖∞) | With inputs |
| UUB | x(t) eventually in compact Ω | Bounded, not 0 |

---

## Lyapunov Theorems (Autonomous ẋ=f(x))

| Condition | Conclusion |
|-----------|-----------|
| V>0, V̇≤0 | Stable |
| V>0, V̇<0 | AS |
| V>0, V̇<0, V radially unbounded | GAS |
| V>0, V̇≤0, E={V̇=0}, M={0} | AS (LaSalle) |
| V(0)=0, ∃ region V>0 and V̇>0 | Unstable (Chetaev) |

---

## Nonautonomous Lyapunov (ẋ=f(t,x))

```
α₁(‖x‖) ≤ V(t,x) ≤ α₂(‖x‖)    (decrescent + pos. def.)
V̇(t,x) ≤ -α₃(‖x‖)              
→ UAS
```
Add α₁∈K∞: → GAS

---

## ISS Lyapunov Condition

```
α₁(‖x‖) ≤ V(x) ≤ α₂(‖x‖)
V̇(x,u) ≤ -α₃(‖x‖)  when  ‖x‖ ≥ σ(‖u‖)   (σ∈K)
→ ISS with gain γ = α₁⁻¹∘α₂∘σ (roughly)
```

---

## Discrete-Time Lyapunov (x(k+1)=F(x(k)))

```
ΔV(x) = V(F(x)) - V(x) ≤ -α₃(‖x‖) → AS
```
Same structure, replace V̇ with ΔV.

---

## ℒ Stability (Input-Output)

| Type | Condition | Implication |
|------|-----------|------------|
| ℒ stable | ‖(Hu)_T‖ ≤ α(‖u_T‖) + β | Bounded input → bounded output |
| Finite-gain ℒ | ‖(Hu)_T‖ ≤ γ‖u_T‖ + β | Linear gain bound |
| ℒ∞ stable | = BIBO | Bounded input → bounded output (pointwise) |

**Small-Gain:** H₁(γ₁) + H₂(γ₂) in feedback: stable if **γ₁γ₂ < 1**

---

## Passivity

```
Passive:         V̇ ≤ uᵀy
Output-strict:   V̇ ≤ uᵀy - ε‖y‖²
Input-strict:    V̇ ≤ uᵀy - δ‖u‖²
Lossless:        V̇ = uᵀy
```
**Passivity Theorem:** (Passive) + (strictly passive) in negative feedback → ℒ₂ stable.

---

## Class Functions

```
K:   α(0)=0, continuous, strictly increasing
K∞:  K + unbounded
KL:  β(r,s) ∈ K in r; β(r,s)→0 as s→∞
```

---

## Feedback Linearization (SISO)

```
System: ẋ=f(x)+g(x)u, y=h(x)
Relative degree r: L_g L_f^(r-1) h(x) ≠ 0
Linearizing control: u = [v - L_f^r h(x)] / [L_g L_f^(r-1) h(x)]
Result: y^(r) = v  (linear I/O)
Zero dynamics: η̇=q(0,η)  (when y≡0)
Minimum phase: zero dynamics AS
```

---

## Lie Derivatives

```
L_f h(x) = (∂h/∂x) f(x)           (first order)
L_f^k h = L_f(L_f^{k-1} h)        (iterated)
L_g L_f h = (∂L_f h/∂x) g(x)      (mixed)
```

---

## Backstepping (2-step)

```
ẋ₁ = f₁(x₁) + x₂
ẋ₂ = f₂(x₁,x₂) + u

Step 1: α₁(x₁) stabilizes ẋ₁=f₁+α₁, V₁=½x₁²
Step 2: e₂=x₂-α₁, V₂=V₁+½e₂²
        u = -c₂e₂ - x₁ - f₂ + (∂α₁/∂x₁)(f₁+x₂)
Result: V̇₂ = -c₁x₁² - c₂e₂² < 0 → GAS
```

---

## Sliding Mode Control

```
Manifold: s(x)=0
Control: u=-β(x)sgn(s), β(x)≥Q(x)+β₀
Lyapunov: V=½s²
V̇ ≤ -g₀β₀|s|   ← finite-time reaching
Reaching time: t_r ≤ |s(0)|/(g₀β₀)
On manifold: reduced dynamics independent of uncertainty
```

---

## Region of Attraction (ROA) Estimation

```
1. V(x) = xᵀPx  (from linearization: AᵀP+PA=-I)
2. c* = min_{x∈∂D} V(x)
3. ROA ⊇ {x | V(x) ≤ c*}
```

---

## Converse Lyapunov (Exponential Stability → Lyapunov fn exists)

```
Exponentially stable ⟺ ∃V with:
  c₁‖x‖² ≤ V(x) ≤ c₂‖x‖²
  V̇(x) ≤ -c₃‖x‖²
  ‖∂V/∂x‖ ≤ c₄‖x‖
```

---

## Singular Perturbation (Tikhonov)

```
ẋ = f(t,x,z,ε),  εż = g(t,x,z,ε)
Reduced: x̄˙ = f(t,x̄,h(t,x̄),0)  where 0=g(t,x̄,h,0)
Boundary layer: dẑ/dτ = g(t,x̄,x̄+ẑ,0)

Approximation (finite T): x=x̄+O(ε), z=h+ẑ+O(ε)
Conditions: boundary layer GAS, reduced system well-posed
```

---

## Averaging

```
ẋ = εf(t,x,ε),  f T-periodic in t
Averaged: x̄˙ = ε f_av(x̄) where f_av=(1/T)∫₀ᵀ f(t,x̄,0)dt
Error: ‖x(t)-x̄(t)‖=O(ε) on [0,1/ε]
```

---

## Linearization Stability

```
A = ∂f/∂x|_{x=0}
• A Hurwitz (all Re(λ)<0) → AS (locally)
• A has Re(λ)>0 eigenvalue → Unstable
• A has Re(λ)=0 eigenvalue → Inconclusive → use center manifold
```

---

## Lyapunov Equation (Linear Systems)

```
AᵀP + PA = -Q  (Q>0 given)
Unique solution P>0 ⟺ A Hurwitz
V(x) = xᵀPx:  V̇ = -xᵀQx ≤ -λmin(Q)‖x‖²
```

---

## ISS Cascade Composition

```
ẋ₁ = f₁(x₁,x₂)  ISS (x₂ as input)
ẋ₂ = f₂(x₂)     GAS
→ Cascade is GAS (if ISS gain doesn't cause growth)
General: ISS₁ + ISS₂ → ISS cascade if γ₁∘γ₂ < Id
```

---

## Key Inequalities

```
Gronwall: u≤α+∫βu ds  ⟹  u≤α·exp(∫β ds)
Young:    ab ≤ a²/(2ε) + εb²/2
Cauchy-Schwarz: |uᵀv| ≤ ‖u‖·‖v‖
Comparison: u̇≤f(u)≤v̇=f(v), v(0)≥u(0) ⟹ u(t)≤v(t)
```
