# Chapter 46: Deconvolution

## Core Idea
Imaging is d = R f + n: a known linear blur/point-spread plus noise. The optimal linear filter (Wiener / Gaussian prior) is the posterior mean under Gaussian image and noise models — and is also the MSE-best linear estimator without saying “Bayes”. Gaussian priors are a poor image model (negative sky, ringing). Better P(f) (positivity, maxent, edges) beats fancier inverse matrices. Supervised nets as deblurrers are just learned linear/nonlinear filters; they do not replace a well-matched prior.

## Key Concepts
- **Distinguish image f and data d**: even if they live on the same pixel grid.
- **R**: blur / projection / point-spread. n: usually iid Gaussian, std σ_ν.
- **Gaussian image prior**: P(f) ∝ exp(− ‖f‖_{C^{−1}}^2 / (2σ_f²)). C=I uncorrelated pixels; C = (G G^T)^{−1} “intrinsic correlation function” (smoothness), G not to be confused with R.
- **Optimal linear filter**: f_MP = (R^T R + (σ_ν²/σ_f²) C)^{−1} R^T d  (or the dual form with C R^T (R C R^T + …)^{−1}).
- **Pseudoinverse**: ignore the regularizer term — ill-conditioned, noise explosion.
- **Maxent / positivity**: Gull–Daniell; killed negative-flux artefacts that linear filters produce on astronomical images.
- **Human deconvolution**: the eye/brain as a prior-using reconstructor (MacKay’s speculative close).

## Frameworks and Methods
- **Bayesian linear-Gaussian**: posterior is Gaussian; mean = MAP = linear in d; covariance Σ = [−∇∇ log P(f|d)]^{−1} gives joint error bars.
- **Evidence**: P(d|σ_ν,σ_f,H) compares noise levels, smoothness, alternative R.
- **Non-Bayesian derivation**: assume f̂=W d, minimize E‖f̂−f‖² over noise and image ensembles; get the same W. Assumptions (quadratic loss, linear estimator) were implicit.
- **Why better priors matter**: less data needed for the same question; artefacts track model mismatch, not “the math of inversion”.
- **Supervised NN deconvolution**: train y(d) ≈ f on simulated blurs. Can work as a nonlinear Wiener filter; still weaker than an explicit image model when you have one, and fails outside the training blur.

## Key Equations
- d_n = ∑_k R_{nk} f_k + n_n
- P(d|f) = N(R f, σ_ν² I)
- P(f) = N(0, σ_f² C^{−1})   (MacKay’s C-in-the-exponent convention: check C vs C^{−1} in (46.3)/(46.7))
- f_MP = (R^T R + (σ_ν²/σ_f²) C)^{−1} R^T d
- Dual: W = C^{−1} R^T (R C^{−1} R^T + σ_ν² I)^{−1}  (with F = σ_f² C^{−1} as second-moment)
- Σ_{f|d} = [ R^T R / σ_ν² + C / σ_f² ]^{−1}
- Linear estimator derivation: W_opt = F R^T (R F R^T + σ_ν² I)^{−1}

## Algorithms and Techniques
**Wiener / optimal linear reconstruction**
1. Know or estimate R, σ_ν, image covariance F (or smoothness C).
2. Apply W_opt in Fourier space if R is convolution (diagonalizes).
3. Inspect negatives / ringing; if present, the Gaussian prior is the culprit.

**Upgrade the prior**
1. Positivity (maxent, truncated Gaussian, entropic).
2. Edge-preserving (total variation, mixture of Gaussians — later than 2003).
3. Compare models with the evidence P(d|H).

## Anti-patterns
- **Inverting R without regularization**.
- **Accepting negative flux** because “the linear filter is optimal”.
- **Confusing the intrinsic correlation G with the blur R**.
- **Training a net on one PSF and deploying on another**.
- **Quadratic loss on images** if your real loss cares about edges or positivity.

## Key Takeaways
1. Deconvolution is Bayesian inference of f, not “undoing a matrix”.
2. Linear-Gaussian ⇒ Wiener filter = posterior mean = best linear MSE estimator.
3. The prior is the scientific content; mismatch shows up as negatives and rings.
4. Error bars and evidence come with the Gaussian calculation; keep them when you change priors.
5. Learned nets are not a substitute for saying what images are.

## Connects To
- **Ch 11**: Gaussian channel, linear estimators.
- **Ch 27–28**: Laplace/evidence for σ_ν, σ_f, H.
- **Ch 45**: GP priors on functions / images.
- **Ch 44**: supervised nets as inverse maps.
- **Ch 33**: variational image models when P(f) is non-Gaussian.
