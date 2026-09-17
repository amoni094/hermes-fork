# Chapter 3: More about Inference

## Core Idea
Bayesian inference is not just point estimates: the posterior over parameters, and the *evidence* P(data|model), automatically implement Occam’s razor. Comparing models by maximum likelihood overfits; comparing them by marginal likelihood prefers the model that predicted the data with least wasted prior mass.

## Frameworks Introduced
- **Parameter inference vs model comparison**
  - Level 1: infer parameters θ of a model H from data D: P(θ|D,H) ∝ P(D|θ,H) P(θ|H).
  - Level 2: infer which model: P(H|D) ∝ P(D|H) P(H), with evidence P(D|H) = ∫ P(D|θ,H) P(θ|H) dθ.
- **The bent-coin laboratory**: unknown bias f ∈ [0,1], N tosses, r heads. The entire Bayesian story in one conjugate example.
- **Occam factor**: a complex model spreads prior mass over a large parameter volume; only a fraction F of that volume fits the data, so evidence is penalized by ~F.

## Key Concepts
- **Likelihood**: P(D|θ,H), a function of θ once D is observed — not a distribution over D in the inverse problem.
- **Prior P(θ|H)**: must be a proper probability for model comparison (improper priors make evidences meaningless).
- **Posterior**: prior reweighted by likelihood and renormalized.
- **Predictive distribution**: P(next datum | D) = ∫ P(datum|θ) P(θ|D) dθ (not P(datum|θ_MAP)).
- **Laplace succession / Dirichlet-multinomial**: after r heads in N tosses with uniform prior on f, P(next is head | data) = (r+1)/(N+2).
- **Legal-evidence example**: Bayesian updating on guilt vs innocence given noisy testimony; base rates matter.

## Key Equations
- P(r | f, N) = C(N,r) f^r (1−f)^{N−r}
- Uniform prior P(f)=1 on [0,1]
- P(f | r,N) = [f^r (1−f)^{N−r}] / B(r+1, N−r+1)  -- Beta(r+1, N−r+1)
- P(D|H) = ∫_0^1 P(r|f,N) df = 1/(N+1)   for uniform prior (any r)
- P(heads next | r,N) = (r+1)/(N+2)
- Evidence ratio P(D|H1)/P(D|H2) = Occam factor × best-fit likelihood ratio

## Algorithms and Techniques
**Bent-coin posterior (Beta conjugate)**
1. Start with prior Beta(a,b); uniform is Beta(1,1).
2. Observe r heads, N−r tails.
3. Posterior is Beta(a+r, b+N−r).
4. Mean (a+r)/(a+b+N); MAP (a+r−1)/(a+b+N−2) for a,b>1.
5. Predict with the posterior mean, not the MAP, for 0-1 next-toss loss.

**Model comparison (fair vs bent)**
1. H0: f=1/2 exactly. Evidence = 2^{−N} (or binomial coefficient times that).
2. H1: f unknown, uniform prior. Evidence = 1/(N+1).
3. For data with r ≈ N/2, H0 wins; for extreme r, H1 wins. No extra “complexity penalty” is inserted by hand.

## Mental Models
- Use the **posterior width**, not just the mode: N=2 with 1 head is *not* the same knowledge as “f=1/2”.
- Think of evidence as the prior’s *predictive success* before seeing data, averaged: models that could have predicted many other datasets pay in evidence.
- Use **base rates** whenever hypotheses are rare (burglars, diseases, guilt).

## Worked Example
N=3 tosses, r=3 heads.

- Under H0 (fair): P(D|H0)=1/8=0.125.
- Under H1 (uniform f): P(D|H1)=∫ f^3 df = 1/4=0.25.
- Bayes factor 2:1 for “bent”. Posterior on f is Beta(4,1), density ∝ f^3, mean 4/5=0.8, MAP=1. The MAP says “the coin is two-headed”; the predictive P(next head)=(3+1)/(3+2)=0.8, which is the quantity you should bet with.

Legal evidence (MacKay): a fallible witness who is 99% accurate still does not yield P(guilty|accusation)≈0.99 if the base rate of guilt is 0.1%. Write P(G|E) = P(E|G)P(G)/P(E) with P(E)=P(E|G)P(G)+P(E|¬G)P(¬G).

## Anti-patterns
- **Reporting θ_MAP as “the answer”** when the posterior is broad or hits a boundary.
- **Using improper priors in model comparison** (evidence is then defined only up to an arbitrary factor).
- **Ignoring the sampling distribution of the evidence**: rare events can look like model failure.
- **Prosecutor’s fallacy**: quoting P(evidence | innocent) as if it were P(innocent | evidence).
- **Comparing peak likelihoods across models of different dimension**.

## Key Takeaways
1. Always write P(parameters | data, model) *and* P(data | model).
2. Predictive probabilities average over the posterior; they implement error bars for free.
3. Occam’s razor is not an extra term — it is the volume of unused prior mass.
4. Uniform Beta(1,1) + binomial → Laplace’s rule of succession (r+1)/(N+2).
5. Rare hypotheses stay rare unless the likelihood ratio is enormous.

## Connects To
- **Ch 2**: Bayes rule, entropy as uncertainty of the posterior.
- **Ch 22**: ML clustering as a cautionary non-Bayesian alternative.
- **Ch 28**: Occam factors via Laplace approximation, explicit model comparison.
- **Ch 36–37**: decision theory and sampling-theory critiques.
