# Chapter 23: Useful Probability Distributions

## Core Idea
A small catalog of distributions — Gaussian, Gamma, Dirichlet, Student-t, entropic — is the vocabulary of conjugate Bayesian modelling. Matching a likelihood to a conjugate prior turns integrals into parameter updates. MacKay emphasizes the Dirichlet as the prior on probability vectors and the Gaussian as the default on reals.

## Frameworks Introduced
- **Exponential family + conjugate prior**: posterior stays in the same family; prior parameters = pseudo-counts.
- **Dirichlet–multinomial**: the bent-coin’s multivariate version. P(p|u) ∝ ∏ p_i^{u_i−1} on the simplex.
- **Gaussian**: location-scale default; conjugate prior on mean is Gaussian, on variance Inverse-Gamma / Wishart.
- **Gamma / Exponential / Poisson**: counts and positive rates.
- **Student-t**: Gaussian with unknown variance marginalized; heavy tails, robust.
- **Entropic prior**: P(p|α,m) ∝ exp(−α DKL(p||m)) on the simplex (maxent community).

## Key Concepts
- **Simplex**: p_i≥0, sum p_i=1. Dirichlet lives here.
- **Aggregation consistency**: Dirichlet on a fine alphabet, when bins are merged, remains Dirichlet on the coarse alphabet iff hyperparameters add (exercise in the chapter). This is why Dirichlet is the “right” prior on discrete P.
- **Hyperparameters u_i**: effective prior counts. u_i=1 is uniform on the simplex (not uniform on log-odds).
- **Improper priors**: e.g. 1/σ; usable for parameter inference, dangerous for evidence (Ch 3, 28).
- **Exchangeability**: Dirichlet–multinomial is the discrete de Finetti default.

## Key Equations
- Normal(y; μ, σ²) = (2πσ²)^{−1/2} exp(−(y−μ)²/2σ²)
- Dirichlet(p|u) = Γ(u_0)/∏Γ(u_i)  ∏ p_i^{u_i−1},  u_0=sum u_i
- E[p_i]=u_i/u_0,  posterior u' = u + counts
- Predictive (Laplace generalization): P(next=i|data) = (u_i+F_i)/(u_0+N)
- Gamma(x; s,c) ∝ x^{s−1} e^{−x/c}  (shape-scale; MacKay’s notation — check his s,c)
- Student-t: p(x|μ,σ,ν) ∝ (1 + (x−μ)²/(νσ²))^{−(ν+1)/2}
- Entropic: P(p|α,m) ∝ exp(−α DKL(p||m)) δ(sum p_i−1)

## Algorithms and Techniques
**Discrete Bayesian histogram**
1. Choose Dirichlet(u) (often u_i=1 or a small α m_i).
2. Count frequencies F_i.
3. Posterior Dirichlet(u+F).
4. Predict with posterior mean; error bars from Dirichlet covariance.

**Unknown Gaussian variance**
1. Use Inverse-Gamma / scaled Inv-χ² prior on σ², Gaussian on μ.
2. Marginal likelihood for μ is Student-t.
3. Robust to outliers relative to a known-σ Gaussian.

## Mental Models
- Always ask “what is conjugate here?” before launching MCMC.
- u_i=1 is uniform on p, not “uninformative” about rare events in a huge alphabet (most mass on sparse p? actually uniform Dirichlet is peaked near the centre for large I? Wait: Dirichlet(1..1) is uniform on the simplex. For large I, typical p is small per coordinate ~1/I. OK.)
- Merging bins must not change inferences — this axiom nearly forces Dirichlet.

## Worked Example
Die with 6 faces, prior Dirichlet(1,1,1,1,1,1), data: 10 rolls of face 1, none else.
- Posterior u=(11,1,1,1,1,1), u_0=16.
- P(next=1)=(11)/16=0.69, P(next=2)=1/16=0.0625 (not 0).
- If a coarser observer only sees “1 vs not-1”, consistency requires their Beta/Dirichlet hyperparameters to be (1,5) → posterior (11,5), P(next=1)=11/16, matching.

## Anti-patterns
- **Uniform on [0,1] for a high-D probability vector** (that is not even on the simplex).
- **Using Gaussian likelihoods on strictly positive data**.
- **Dirichlet(1..1) on a 10^5-word vocabulary** as if it were “innocent” — it puts huge implied counts on the tail unless you use a hierarchical / sparse prior.
- **Improper priors when you will compare models by evidence**.

## Key Takeaways
1. Learn Dirichlet, Gaussian, Gamma, Student-t as first-class tools.
2. Conjugacy turns inference into adding counts.
3. Predictive probabilities keep residual uncertainty (never P=0 for unseen symbols if u_i>0).
4. Aggregation consistency is Dirichlet’s uniqueness selling point.
5. Heavy tails (Student-t) for robustness.

## Connects To
- **Ch 3**: Beta is Dirichlet on 2-simplex.
- **Ch 22**: Dirichlet on π, Wishart on Σ in Bayesian mixtures.
- **Ch 27–28**: Laplace around these posteriors for evidence.
- **Ch 45**: Gaussian processes as infinite-dimensional Gaussian.
