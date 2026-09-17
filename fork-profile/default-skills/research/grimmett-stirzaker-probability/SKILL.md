---
name: grimmett-stirzaker-probability
description: "Knowledge base from Probability and Random Processes by Grimmett and Stirzaker. Use when applying probability spaces, random variables, conditional expectation, martingales, Markov chains, Brownian motion, convergence theorems, characteristic functions, and stochastic processes to agent memory models, skill routing distributions, and sequential decision-making in Hermes."
related_skills:
  - jaynes-probability
  - wald-sequential-analysis
---

<!-- argument-hint: [topic, chapter number, or concept] -->

# Probability and Random Processes
**Author**: Geoffrey R. Grimmett & David R. Stirzaker | **Pages**: 682 | **Chapters**: 13 | **Edition**: 4th (2020)

## How to Use This Skill

- **Without arguments** — load core frameworks (martingales, Markov chains, convergence)
- **With a topic** — ask about `optional stopping`, `mixing times`, `characteristic functions`; I find the right chapter
- **With chapter** — ask for `ch06` (Markov chains) or `ch12` (Martingales)
- **Hermes applications** — ask "how does G&S apply to skill routing?" → I check chapters + patterns.md

Complements **jaynes-probability** (Bayesian): G&S is the frequentist/stochastic-process side — Markov chains, martingales, renewal theory, Brownian motion.

---

## Core Frameworks & Mental Models

### 1. Probability Space — the triple (Ω, F, P)
Every probabilistic statement requires specifying:
- **Ω** (sample space): all possible outcomes
- **F** (σ-field/σ-algebra): the events we can assign probability to — closed under countable unions and complements
- **P** (probability measure): countably additive, P(∅)=0, P(Ω)=1

**Use when**: formalizing any random system. *If you cannot specify these three, your probabilistic claim is informal.*

### 2. Martingale — requires a FILTRATION, not just a sequence
**Definition (Def. 12.1.8)**: A pair (Y, F) is a martingale if:
- Y is adapted to filtration F (Yn is Fn-measurable for all n)
- E|Yn| < ∞
- E(Yn+1 | Fn) = Yn  a.s.

**Critical**: The filtration F = {F0, F1, …} represents information available at each time. A sequence of values is NOT a martingale unless it is adapted to a specified filtration and satisfies the conditional expectation condition.

- **Submartingale**: E(Yn+1 | Fn) ≥ Yn — "on average goes up"
- **Supermartingale**: E(Yn+1 | Fn) ≤ Yn — "on average goes down"

**Use when**: modeling a fair process (zero drift), gambler's capital in a fair game, likelihood ratios under the true measure.

### 3. Optional Stopping Theorem (OST) — when does E[Y_T] = E[Y_0]?
**Theorem (12.5.1)**: Let (Y, F) be a martingale and T a stopping time. Then E(YT) = E(Y0) if:
- (a) P(T < ∞) = 1
- (b) E|YT| < ∞
- (c) E(Yn · I{T>n}) → 0 as n → ∞

**Alternative (Theorem 12.5.9)**: E(YT) = E(Y0) if P(T < ∞) = 1, ET < ∞, and |Yn+1 − Yn| has bounded conditional expectation given Fn.

**Stopping time T**: a random variable where {T=n} ∈ Fn for all n — "decision to stop uses only past information, not the future."

**Use when**: computing first-passage probabilities, gamblers' ruin, expected absorption times.

### 4. Markov Chain — the memoryless process
**Definition (6.1.1)**: X is a Markov chain if P(Xn = s | X0,...,Xn-1) = P(Xn = s | Xn-1).

**Key facts**:
- Transition matrix P is stochastic (rows sum to 1, entries ≥ 0)
- n-step transitions: P(n) = Pⁿ  (Chapman-Kolmogorov)
- Distribution evolution: μ(n) = μ(0) Pⁿ

**Classification of states**: transient (probability of return < 1) vs. recurrent (certain return). Positive recurrent: mean return time μi < ∞.

### 5. Stationary Distribution & Convergence (Limit Theorem 6.4.3)
An irreducible chain has a unique stationary distribution π iff all states are positive recurrent.
Then: πi = 1/μi (inverse mean return time).

For irreducible, positive recurrent, **aperiodic** chains: pij(n) → πj as n → ∞.

**Mixing time**: τmix(ε) = min{n : max_i ||P^n(i,·) − π||_TV ≤ ε}. Controls how quickly the chain "forgets" its start.

**Use when**: routing convergence, stationary behavior of any state machine.

### 6. Laws of Large Numbers
- **Weak LLN**: n⁻¹Sn →P μ (convergence in probability)
- **Strong LLN (7.4.3)**: If E(X₁²) < ∞ and E(X₁) = μ, then n⁻¹Sn → μ a.s. and in mean square. Necessary and sufficient for a.s. convergence: E|X₁| < ∞.

**Use when**: estimating long-run frequencies; Sn/n converges only if the mean exists.

### 7. Central Limit Theorem (5.10.4)
If X₁, X₂, … iid with mean μ and variance σ², then:
(Sn − nμ)/(σ√n) →D N(0,1)

**Practical**: For n observations, a 95% confidence interval for μ is x̄ ± 1.96σ/√n.

### 8. Characteristic Functions — the Fourier transform of distributions
**Definition (5.7.2)**: φ(t) = E(e^{itX}) — always exists (unlike MGF), uniquely determines the distribution.

**Properties**:
- φ(0) = 1, |φ(t)| ≤ 1
- Independent X, Y: φ_{X+Y}(t) = φ_X(t)·φ_Y(t)
- Moments: φ^(k)(0) = iᵏ E(Xᵏ) when moments exist
- Bochner's theorem: φ is a characteristic function iff it is positive-definite, uniformly continuous, and φ(0)=1

**Use when**: proving convergence in distribution (continuity theorem), analyzing convolutions, identifying distributions.

### 9. Doob's Upcrossing Inequality & Convergence Theorem
**Upcrossings Un[a,b]**: number of times a sequence crosses from below a to above b in n steps.

**Doob's upcrossing inequality**: (b-a)E[Un(a,b)] ≤ E[(Yn - a)⁺]

**Martingale convergence theorem (7.8.1)**: If (Y, F) is a submartingale with sup_n E(Yn⁺) < ∞, then Yn → Y∞ a.s.

**Use when**: proving a.s. convergence of accumulated evidence; anomaly detection via upcrossing count.

### 10. Renewal Theory — events that regenerate
**Renewal process**: interarrival times X₁, X₂, … iid with distribution F. N(t) = number of renewals by time t.

**Key renewal theorem (10.2.7)**: As t → ∞, m(t)/t → 1/μ (where μ = E(X₁)).

**Elementary renewal theorem**: E[N(t)]/t → 1/μ.

**Excess lifetime (10.3)**: E(t) = time until next renewal from t. As t → ∞, E(t) → distribution with density (1-F(x))/μ.

**Use when**: cache refresh scheduling, modeling any regenerative system (queue busy periods, skill reuse).

### 11. Brownian Motion / Wiener Process
**Definition (13.3.1)**: W = {W(t): t≥0} is a Gaussian process with:
- W(0) = 0
- Stationary independent increments: W(s+t) − W(s) ~ N(0, σ²t)
- Continuous sample paths (a.s.)
- Covariance: cov(W(s),W(t)) = σ² min(s,t)

Sample paths are continuous but nowhere differentiable (a.s.).

**Itô's formula (13.9)**: For smooth f, df(W(t)) = f'(W(t))dW(t) + ½f''(W(t))dt — the extra drift term ½f'' is the key difference from ordinary calculus.

---

## Chapter Index

| # | Title | Key Topics |
|---|-------|------------|
| [ch01](chapters/ch01-events-probability.md) | Events and their probabilities | σ-fields, probability axioms, conditional probability, Bayes |
| [ch02](chapters/ch02-random-variables.md) | Random variables and their distributions | r.v. definition, law of averages, random vectors, Monte Carlo |
| [ch03](chapters/ch03-discrete-random-variables.md) | Discrete random variables | PMFs, expectation, indicators, Bernoulli/Poisson/geometric, random walk |
| [ch04](chapters/ch04-continuous-random-variables.md) | Continuous random variables | PDFs, expectation, multivariate normal, coupling, Poisson approx |
| [ch05](chapters/ch05-generating-functions.md) | Generating functions and applications | PGFs, MGFs, characteristic functions, CLT, large deviations |
| [ch06](chapters/ch06-markov-chains.md) | Markov chains | Transition matrices, classification, stationary dist., MCMC, Poisson |
| [ch07](chapters/ch07-convergence.md) | Convergence of random variables | Modes of convergence, LLN, martingale convergence, uniform integrability |
| [ch08](chapters/ch08-random-processes.md) | Random processes | Stationarity, Wiener process, Lévy processes, existence theorems |
| [ch09](chapters/ch09-stationary-processes.md) | Stationary processes | Spectral theory, ergodic theorem, Gaussian processes |
| [ch10](chapters/ch10-renewals.md) | Renewals | Renewal equation, limit theorems, excess lifetime, applications |
| [ch11](chapters/ch11-queues.md) | Queues | M/M/1, M/G/1, G/G/1, heavy traffic, networks |
| [ch12](chapters/ch12-martingales.md) | Martingales | Filtrations, stopping times, OST, upcrossing inequality, Doob |
| [ch13](chapters/ch13-diffusion.md) | Diffusion processes | Brownian motion, Itô calculus, Feynman-Kac, option pricing |

## Topic Index

- **Brownian motion** → ch13
- **Central limit theorem** → ch05, ch07
- **Characteristic functions** → ch05
- **Chapman-Kolmogorov** → ch06
- **Conditional expectation** → ch03, ch04, ch07, ch12
- **Convergence (a.s., L², probability, distribution)** → ch07
- **Coupling** → ch04, ch06
- **Doob's inequality / upcrossings** → ch07, ch12
- **Ergodic theorem** → ch09
- **Filtration** → ch12
- **Gamblers' ruin** → ch03, ch12
- **Gaussian process** → ch09, ch13
- **Generating functions (PGF, MGF)** → ch05
- **Itô's formula** → ch13
- **Large deviations** → ch05
- **Law of large numbers** → ch07
- **Lévy processes** → ch08
- **Markov chains (discrete)** → ch06
- **Markov chains (continuous-time)** → ch06
- **Martingales** → ch07, ch12
- **MCMC** → ch06
- **Mixing time** → ch06
- **Optional stopping theorem** → ch12
- **Ornstein-Uhlenbeck process** → ch09, ch13
- **Poisson process** → ch06, ch10
- **Queues** → ch11
- **Random walk** → ch03, ch05, ch12
- **Renewal theory** → ch10
- **σ-field, σ-algebra** → ch01
- **Stationary distribution** → ch06
- **Stochastic calculus** → ch13
- **Stopping times** → ch12
- **Uniform integrability** → ch07
- **Wald's equation** → ch12
- **Wiener process** → ch08, ch09, ch13

## Supporting Files

- [chapters/](chapters/) — 13 chapter summaries
- [glossary.md](glossary.md) — key terms with definitions
- [patterns.md](patterns.md) — techniques, algorithms, and stochastic patterns
- [cheatsheet.md](cheatsheet.md) — decision guide for applying G&S to Hermes

---

## Scope & Limits

This skill covers G&S 4th edition (2020). Complements jaynes-probability (Bayesian focus). For measure-theoretic foundations beyond G&S, see Billingsley. The Hermes-specific spike proposals applying these results are in `/tmp/grimmett_spikes.json`.
