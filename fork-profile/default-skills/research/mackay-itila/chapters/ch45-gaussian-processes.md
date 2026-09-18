# Chapter 45: Gaussian Processes

## Core Idea
A Bayesian neural net defines a prior on functions y(x). In the large-H limit that prior is a Gaussian process (Neal). Discard parameters: specify a mean (often 0) and a covariance function C(x,x′), then condition on data with matrix algebra. Many interpolators (RBF, splines, kriging, Wiener filters) are GPs. Adaptation is inference of kernel hyperparameters, not of w.

## Key Concepts
- **GP**: a distribution over functions such that any finite (y(x_1),…,y(x_n)) is multivariate Gaussian. Specified by m(x) and C(x,x′).
- **Why GPs replace nets**: predictions depend only on P(y(·)) and the noise model, not on a parameterization y(x;w).
- **Regression**: t_n = y(x_n) + noise; jointly Gaussian ⇒ posterior y is Gaussian with explicit mean and variance.
- **Covariance / kernel**: encodes smoothness, periodicity, input scales. Examples: Gaussian/RBF C ∝ exp(−|x−x′|²/(2ℓ²)), Ornstein–Uhlenbeck, Brownian, rational quadratic.
- **Hyperparameters**: ℓ, signal variance, noise variance — learned by maximizing P(t|X,θ) (the GP evidence) or by MCMC.
- **Classification**: y is a latent GP; t is Bernoulli(σ(y)). Non-Gaussian likelihood ⇒ Laplace, EP, or MCMC, not a single linear solve.
- **Kriging / Kalman / Wiener**: old names for GP regression in space/time.

## Frameworks and Methods
- **Standard parametric regression**: posterior P(y(·)|t,X) ∝ P(t|y) P(y); P(y) was implicit in architecture+regularizer. Make P(y) explicit.
- **Conditioning**: let K_{nn'} = C(x_n,x_{n'}) + σ_ν² δ_{nn'}. Predictive mean at x_* is k_*ᵀ K^{−1} t; variance is C(x_*,x_*) − k_*ᵀ K^{−1} k_*.
- **O(N³)**: inversion of K is the bottleneck. Fine for N up to ~10³ in 2003; sparse / approximate GPs later.
- **MacKay’s assessment**: for supervised regression/classification, GPs often *supersede* MLPs — fewer local minima in w, clearer priors, same function class as infinite nets.
- **Software note**: MacKay points to his demos and Neal’s GP code.

## Key Equations
- y(·) ~ GP(m, C), often m=0
- P(t | y, X) = N(y_X, σ_ν² I)   (regression)
- K = C(X,X) + σ_ν² I
- ȳ(x_*) = C(x_*,X) K^{−1} t
- var y(x_*) = C(x_*,x_*) − C(x_*,X) K^{−1} C(X,x_*)
- ln P(t|X,θ) = −½ tᵀ K_θ^{−1} t − ½ ln det K_θ − (N/2) ln 2π
- RBF: C(x,x′) = σ_f² exp(−∑_i (x_i−x'_i)² / (2 ℓ_i²))  (ARD lengths ℓ_i)
- Classification: P(t=1|x) = σ(y(x)), y~GP

## Algorithms and Techniques
**GP regression**
1. Choose C_θ and noise σ_ν².
2. Build K; Cholesky solve α = K^{−1} t.
3. Mean at new x: C(x,X) α; variance from the Schur complement.
4. Optimize θ by gradient of ln P(t|X,θ) (uses K^{−1} and ∂K/∂θ) or MCMC θ.

**GP classification**
1. Laplace: mode of P(y|t), Gaussian around it, then the regression formulae on the approximate likelihood.
2. Or sample y on the N training points (Neal).

## Anti-patterns
- **Using a GP as if it were a point interpolator** and ignoring predictive variance.
- **One global ℓ on unscaled inputs** — ARD lengthscales exist for a reason.
- **N in the tens of thousands with dense K^{−1}**.
- **Assuming classification is the same closed-form as regression**.
- **A non-PSD “covariance”** — not a GP.

## Key Takeaways
1. Infinite Bayesian MLPs are GPs; you can start from C(x,x′).
2. Regression is linear algebra on K; classification needs extra approximation.
3. Hyperparameters of C *are* the model; evidence trains them.
4. Error bars come for free from the posterior process.
5. For many supervised tasks MacKay judges GPs the cleaner tool vs backprop nets.

## Connects To
- **Ch 23**: Gaussians, kernels as covariances.
- **Ch 27–28**: evidence for kernel hyperparameters.
- **Ch 41, 44**: function-space view of neural learning.
- **Ch 46**: linear-Gaussian image priors are GPs on pixels.
- **Ch 11**: Gaussian channels — same algebra, different story.
