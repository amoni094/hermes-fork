---
name: jaynes-probability
description: "Use when Bayesian updating, maxent, priors, or calibration."
related_skills:
  - coding-conventions
  - systematic-debugging
  - test-driven-development
  - shannon-1948
  - mackay-itila
---

# Probability Theory: The Logic of Science
**Author**: E. T. Jaynes | **Chapters**: 30 + appendices | **Source**: unfinished 1995 MS (Cambridge 2003)

Knowledge base from Jaynes *Probability Theory: The Logic of Science*. Use when reasoning about uncertainty in code, Bayesian updating, prior selection, maximum entropy, or making decisions under incomplete information.

Probability is extended logic: the unique consistent assignment of real numbers to degrees of belief. Not frequencies, not propensity. Load this skill when assigning, combining, or acting on uncertain quantities.

## How to Use

- **Without arguments** — apply the core rules below
- **Topic** — Cox, maxent, priors, calibration, decision vs inference, paradoxes
- **Chapter** — see Chapter Index

---

## Core Frameworks

### Probability as extended logic (Cox)

Jaynes (after R. T. Cox 1946) derives the product and sum rules from three desiderata, not from frequency axioms:

1. **Degrees of plausibility are real numbers** (must live in a machine / robot brain).
2. **Qualitative correspondence with common sense** (weak syllogisms of Pólya: if A ⇒ B and B is true, A becomes more plausible).
3. **Consistency**: (a) every valid chain of reasoning yields the same number; (b) use *all* relevant evidence (non-ideological); (c) equivalent states of knowledge → equivalent assignments.

These force, uniquely up to a monotonic reparametrization that we fix by convention 0 ≤ p ≤ 1:

```
product:  p(AB|C) = p(A|C) p(B|AC) = p(B|C) p(A|BC)
sum:      p(A|B) + p(¬A|B) = 1
extended: p(A+B|C) = p(A|C) + p(B|C) − p(AB|C)
Bayes:    p(H|DX) = p(H|X) p(D|HX) / p(D|X)
```

**Use when:** a function returns a "confidence", "score", or "probability". If it does not obey non-negativity and the sum rule over an exhaustive partition, it is **not a probability**. Do not multiply it, do not threshold it as p, do not feed it to expected-utility arithmetic.

**Why uniqueness matters:** any other combination rule (heuristic weighted sums, ad-hoc AND of scores) eventually contradicts itself on some Boolean identity. Cox is the uniqueness theorem for that claim.

### Probability as degree of belief

`p(A|X)` is the robot's degree of belief in A given information X. There is no "true probability of A" independent of X. Two agents with different X *should* assign different p. Frequency is a special case: a limiting property of some physical experiments, recovered when the information is an exchangeable sequence (Ch 9). Do not require a frequency interpretation before using p.

Notation: always condition on background information. Write `p(H|DX)`, never a naked `p(H)`.

### Bayesian updating

Start with a prior `p(H|X)` over hypotheses (including "the bug is here", "this model is true"). Each observation D updates:

```
posterior ∝ prior × likelihood
```

- The posterior after datum n is the prior for datum n+1. There is no other consistent way to fold evidence in.
- Skipping to a degenerate posterior (certainty) without likelihood evidence is assigning `p=1` by fiat — forbidden by desideratum IIIb (use all evidence; invent none).
- Multiple hypotheses: never test H vs ¬H as if ¬H were a single alternative. Enumerate the actual competitors (Ch 4). Binary tests do not extend.
- Likelihood principle (Ch 6, 8): given the model, only the observed data's likelihood matters — not the sampling plan, optional stopping, or unobserved outcomes.

**Debugging is this procedure.** Prior over locations (recent diffs, stack traces) × each new observation (test, log line) → posterior = next hypothesis to test. One hypothesis at a time is sequential Bayes, not indecision.

### Maximum entropy principle (Ch 11)

When information is constraints (means, bounds, known moments) rather than a sampling model, assign the distribution that **maximizes Shannon entropy** `H = −∑ p_i log p_i` subject to those constraints. That is the unique assignment that:

- agrees with everything you know,
- is maximally noncommittal about everything you don't,
- never puts p=0 on a possibility the data have not ruled out.

Standard maxent distributions (use these; do not invent narrower ones):

| Known constraint | Maxent distribution |
|---|---|
| Nothing / finite exhaustive set | Uniform (principle of indifference) |
| Mean (real line, or unbounded support) | Exponential |
| Mean and variance | Gaussian |
| Mean of log (positive scale) | Inverse-gamma / Jeffreys-related |
| Discrete mean of a count | Geometric / exponential family |

**Over-specification:** choosing a tighter family (mixture of 5 Gaussians, Beta(100,3), …) without a constraint that forces it is claiming information you do not have. Maxent forbids it.

Maxent assigns the *prior / sampling distribution*. Bayes then updates it when data arrive. They are complementary, not rivals (preface / Ch 11).

### Prior selection (Ch 6, 12)

1. **Indifference:** if X does not prefer any atom of a finite exhaustive partition, p = 1/n.
2. **Jeffreys prior for a scale parameter s > 0:** `p(s) ∝ 1/s` (uniform in log s). Required by consistency under reparametrization s → s^m, and uniquely uninformative about location given scale (transformation groups, Ch 12; reinforced by marginalization theory).
3. **Transformation groups:** the prior is the (improper) Haar measure of the group of transformations that leave the problem looking the same. Equivalent states of knowledge → equivalent assignments (desideratum IIIc).
4. **Proper limits:** unnormalizable priors are limits of proper sequences. If the posterior will not settle, the data are too weak — get more evidence; do not pick a convenient proper prior to force an answer.
5. A prior is not a subjective whim. It is a transcription of X. If you cannot state X, you cannot justify the prior.

### Calibration — the honest weatherman (Ch 13)

Inference yields p. Announcing q ≠ p is a *decision*, driven by a loss function. If pay is logarithmic in the announced probability of the event that occurs, expected pay is maximized uniquely at q = p. Honesty is then optimal; acquiring more information (lowering entropy of p) is also optimal.

**Operational rule:** a predicted probability p is calibrated iff events you tag with p occur with empirical frequency ≈ p. Uncalibrated outputs are not probabilities in Jaynes's sense even if they sit in [0,1].

### Inference vs decision

Probability theory stops at the posterior. Turning a posterior into an action requires a loss/utility function (Wald / Bernoulli). Do not smuggle the decision into the inference (e.g. "reject H0") and then pretend the number was a probability. Conversely, do not refuse to assign p because you have not yet chosen a loss.

Point estimates: posterior mean iff squared-error loss; median iff absolute-error; MAP is a mode, not an expected-loss minimizer unless the loss is a vanishing neighborhood of the mode.

### Model comparison (Ch 24)

Bayes automatically penalizes unused flexibility (Occam factor): a model that spreads prior mass over a large parameter volume pays in the marginal likelihood. Prefer the model with higher `p(D|M X)`, not the one with a prettier in-sample fit.

---

## Anti-patterns

- **Ad-hoc scoring:** magic weights on features, then treat the sum as a probability. Uncalibrated; Cox-inconsistent. Either derive the score from a probabilistic model or label it `uncalibrated_score`.
- **Degenerate priors:** "I'm sure it's X" with no likelihood. Ideology (violates IIIb).
- **Sampling-theory theater:** p-values, unbiasedness, confidence intervals that do not contain the parameter at the advertised rate for *this* data (Ch 16–17). Pre-data vs post-data are different problems.
- **Causation ≠ implication:** A ⇒ B is logical, not causal. Clouds do not cause rain in the syllogism; rain implies clouds.
- **Ignoring nuisance parameters** or plugging in a point estimate for them (Ch 8). Marginalize.
- **Infinite-set paradoxes** (Borel–Kolmogorov, nonconglomerability, Ch 15): they are artifacts of taking limits before stating the finite problem. Do the finite problem; pass to the limit last (finite-sets policy).
- **Sample re-use / peeking** that violates the likelihood principle while claiming Bayesian status.

---

## Chapter Index

**Part A — Principles**
| # | Title | Use for |
|---|-------|--------|
| 1 | Plausible reasoning | Weak syllogisms, desiderata, the robot |
| 2 | Quantitative rules (Cox) | Product/sum rules, uniqueness |
| 3 | Elementary sampling | Urns, exchangeability, models vs reality |
| 4 | Hypothesis testing | Priors, multiple H, pdfs |
| 5 | Queer uses | Convergence of opinion, ESP, Neptune |
| 6 | Parameter estimation | Uniform / Jeffreys priors, likelihood principle |
| 7 | Central Gaussian | Why Gaussians: maxent + convolution |
| 8 | Sufficiency, ancillarity | Nuisance parameters, meta-analysis |
| 9 | Probability and frequency | When frequencies exist |
| 10 | Physics of "random" experiments | Bias, coins, quantum aside |
| 11 | Entropy principle | Maxent assignment of discrete priors |
| 12 | Ignorance priors | Transformation groups |
| 13 | Decision theory history | Inference vs action, honest weatherman |
| 14 | Decision theory applications | Loss, widgets |
| 15 | Paradoxes | Finite-sets policy |
| 16–17 | Orthodox statistics | Pathologies of sampling theory |
| 18 | A_p-distribution, rule of succession | Laplace succession |

**Part B — Applications** — 19 measurements, 20 regression, 21 Cauchy/t, 22 time series, 23 spectrum, 24 model comparison, 25 image reconstruction, 26 marginalization, 27 communication theory, 28 antennas/filters, 29 statistical mechanics, 30 maxent matrix / density-matrix form.

---

## Topic Index

- **Bayes' theorem** → Ch 4, 6
- **Calibration / honest weatherman** → Ch 13
- **Cox theorems** → Ch 2
- **Degree of belief vs frequency** → Ch 1, 9, 10
- **Gaussian / CLT as maxent** → Ch 7, 11
- **Jeffreys prior** → Ch 6, 12
- **Likelihood principle** → Ch 6, 8
- **Marginalization** → Ch 8, 15, 26
- **Maximum entropy** → Ch 11, 30
- **Model comparison / Occam** → Ch 24
- **Paradoxes, finite sets** → Ch 15
- **Prior selection / transformation groups** → Ch 6, 11, 12
- **Rule of succession** → Ch 18
- **Sufficiency** → Ch 8
