# Cheatsheet — Probability and Random Processes (G&S 4th ed.)

Decision guide for applying G&S results in practice (especially to Hermes).

---

## 1. Which convergence mode do you need?

| Goal | Mode needed | Condition |
|------|------------|-----------|
| "Will average converge?" | a.s. or L² | E\|X₁\| < ∞ (a.s.); E(X₁²) < ∞ (L²) |
| "Distribution converges?" | In distribution | Char. functions converge (Lévy) |
| "Probability of deviation?" | In probability | Chebyshev, Markov, or weak LLN |
| "L¹ convergence at stopping time?" | UI + a.s. | Uniform integrability needed |

**Decision rule**: If you only care about long-run averages → L² suffices. If you need sample-path guarantees → a.s. If statistical test performance → in distribution (CLT).

---

## 2. Is this sequence a martingale? (CHECKLIST)

Before claiming (Yn) is a martingale, verify ALL:
- [ ] There is a specified filtration F = {Fn}
- [ ] Yn is Fn-measurable (adapted)
- [ ] E\|Yn\| < ∞ for all n
- [ ] E(Yn+1 \| Fn) = Yn a.s.

**If any box is unchecked → it is NOT formally a martingale.** Mark as LOW confidence for OST applications.

⚠️ **Hermes agents**: A sequence of accumulated scores Sn is NOT automatically a martingale. Need to verify: (1) defined filtration (e.g., Fn = σ(X1,...,Xn)), (2) increments have zero conditional mean given past.

---

## 3. Can you apply the Optional Stopping Theorem?

**Scenario**: You have a martingale (Y,F) and stopping time T. You want E(YT) = E(Y0).

| Condition | Check | Easy sufficient |
|-----------|-------|-----------------|
| T finite a.s. | P(T<∞)=1 | T = first passage to a closed set |
| YT integrable | E\|YT\|<∞ | Y bounded at time T |
| Tail vanishes | E(Yn·I{T>n})→0 | ET < ∞ + bounded increments (Thm 12.5.9) |

**Recommended sufficient conditions (Thm 12.5.9)**:
- P(T<∞)=1 ✓
- ET < ∞ ✓
- E(\|Yn+1−Yn\| \| Fn) ≤ c for all n < T ✓

**Common failure**: T is a.s. finite but ET = ∞ and increments are unbounded → OST may fail.

---

## 4. Markov chain limit behavior

| Chain type | Long-run behavior |
|-----------|------------------|
| Irreducible + transient | P(visit state i i.o.) = 0; pij(n)→0 |
| Irreducible + null recurrent | No stationary distribution; pij(n)→0 |
| Irreducible + positive recurrent | Unique π; pij(n)→πj iff also aperiodic |
| Finite + irreducible | Always positive recurrent |

**Mixing rate**: τmix ≈ 1/(1−λ₂) where λ₂ = second eigenvalue. Small spectral gap = slow mixing.

---

## 5. Renewal theory decision rules

| Question | Answer | Formula |
|----------|--------|---------|
| Long-run rate of events? | 1/μ | Elementary renewal theorem |
| Expected events by time t? | ≈ t/μ for large t | m(t)/t → 1/μ |
| Expected wait for next event (at stationarity)? | (μ² + σ²)/(2μ) | Inspection paradox |
| When to use Poisson model? | Exactly when renewal + Markov holds | Unique memoryless inter-arrivals |
| Availability of alternating system? | E(up)/(E(up)+E(down)) | Key renewal theorem |

---

## 6. Characteristic function identifiers (quick table)

| Distribution | CF φ(t) |
|-------------|---------|
| N(μ,σ²) | exp(iμt − σ²t²/2) |
| Poisson(λ) | exp(λ(e^{it}−1)) |
| Bernoulli(p) | 1−p+pe^{it} |
| Exp(λ) | λ/(λ−it) |
| Cauchy(0,1) | exp(−\|t\|) |
| Uniform[a,b] | (e^{ibt}−e^{iat})/(i(b−a)t) |
| Binomial(n,p) | (1−p+pe^{it})^n |

**Independence test**: X⊥Y iff φ_{X,Y}(s,t) = φX(s)·φY(t) for ALL (s,t). (Condition only on diagonal t=s is insufficient.)

---

## 7. Hermes application decision rules

| Hermes problem | G&S tool | Condition to check |
|----------------|----------|-------------------|
| "Should the retry loop terminate?" | OST (Ch12) | Verify sequence forms a martingale w.r.t. a filtration; check E(T)<∞ |
| "Has skill routing converged?" | Markov chain mixing (Ch06) | Irreducible + aperiodic + spectral gap > 0 |
| "Estimate skill usage frequency" | Strong LLN (Ch07) | E\|X₁\| < ∞; n large enough for error ≤ 1.96σ/√n |
| "Confidence interval on skill perf." | CLT (Ch05) | iid samples, n≥30, finite variance |
| "Detect anomaly in agent metrics" | Doob maximal inequality (Ch12) | Need a (sub)martingale — verify conditions |
| "Schedule cache refresh" | Renewal-reward (Ch10) | i.i.d. TTLs; optimal rate = 1/μ |
| "Analyze skill embedding distribution" | Characteristic functions (Ch05) | Always applicable; identify via φ |

---

## 8. OST — when does E[Y_T] = E[Y_0]? (Summary)

```
Is (Y,F) a martingale?    NO → can't use OST directly
         ↓ YES
Is T a stopping time?     NO → redefine T with {T=n}∈Fn
         ↓ YES
Is P(T<∞)=1?              NO → OST fails (may need truncation)
         ↓ YES
Is ET < ∞ and increments  NO → Check conditions 12.5.1 (a)(b)(c) directly
bounded given past?
         ↓ YES
E(Y_T) = E(Y_0) ✓
```

---

## 9. LLN convergence rate (practical)

For n iid observations with mean μ and variance σ²:
- Error |x̄ − μ| ≤ 1.96σ/√n with 95% probability (CLT)
- For 1% error: n ≥ (196σ/μ)² (if μ≠0)
- If distribution heavy-tailed (σ²=∞): CLT fails → use median or trimmed mean

---

## 10. Martingale vs. Submartingale tells

| Sequence | Type | Tell |
|---------|------|------|
| Fair game capital | Martingale | E(gain\|past) = 0 |
| Unfair game (house edge) | Supermartingale | E(capital\|past) < current |
| Accumulated score (positive rewards) | Submartingale | E(next\|past) ≥ current |
| Sn² − n (sum of iid zero-mean) | Submartingale | variance grows |
| ψ(Markov chain) for harmonic ψ | Martingale | Pψ = ψ |
| η^{Zn} for branching process | Martingale | G(η)=η |
