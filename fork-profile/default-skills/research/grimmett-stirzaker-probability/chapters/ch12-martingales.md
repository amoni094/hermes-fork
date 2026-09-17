# Chapter 12: Martingales

## Core Idea
Martingales are processes with zero conditional drift. The filtration formalizes "available information." Stopping times encode "decisions based only on the past." The optional stopping theorem (OST) tells when the martingale property survives stopping — the key tool for computing first-passage probabilities and exit times.

## Frameworks Introduced

- **Martingale (Y, F) — Definition 12.1.8**:
  - Filtration F = {F0, F1, …}: increasing sequence of σ-fields (information grows over time)
  - Y adapted to F: Yn is Fn-measurable for all n
  - E|Yn| < ∞ and E(Yn+1 | Fn) = Yn a.s.
  - **Sub/supermartingale**: replace = with ≥ (sub) or ≤ (super)

- **Stopping time T (§12.4)**: T: Ω → {0,1,…,∞} with {T=n} ∈ Fn for all n.
  - Interpretation: decision to stop at time n uses only information available at n.
  - Examples: first passage times, first time a threshold is crossed.
  - NOT a stopping time: "stop just before a loss" (requires future knowledge).

- **Optional Stopping Theorem (OST) — Theorem 12.5.1**:
  E(YT) = E(Y0) if: (a) P(T<∞)=1, (b) E|YT|<∞, (c) E(Yn·I{T>n}) → 0.
  
- **Practical OST condition (Theorem 12.5.9)**:
  E(YT) = E(Y0) if P(T<∞)=1, ET<∞, and |Yn+1−Yn| has bounded conditional mean given Fn.

- **Doob's maximal inequality (Theorem 12.4.13)**:
  P(max_{0≤m≤n} Ym ≥ x) ≤ E(Yn⁺)/x for x>0.

- **Doob's upcrossing inequality**: (b-a)·E[U_n(a,b)] ≤ E[(Yn-a)⁺]. Forces convergence.

- **Backward martingales (§12.7)**: Yn indexed by decreasing n; useful for U-statistics and strong LLN.

- **Wald's equation (§12.5)**: If Xᵢ iid mean μ, T stopping time with ET<∞, then E(ST) = μ·ET.

- **Wald's identity (§12.5.15)**: For MGF M(t)=E(e^{tX}) with M(t)≥1 and T bounded-path stopping time: E[e^{tST}/M(t)^T] = 1.

## Key Concepts

- **Filtration Fn** — σ-field of events observable by time n; F0 ⊆ F1 ⊆ …
- **Adapted process** — Yn is Fn-measurable (Yn is "known" at time n)
- **Martingale** — adapted process with E(Yn+1|Fn) = Yn
- **Stopping time** — T with {T=n} ∈ Fn; the event "stop now" is Fn-measurable
- **σ-field FT** — events knowable by random time T: A ∈ FT iff A∩{T≤n} ∈ Fn for all n
- **Uniform integrability** — condition needed for L¹ convergence at stopping time
- **Harmonic function** — ψ:S→ℝ with (Pψ)(i) = ψ(i); yields martingale ψ(Xn) for Markov chain X
- **Optional switching** — switching between two martingales at a stopping time preserves the martingale property

## Anti-patterns

- **No filtration, no martingale**: Calling a sequence Sn a "martingale" without specifying the filtration is informal; the filtration determines what "conditional on the past" means.
- **Applying OST without checking conditions**: E(YT) = E(Y0) fails for the simple random walk stopped at first return to 0 (T is a.s. finite but E|YT| = ∞ check needed).
- **Confusing T finite a.s. with ET < ∞**: T finite a.s. does not imply ET < ∞ (geometric T can have ET = ∞).
- **Treating submartingale OST like martingale OST**: For submartingales, OST gives E(YT) ≥ E(Y0) only.

## Worked Example

**Symmetric random walk gambler's ruin** (§12.5.6): Sn = X₁+…+Xn with Xi iid ±1 equally likely. Let T = min{n: Sn = −a or Sn = b} for a,b > 0.

1. {Sn} is a martingale w.r.t. natural filtration.
2. T is a stopping time (first passage time to {-a, b}).
3. Check OST conditions: P(T<∞)=1 ✓, E|YT| = max(a,b) < ∞ ✓, condition (c) holds ✓.
4. E(ST) = E(S0) = 0.
5. Therefore: (−a)·P(ST=−a) + b·(1−P(ST=−a)) = 0 → P(ST=−a) = b/(a+b). ✓

Also: {Sn²−n} is a martingale. OST gives E(T) = a·b.

## Key Takeaways

1. A martingale REQUIRES a filtration — the pair (Y, F) is the fundamental object, not Y alone.
2. Stopping time T must have {T=n} ∈ Fn — "stop based on the past."
3. OST: E(YT) = E(Y0) under regularity conditions. Three conditions in Thm 12.5.1 are checkable.
4. The practical condition ET<∞ + bounded increments (Thm 12.5.9) covers most applications.
5. Wald's equation E(ST) = μ·E(T) is a special case of OST for iid sums.
6. Doob's maximal inequality: tail probability of the running maximum ≤ E(Yn⁺)/x.

## Connects To

- **Ch07**: Martingale convergence theorem proved via Doob's upcrossing inequality from here.
- **Ch06**: Harmonic functions of Markov chains yield martingales; OST solves first-passage problems.
- **Ch10**: Wald's equation connects to renewal theory via E(ST) = μ·E(T).
- **Ch13**: Continuous-time martingales; Itô integral as a (continuous) martingale.
