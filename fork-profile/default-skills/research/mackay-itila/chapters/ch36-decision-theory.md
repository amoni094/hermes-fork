# Chapter 36: Decision Theory

## Core Idea
Decision theory is trivial except for computation: choose action a maximizing expected utility E[U|a] = ∫ U(x,a) P(x|a) dx. Sequential decisions mix forward probability (what data might I see?) with inverse probability (what will I believe then?). Prospecting for a mine is the worked example: pay c for a chance to change the action.

## Key Concepts
- **Action a, state x, utility U(x,a)** (pessimists: loss L = −U).
- **Bayes action**: a* = argmax_a E[U|a].
- **Value of information**: expected utility *with* an experiment minus without; VOI ≥ 0 if you will act optimally afterwards (you can always ignore the datum).
- **Linear utility**: with U linear in return x, only posterior *means* matter; variances affect the decision only through how they shape the distribution of future means.
- **Gaussians**: prior x_n ~ N(μ_n, σ_n²); prospecting d_n | x_n ~ N(x_n, σ²); posterior precision adds; predictive variance of d is σ²+σ_n².

## Frameworks and Methods
- **One-shot decision**: enumerate a, compute E[U|a], pick the max. No extra philosophy.
- **Sequential / tree**: each experiment branches on d; at leaves choose a; at chance nodes average; at decision nodes max. Chess-sized trees are intractable (bounded rationality: Russell & Wefald, Baum & Smith).
- **Rational prospecting**: N independent sites. Without data, pick argmax μ_n. With one prospecting opportunity, choose the site where the *option* to revise the choice is worth more than c_n — typically a runner-up with large σ_n, not always the current leader.
- **Nonlinear U**: risk aversion makes σ_n matter even with no prospecting.

## Key Equations
- E[U|a] = ∫ U(x,a) P(x|a) dx
- No prospecting, linear U: a* = argmax_n μ_n,  E[U] = max μ_n
- With prospecting at n: U = −c_n + x_{a(d)}
- P(d_n) = Normal(μ_n, σ² + σ_n²)
- Posterior: precision 1/σ_n'² = 1/σ_n² + 1/σ²,  μ' = σ_n'² (μ_n/σ_n² + d_n/σ²)
- Distribution of the new mean μ': Gaussian, mean μ_n, variance s² = σ_n² − σ_n'²  (variance that will be “used up”)
- VOI = E_d[ max(μ'_n(d), max_{k≠n} μ_k) ] − max_k μ_k  − c  (schematic)

## Algorithms and Techniques
**Should I prospect once?**
1. Compute E[U] = max μ_n with no experiment.
2. For each candidate site n, push forward P(μ'_n): N(μ_n, s_n²).
3. After seeing μ'_n, action is argmax among {μ'_n} ∪ {μ_k}_{k≠n}.
4. Average that max over P(μ'_n); subtract c_n.
5. Prospect at the n with largest expected utility, or nowhere if all are worse than step 1.

**Gaussian mnemonics MacKay wants memorized**
- Independent add ⇒ variances add.
- Gaussians multiply ⇒ precisions add.

## Anti-patterns
- **Choosing the current best site to prospect** always — VOI is about *changing* the decision; a certain leader needs no experiment.
- **Including σ_n in the no-data choice while keeping U linear** — inconsistency; if risk matters, change U.
- **Computing posterior after d but forgetting to average over unknown d** when deciding whether to buy d.
- **Treating decision theory as a rival to Bayesian inference** — it *uses* the posterior.

## Key Takeaways
1. Infer P(x|data), then maximize expected U; that is the whole theory.
2. Experiments have value only if they can change the action.
3. Linear U ⇒ decide on means; buy data to move those means.
4. Sequential problems are inference + trees; computation, not axioms, is the bottleneck.
5. Independent Gaussian sites: variances add, precisions add, VOI is an option-value integral.

## Connects To
- **Ch 3, 21**: forward vs inverse probability.
- **Ch 41, 44**: predictions from a posterior, not a point w*.
- **Ch 28**: model choice as a decision if you specify U.
- **Ch 37**: sampling theory answers the wrong question; decisions need P(x|data).
