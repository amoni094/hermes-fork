# Chapter 35: Random Inference Topics

## Core Idea
A miscellany that trains Bayesian taste: what “knowing nothing” means (Benford), record-breaking under ignorance, the Luria–Delbrück heavy-tailed mutation problem, and inferring causation. Ignorance is an invariance, not a uniform distribution on the naive alphabet.

## Key Concepts
- **Benford’s law**: P(first digit = d) = log_{10}(1 + 1/d). Follows from scale invariance: if units are arbitrary, P(ln x) is locally flat, so first-digit mass is the length of log-scale intervals.
- **Ignorance priors**: invariance to units ⇒ Jeffreys / log prior on a positive scale variable, *not* uniform on the mantissa’s first digit.
- **Record breaking**: if P(x) is unknown and attempts arrive at a steady rate, waiting times between records have a simple pattern (each new record is equally likely to fall in any attempt, in a suitable exchangeable sense); you can say something without knowing P(x).
- **Luria–Delbrück distribution**: mutants in an exponentially growing colony. Early mutations explode into huge clones ⇒ heavy-tailed n. Mean is a terrible estimator of mutation rate a.
- **Causation vs correlation**: MacKay’s short warning that interventional / causal questions are not answered by P(y|x) from observational data alone.

## Frameworks and Methods
- **Invariance arguments**: write the symmetry (change of units, rotation of a tumbling pin) and let it constrain P. This is how uninformative priors should be built.
- **Heavy tails and Bayes**: for Luria–Delbrück, write the generative process (mutations as Poisson in each generation, then deterministic growth of clones) and infer a from the *whole* likelihood, not from the sample mean.
- **Why sampling-theory hacks fail here**: Luria and Delbrück, lacking Bayes, produced two ad hoc estimators; the mean-based one has huge variance, yet confidence intervals are still built around it.

## Key Equations
- P(first digit d) = log_{10}(1 + 1/d)   (Benford)
- p_1 ≈ log_{10}(2) ≈ 0.301;  2^{10}≈10^3 gives the 3/10 mnemonic
- Scale invariance: P(x) dx invariant under x → c x  ⇒  P(x) ∝ 1/x  (on positives)
- Luria–Delbrück sketch: N = 2^g cells; mutation rate a per cell per generation; n = number of resistant cells is a compound of rare early events
- E[n] involves a N log N-type growth; Var(n) ≫ (E[n])²  (jackpot events)
- Record model: under iid x_t from unknown P, P(t is a record | history) = 1/t

## Algorithms and Techniques
**First-digit / units argument**
1. Refuse a uniform prior on x or on digits.
2. Demand invariance to x → c x.
3. Use log-uniform measure; digit probabilities become log-interval lengths.

**Mutation-rate inference (Bayes, not mean)**
1. Model generation-by-generation mutations ~ Poisson(a × population).
2. Each mutant founds a clone of size 2^{g−t}.
3. Likelihood of observed n (or a histogram of n across cultures) as function of a.
4. Posterior on a; *do not* use E[n]/something as if n were Poisson.

## Anti-patterns
- **Uniform on digits or on x** as “I know nothing”.
- **Estimating a from the mean number of mutants** — infinite or huge variance because of jackpots.
- **p-values / two estimators “because the distribution is ugly”** instead of writing P(data | a).
- **Calling P(y|x) a causal effect**.

## Key Takeaways
1. Ignorance is symmetry: units, not uniformity.
2. Benford is what a scale-free prior predicts about leading digits.
3. Heavy tails make means and classical SEs dishonest; use the actual likelihood.
4. Record processes give predictions even when P(x) is unknown.
5. Causal claims need more than a posterior predictive of observational data.

## Connects To
- **Ch 3**: legal evidence, bent coin — same “write P(data|hypothesis)”.
- **Ch 23**: priors on positive reals (Gamma, Jeffreys).
- **Ch 28**: model comparison rather than hacks.
- **Ch 37**: sampling theory vs Bayes on ugly likelihoods.
