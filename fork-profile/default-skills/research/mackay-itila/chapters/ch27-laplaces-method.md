# Chapter 27: Laplace’s Method

## Core Idea
When a posterior is a high-dimensional peak, approximate it by a Gaussian at the mode: log P(θ|D) ≈ const − (1/2)(θ−θ̂)^T A (θ−θ̂), with A = −∇∇ log P. The Gaussian integral then gives an evidence estimate. This is the cheap, deterministic workhorse behind Occam factors in Ch 28.

## Frameworks Introduced
- **Laplace approximation**
  1. Find a mode θ̂ of P(θ|D) (or of P(D,θ)).
  2. Hessian A = −∇∇ log P(D,θ) |_{θ̂}
  3. P(θ|D) ≈ Normal(θ̂, A^{−1})
  4. P(D|H) ≈ P(D,θ̂) (2π)^{k/2} (det A)^{−1/2}
- **Occam factor** (preview): (2π)^{k/2} (det A)^{−1/2} / prior-volume ≈ posterior-volume / prior-volume.

## Key Concepts
- **Mode vs mean**: Laplace uses the MAP, not the posterior mean. Bad if the posterior is skewed (e.g. θ>0 parameters).
- **Hessian / curvature**: sharp peaks (large eigenvalues of A) occupy little volume → small Occam factor → penalty for extra parameters that are well-determined.
- **Reparameterization**: Laplace is not invariant to nonlinear changes of variables. Choose coordinates where the posterior looks Gaussian (e.g. log σ, unconstrained simplex maps).
- **Multiple modes**: Laplace at one mode misses the rest; sum contributions if you can find them.

## Key Equations
- log P(D,θ) ≈ log P(D,θ̂) − ½ Δθ^T A Δθ
- ∫ exp(−½ Δθ^T A Δθ) dθ = (2π)^{k/2} (det A)^{−1/2}
- P(D|H) ≈ P(D|θ̂,H) P(θ̂|H) (2π)^{k/2} (det A)^{−1/2}
- Occam factor ≈ (2π)^{k/2} / ( (det A)^{1/2} × prior volume )

## Algorithms and Techniques
**Laplace evidence**
1. Optimize θ̂ = argmax [log likelihood + log prior] with a second-order or quasi-Newton method.
2. Compute Hessian analytically or by finite differences / autodiff.
3. Ensure A is positive definite (on the constrained manifold).
4. Evaluate the evidence formula in log space: log P(D,θ̂) + (k/2)log(2π) − ½ log det A.
5. Transform to coordinates with support ℝ^k first (log, logit).

## Mental Models
- Think “posterior volume ≈ product of 1/√λ_i error bars”.
- Use Laplace when n is large, likelihood is peaked, and k is moderate.
- Do not use Laplace on a posterior that piles up against a boundary (the bent coin with r=N, θ̂=1).

## Worked Example
1-D parameter, log posterior = −N (θ−θ_true)² / (2σ²) + const, already Gaussian. Hessian A=N/σ². Laplace is exact: evidence factor √(2π σ²/N). The extra parameter’s Occam factor shrinks as 1/√N — more data, more penalty for a parameter that is tightly determined (it used up more of its prior).

Bent coin with uniform prior, N large, r/N away from 0,1: Laplace in logit coordinates is accurate; Laplace in f∈[0,1] near the edge is terrible.

## Anti-patterns
- **Laplace in f on [0,1] near 0 or 1**.
- **Ignoring det A and quoting only the MAP likelihood** as a model score.
- **Singular Hessian** (unidentifiable parameters, label switching in mixtures) — det A=0, evidence formula blows up.
- **Trusting Laplace for small N or heavy-tailed posteriors** (use MCMC, Ch 29).

## Key Takeaways
1. Gaussian-at-the-mode is the default deterministic posterior approximation.
2. Evidence ≈ height × posterior volume.
3. Reparameterize so the Gaussian assumption is plausible.
4. This is how Occam’s razor becomes a number in Ch 28.
5. When the posterior is not a blob, pick another method.

## Connects To
- **Ch 3**: Occam story without the Gaussian integral.
- **Ch 28**: model comparison using this formula.
- **Ch 33**: variational Gaussians as a cousin (optimize the whole Gaussian, not just the mode).
- **Ch 41**: neural-net learning as inference, Laplace on weights (evidence framework).
