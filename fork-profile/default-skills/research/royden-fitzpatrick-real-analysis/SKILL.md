---
name: royden-fitzpatrick-real-analysis
description: "Knowledge base from Real Analysis by Royden and Fitzpatrick. Use when applying measure theory, Lebesgue integration, Lp spaces, convergence theorems, metric spaces, Banach spaces to agent memory scoring, context compression quality bounds, and probabilistic reasoning in Hermes."
related_skills:
  - kreyszig-functional-analysis
  - jaynes-probability
  - cover-thomas-eit
---

<!-- argument-hint: [theorem name, chapter number, or topic: measure, Lp, Banach, convergence, Radon-Nikodym, Egorov, Vitali] -->

# Real Analysis (Fourth Edition)
**Authors**: H. L. Royden, P. M. Fitzpatrick | **Pages**: 516 | **Chapters**: 22 | **Parts**: 3

## How to Use This Skill

- **Without arguments** — load core measure-theoretic frameworks and Hermes application patterns
- **With theorem name** — e.g. `Vitali`, `Radon-Nikodym`, `Egorov` → load chapter with full theorem statement
- **With chapter** — `ch04`, `ch07`, `ch18` → load that chapter summary
- **Browse** — ask "what chapters?" to see full index
- **Hermes applications** — ask "how does DCT apply to agent loops?" for Hermes-specific guidance

Kreyszig covers Banach/Hilbert space operators (functional analysis abstract level). This skill covers the **measure-theoretic foundations**: σ-algebras, Lebesgue measure construction, Lp space completeness proofs, convergence theorems, and Radon-Nikodym. They are complementary.

---

## Core Frameworks & Mental Models

### 1. Measure-Theoretic Probability Model (Hermes: Skill Usage Distributions)

A **measure space** (X, M, μ) consists of a set X, a σ-algebra M closed under complement and countable union, and a measure μ: M → [0,∞] with μ(∅)=0 and countable additivity. Skill routing weights form a discrete probability measure on the finite set of skills — modeled as μ on (Ω, 2^Ω). **Lp norms** then bound how concentrated or diffuse a routing distribution is:

- **‖f‖_p = (∫|f|^p dμ)^{1/p}** for 1 ≤ p < ∞; ‖f‖_∞ = ess sup|f|
- Use ‖routing_weights‖_1 = 1 (normalization), ‖routing_weights‖_2 as concentration index, ‖routing_weights‖_∞ = max routing mass on any single skill
- **Young's Inequality**: ab ≤ a^p/p + b^q/q for 1/p + 1/q = 1 → bounds cross-terms in inner products
- **Hölder's Inequality**: ∫|fg| dμ ≤ ‖f‖_p · ‖g‖_q → bounds correlation between two routing distributions
- **Minkowski's Inequality**: ‖f+g‖_p ≤ ‖f‖_p + ‖g‖_p → routing distribution perturbation is bounded

### 2. Lebesgue Integration: Three Construction Stages

**Stage 1 — Simple functions**: ψ = Σ aᵢ · 1_{Eᵢ}, integral = Σ aᵢ μ(Eᵢ). Models discrete scoring.

**Stage 2 — Nonneg measurable**: ∫f dμ = sup{∫ψ dμ : 0 ≤ ψ ≤ f, ψ simple}. Monotone approximation.

**Stage 3 — General**: ∫f = ∫f⁺ - ∫f⁻ when at least one is finite. Linearity + monotonicity.

**Key property**: Linearity of integration mirrors linearity of expectation. If memory scores are integrable, their weighted averages under measure-change are computable via change of measure.

### 3. The Four Convergence Theorems (Hermes: Iterative Loop Limits)

| Theorem | Hypothesis | Conclusion | Hermes Application |
|---------|-----------|------------|-------------------|
| **Monotone Convergence (MCT)** | fₙ ↑ f a.e., fₙ ≥ 0 | ∫fₙ → ∫f | Monotone improvement of quality scores converges |
| **Fatou's Lemma** | fₙ ≥ 0 | ∫lim inf fₙ ≤ lim inf ∫fₙ | Lower bound on limiting loop quality; guards against overfitting |
| **Dominated Convergence (DCT)** | fₙ → f a.e., |fₙ| ≤ g, g integrable | ∫fₙ → ∫f | If per-step scoring is bounded by integrable dominator, limit score = score of limit policy |
| **Vitali Convergence** | {fₙ} uniformly integrable + tight, fₙ → f a.e. | ∫fₙ → ∫f | Convergence of memory consolidation batches without dominator; need uniform integrability |

**DCT operational form**: To justify lim_{n→∞} E[score_n] = E[lim score_n], confirm: (1) score_n → score_∞ pointwise, (2) |score_n| ≤ g where E[g] < ∞.

**Uniform Integrability** (Vitali prerequisite): {fₙ} uniformly integrable iff ∀ε>0 ∃δ>0 s.t. μ(A)<δ ⟹ ∫_A |fₙ|dμ < ε for all n. Equivalently: sup_n ∫_{|fₙ|>M} |fₙ|dμ → 0 as M→∞. In Hermes: routing weights {wₙ} are uniformly integrable if no single skill ever accumulates unbounded mass.

### 4. Egorov's Theorem: Almost-Uniform Convergence

**Theorem**: Let μ(E) < ∞. If fₙ → f a.e. on E, then ∀ε>0 ∃ measurable F ⊂ E with μ(E\F) < ε such that fₙ → f **uniformly** on F.

**Hermes application**: Skill routing convergence that holds pointwise a.e. also holds uniformly on a large fraction (1-ε) of the skill domain. Identify F as the "stable core" of routing behavior; accept ε-mass of skills as slow-converging outliers. Requires finite measure — must restrict to compact subset of skill space.

### 5. Radon-Nikodym: Change of Measure for Skill Weighting

**Theorem**: If ν ≪ μ (ν absolutely continuous w.r.t. μ — every μ-null set is ν-null), then ∃ unique measurable f ≥ 0 (the **Radon-Nikodym derivative** dν/dμ) such that ν(E) = ∫_E f dμ for all E ∈ M.

**Chain rule**: If ν ≪ μ ≪ λ, then dν/dλ = (dν/dμ)·(dμ/dλ) a.e.[λ].

**Hermes application**: Current skill weights (ν) and reference/prior weights (μ) — when ν ≪ μ, the importance ratio dν/dμ = w(skill) is the reweighting factor. Bayesian skill weight update is a Radon-Nikodym derivative of posterior w.r.t. prior. If any skill has zero prior weight (μ-null), posterior must also be zero (no evidence can make ν(E) > 0 if μ(E) = 0).

### 6. Lp Spaces: Completeness and Dual Structure

**Riesz-Fischer Theorem**: Lp(E) is complete for 1 ≤ p ≤ ∞. Every Cauchy sequence in Lp converges to an Lp element. Equivalently: if Σ‖fₙ‖_p < ∞, then Σfₙ converges in Lp and a.e.

**Dual space**: For 1 < p < ∞ with conjugate q (1/p+1/q=1), [Lp]* ≅ Lq via T(f) = ∫f·g dμ, ‖T‖ = ‖g‖_q. The dual of L1 is L∞; the dual of L∞ is strictly larger than L1.

**Weak convergence**: fₙ ⇀ f in Lp iff ∫fₙ·g → ∫f·g for all g ∈ Lq. Weak ≠ norm convergence. Bounded Lp sequences have weakly convergent subsequences (for 1 < p < ∞).

**Hermes application**: Working memory state vector lives in L2 (square-integrable). Memory consolidation is a projection onto a closed subspace. Compression error ‖f - Pf‖_2 is bounded by the Riesz-Fischer completeness guarantee.

### 7. Banach and Metric Space Tools

- **Complete metric space**: Every Cauchy sequence converges. Baire Category: countable intersection of dense open sets is dense — a complete metric space is not meagre. Apply to show skill routing cannot be "mostly bad" across all strategy classes simultaneously.
- **Banach Contraction**: Fixed-point theorem. T: X → X with ‖Tx - Ty‖ ≤ c‖x-y‖ (c < 1) has unique fixed point. Iterative agent loops converge if each step is a contraction.
- **Open Mapping Theorem**: Surjective bounded linear operator between Banach spaces is open. Inverse is bounded — bounded input change → bounded output change.
- **Uniform Boundedness (Banach-Steinhaus)**: If supₙ |Tₙ(x)| < ∞ for each x, then supₙ ‖Tₙ‖ < ∞. Apply: if individual skill scores are bounded at each context, the operator norm (worst-case score) is uniformly bounded.

---

## Chapter Index

| # | Title | Key Theorems |
|---|-------|--------------|
| [ch01](chapters/ch01-real-numbers.md) | Real Numbers: Sets, Sequences, Functions | Completeness axiom, Borel sets, lim sup/inf |
| [ch02](chapters/ch02-lebesgue-measure.md) | Lebesgue Measure | Outer measure, σ-algebra, Borel-Cantelli, Cantor set |
| [ch03](chapters/ch03-measurable-functions.md) | Lebesgue Measurable Functions | Egorov's theorem, Lusin's theorem, simple approx |
| [ch04](chapters/ch04-lebesgue-integration.md) | Lebesgue Integration | MCT, Fatou, DCT, Vitali convergence |
| [ch05](chapters/ch05-further-topics.md) | Integration: Further Topics | Uniform integrability, convergence in measure |
| [ch06](chapters/ch06-differentiation.md) | Differentiation and Integration | BV functions, absolute continuity, FTC |
| [ch07](chapters/ch07-lp-spaces.md) | Lp Spaces: Completeness | Hölder, Minkowski, Riesz-Fischer, separability |
| [ch08](chapters/ch08-lp-duality.md) | Lp Spaces: Duality and Weak Convergence | Riesz representation, weak compactness, minimization |
| [ch09](chapters/ch09-metric-spaces.md) | Metric Spaces: General Properties | Open/closed sets, completeness, compactness |
| [ch10](chapters/ch10-metric-theorems.md) | Metric Spaces: Three Theorems | Arzelà-Ascoli, Baire Category, Banach contraction |
| [ch11](chapters/ch11-topological-spaces.md) | Topological Spaces: General | Hausdorff, countability, compactness |
| [ch12](chapters/ch12-topological-theorems.md) | Topological Spaces: Three Theorems | Urysohn, Tychonoff, Stone-Weierstrass |
| [ch13](chapters/ch13-banach-operators.md) | Continuous Linear Operators (Banach) | Open mapping, closed graph, uniform boundedness |
| [ch14](chapters/ch14-duality-normed.md) | Duality for Normed Spaces | Hahn-Banach, reflexivity, Krein-Milman |
| [ch15](chapters/ch15-weak-topology.md) | Compactness Regained: Weak Topology | Alaoglu, Kakutani, Eberlein-Smulian |
| [ch16](chapters/ch16-hilbert-spaces.md) | Operators on Hilbert Spaces | Orthogonality, Hilbert-Schmidt, Riesz-Schauder |
| [ch17](chapters/ch17-general-measure.md) | General Measure Spaces | Signed measures, Hahn-Jordan decomposition, Carathéodory |
| [ch18](chapters/ch18-general-integration.md) | Integration over General Measure Spaces | Radon-Nikodym, Lebesgue decomposition, Vitali-Hahn-Saks |
| [ch19](chapters/ch19-general-lp.md) | General Lp Spaces | Completeness, dual representation, Dunford-Pettis |
| [ch20](chapters/ch20-particular-measures.md) | Construction of Particular Measures | Fubini-Tonelli, Lebesgue on Rⁿ, Hausdorff measure |
| [ch21](chapters/ch21-measure-topology.md) | Measure and Topology | Radon measures, Riesz-Markov theorem |
| [ch22](chapters/ch22-invariant-measures.md) | Invariant Measures | Haar measure, ergodicity, Bogoliubov-Krylov |

## Topic Index

- **Absolute continuity** → ch06, ch18
- **Arzelà-Ascoli** → ch10
- **Baire Category** → ch10
- **Banach contraction** → ch10
- **Banach spaces** → ch07, ch13, ch14, ch15
- **Borel sets / σ-algebra** → ch01, ch02, ch17
- **Borel-Cantelli Lemma** → ch02
- **Dominated Convergence (DCT)** → ch04
- **Dual spaces** → ch08, ch14, ch19
- **Dunford-Pettis theorem** → ch19
- **Egorov's theorem** → ch03
- **Ergodicity** → ch22
- **Fatou's Lemma** → ch04
- **Fubini-Tonelli** → ch20
- **Haar measure** → ch22
- **Hahn-Banach** → ch14
- **Hilbert spaces** → ch16
- **Hölder's inequality** → ch07
- **Lp spaces** → ch07, ch08, ch19
- **Lebesgue measure** → ch02
- **Lusin's theorem** → ch03
- **Monotone Convergence (MCT)** → ch04
- **Outer measure** → ch02, ch17
- **Radon-Nikodym** → ch18
- **Riesz-Fischer** → ch07
- **Riesz representation (Lp dual)** → ch08, ch19
- **Signed measures** → ch17
- **Uniform integrability** → ch04, ch05
- **Vitali Convergence** → ch04, ch05
- **Weak convergence** → ch08, ch15, ch19

## Supporting Files

- [glossary.md](glossary.md) — key terms with definitions and chapter references
- [patterns.md](patterns.md) — theorems as reusable proof patterns
- [cheatsheet.md](cheatsheet.md) — decision rules and quick-reference tables

---

## Scope & Limits

Covers Royden-Fitzpatrick 4th ed. content only (Lebesgue integration, abstract measure theory, Banach/Hilbert spaces). Overlaps with kreyszig-functional-analysis (operator theory); this skill is authoritative for **measure-theoretic foundations**. For probability-specific applications, combine with jaynes-probability. For information-theoretic bounds, combine with cover-thomas-eit or gallager-itrc.
