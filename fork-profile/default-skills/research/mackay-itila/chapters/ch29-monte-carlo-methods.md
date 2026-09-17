# Chapter 29: Monte Carlo Methods

## Core Idea
When you cannot sum or integrate, sample. Monte Carlo turns expectations into averages over random draws. Importance sampling, rejection sampling, and Markov chain Monte Carlo (Metropolis–Hastings, Gibbs) are the general-purpose Bayesian computers of the book. The hard part is not the update rule — it is diagnosing that the chain has mixed.

## Frameworks Introduced
- **The Monte Carlo identity**: E_p[f] ≈ (1/T) sum_{t=1}^T f(x^{(t)}) with x^{(t)} ~ p.
- **Importance sampling**: sample from q, weight w=p/q. Useful if q covers p’s mass.
- **Rejection sampling**: sample q, accept with p/(M q). Needs a tight envelope M q ≥ p.
- **Metropolis–Hastings**: propose x'~Q(x'|x), accept with a=min(1, [p(x')Q(x|x')]/[p(x)Q(x'|x)]).
- **Gibbs sampling**: MH with conditional proposals; accept probability 1. Requires tractable full conditionals.
- **Markov chain theory**: stationary distribution π=p if the chain is irreducible, aperiodic, and satisfies detailed balance.

## Key Concepts
- **Burn-in**: discard initial transient from a bad start.
- **Mixing / autocorrelation time τ**: effective sample size ESS ≈ T/τ. Highly correlated samples do not count as T independent ones.
- **Detailed balance**: p(x)Q(x'|x)a(x',x) = p(x')Q(x|x')a(x,x').
- **Random-walk MH**: Gaussian proposals; step size too small → slow diffusion; too big → high rejection.
- **Why MacKay cares**: Ising models, neural-net weights, Bayesian clustering — all high-D integrals.

## Key Equations
- Ê[f] = (1/T) ∑ f(x^t),  var ≈ Var(f)/ESS
- Importance: Ê[f] = ∑ w̃_t f(x^t),  w̃ = w/∑w,  w=p/q
- Effective sample size (IS): ESS = (∑w)² / ∑w²
- MH accept: a = min(1, p(x')Q(x|x') / p(x)Q(x'|x))
- Gibbs: x_i ~ P(x_i | x_{−i})
- Detailed balance ⇒ p stationary

## Algorithms and Techniques
**Metropolis–Hastings**
1. Start at x.
2. Propose x' ~ Q(·|x).
3. Compute a; accept x←x' with probability a, else stay.
4. Repeat; store x after burn-in, possibly thinned.

**Gibbs**
1. For i in 1..d: draw x_i from its full conditional.
2. One sweep = one sample (highly autocorrelated in practice).

**Importance sampling**
1. Draw from q that is *broader* than p in the tails.
2. Normalize weights; watch ESS. If one weight dominates, q failed.

## Mental Models
- Monte Carlo is for *expectations*, not for finding modes (use an optimizer).
- A chain that “looks stable” on one coordinate may be stuck in a metastable mode (Ising below critical T, Ch 31).
- Use Gibbs when conditionals are easy (Dirichlet–multinomial, GMM with conjugate priors); MH when they are not.
- Importance sampling dies in high-D (weights collapse). MCMC is the high-D tool.

## Worked Example
Estimate Z = ∫_0^1 f^r (1−f)^{N−r} df = B(r+1,N−r+1) by sampling — silly in 1-D (we know the Beta function) but pedagogical.
- Rejection: q=uniform, M=max of the polynomial. Acceptance rate collapses for large N (peak is narrow) — the Occam/Laplace story again.
- MH with Gaussian proposals on logit(f) mixes well.
- Lesson: parameterize to make the target blob-like, then MH is easy.

## Anti-patterns
- **Calling T correlated samples “T posterior draws”**.
- **Tiny random-walk steps** in high-D (diffusion time ~ L² / ε²).
- **Importance sampling from a too-narrow q**.
- **Starting 1 chain, no trace plots, no multiple starts**.
- **Using MCMC to maximize** (it will wander around the mode, not sit on it).

## Key Takeaways
1. Sampling estimates integrals; mixing, not the proposal formula, is the skill.
2. MH is universal; Gibbs is MH with perfect conditional proposals.
3. Monitor ESS, traces, and multiple chains.
4. High-D importance sampling usually fails; use MCMC or annealed variants (Ch 30).
5. Reparameterize so the posterior is roughly Gaussian, then even random-walk MH works.

## Connects To
- **Ch 27–28**: deterministic alternative when the posterior is a single blob.
- **Ch 30**: Hamiltonian / overrelaxation / simulated annealing as better movers.
- **Ch 31–32**: Ising as the test-bed; exact sampling.
- **Ch 41, 43**: sampling neural-net weights and Boltzmann machines.
