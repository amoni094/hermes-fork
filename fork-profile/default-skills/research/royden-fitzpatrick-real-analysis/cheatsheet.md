# Cheatsheet: Real Analysis (Royden-Fitzpatrick)

## Convergence Theorem Decision Tree

```
Have: fₙ → f (a.e. or pointwise)
│
├─ Is there g integrable with |fₙ| ≤ g a.e. for ALL n?
│   └─ YES → Dominated Convergence: ∫fₙ → ∫f ✓
│
├─ Is m(E) < ∞ and {fₙ} uniformly integrable?
│   └─ YES → Vitali Convergence: ∫fₙ → ∫f ✓
│
├─ Are fₙ ≥ 0 and monotone increasing (fₙ ↑ f)?
│   └─ YES → Monotone Convergence: ∫fₙ → ∫f ✓
│
├─ Are fₙ ≥ 0 (no dominator, no monotonicity)?
│   └─ Fatou's Lemma: ∫lim inf fₙ ≤ lim inf ∫fₙ (only lower bound!)
│
└─ None of the above → No theorem applies directly; check tightness
```

## Lp Norm Quick Reference

| p | Space | Norm formula | Dual | Reflexive? |
|---|-------|-------------|------|-----------|
| 1 | L1 | ∫\|f\| dμ | L∞ | NO |
| (1,∞) | Lp | (∫\|f\|^p)^{1/p} | Lq (1/p+1/q=1) | YES |
| 2 | L2 | (∫f²)^{1/2} | L2 | YES (Hilbert) |
| ∞ | L∞ | ess sup\|f\| | ⊋L1 | NO |

**On finite-measure sets**: L∞ ⊆ Lq ⊆ Lp ⊆ L1 for q > p ≥ 1.

## Key Inequalities (in order of proof dependency)

| Inequality | Statement | Derived from |
|-----------|-----------|-------------|
| Young's | ab ≤ a^p/p + b^q/q | Concavity of log |
| Hölder's | ∫\|fg\| ≤ ‖f‖_p ‖g‖_q | Young's applied pointwise |
| Cauchy-Schwarz | \|⟨f,g⟩\| ≤ ‖f‖₂ ‖g‖₂ | Hölder with p=q=2 |
| Minkowski's | ‖f+g‖_p ≤ ‖f‖_p + ‖g‖_p | Hölder applied twice |
| Jensen's | f(∫φ dμ) ≤ ∫f∘φ dμ | Convexity of f |
| Chebyshev's | m({f>t}) ≤ (1/t)∫f | Markov inequality |

## Absolute Continuity vs Bounded Variation

| Property | Definition | Implies | Example |
|----------|-----------|---------|---------|
| AC | ε-δ on intervals | BV, FTC holds, f'∈L1 | ∫ₐˣ g(t)dt |
| BV | TV < ∞ | Diff a.e. | Cantor-Lebesgue fn |
| BV not AC | TV<∞, f'=0 a.e. | FTC fails | Cantor-Lebesgue fn |

**Rule**: f is indefinite integral of f' iff f is AC. If f is BV but not AC, there's a singular component.

## Measure Comparison Quick Reference

| Relation | Meaning | Consequence |
|----------|---------|-------------|
| ν ≪ μ | μ(E)=0 ⟹ ν(E)=0 | ∃ RN derivative dν/dμ |
| ν ⊥ μ | ∃E: μ(E)=0, ν(Eᶜ)=0 | No common mass |
| ν = νₐc + νₛ | Lebesgue decomp | νₐc ≪ μ, νₛ ⊥ μ; unique |

**When to use RN**: Changing base measure in an expectation: E_ν[h] = E_μ[h·(dν/dμ)].

## Compactness Decision Rules

| Space / Setting | Compact? | Method |
|----------------|---------|--------|
| Closed bounded set in ℝⁿ | YES | Heine-Borel |
| Closed unit ball in Lp, 1<p<∞ | NO (norm topology) | Unit ball not compact in ∞-dim |
| Closed unit ball in Lp, 1<p<∞ | YES (weak topology) | Kakutani (reflexive) |
| Closed unit ball in L1 | NO (weak topology unless UI) | L1 not reflexive |
| Closed unit ball in X* (any Banach X) | YES (weak-* topology) | Alaoglu |
| Subset of C(X), X compact | YES iff bounded+equicontinuous | Arzelà-Ascoli |

**Rule**: In infinite dimensions, always specify the topology when claiming compactness.

## Tells and Smells

| Symptom | Likely Issue | Fix |
|---------|-------------|-----|
| ∫fₙ ↛ ∫f despite fₙ→f | Missing dominator or mass escapes | Check tails: UI? Tight? |
| DCT fails because no dominator | Try Vitali instead | Verify UI condition |
| Sequence bounded but no norm-convergent subseq | Infinite dimension | Use weak topology |
| Iteration not converging | Contraction constant c ≥ 1 | Find reformulation with c<1 |
| Dual pairing ⟨f,g⟩ not well-defined | f∈Lp, g∉Lq | Ensure conjugate exponent |
| ν not ≪ μ | Cannot apply RN directly | Apply Lebesgue decomp first |
| Uniform integrability fails | Tails don't vanish uniformly | p>1 bound needed; check Lp norm |

## Hermes Application Quick-Map

| Hermes Concept | Royden Framework | Chapter |
|---------------|-----------------|---------|
| Skill routing distribution | Probability measure on skill set | Ch02, Ch17 |
| Routing weight concentration | ‖w‖_p for p=1,2,∞ | Ch07 |
| Score convergence over steps | DCT / Vitali for agent loops | Ch04 |
| Skill routing near-uniform convergence | Egorov's theorem | Ch03 |
| Bayesian weight update | Radon-Nikodym derivative | Ch18 |
| Memory consolidation convergence | Vitali + UI condition | Ch05, Ch19 |
| Working memory state space | Banach/Hilbert space (L2) | Ch07, Ch16 |
| Memory compression projection | Orthogonal projection in L2 | Ch16 |
| Iterative agent loop convergence | Banach contraction principle | Ch10 |
| Bounded scoring over all contexts | Uniform Boundedness Principle | Ch13 |
