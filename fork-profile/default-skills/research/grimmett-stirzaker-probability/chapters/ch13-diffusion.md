# Chapter 13: Diffusion Processes

## Core Idea
Brownian motion / the Wiener process is the scaling limit of random walk and the canonical continuous-time, continuous-space stochastic process. Its sample paths are continuous but nowhere differentiable. Itô's formula extends ordinary calculus to these irregular paths, adding a "second-order correction" (the Itô term).

## Frameworks Introduced

- **Wiener process W (Definition 13.3.1)**:
  - W(0) = 0; Gaussian process with stationary independent increments
  - W(s+t) − W(s) ~ N(0, σ²t); continuous sample paths a.s.
  - Covariance: cov(W(s), W(t)) = σ² min(s,t)
  - Nowhere differentiable a.s.

- **Diffusion process (§13.3)**: Markov process X with transition density satisfying Kolmogorov forward/backward equations. Characterized by drift μ(x,t) and diffusion σ²(x,t).

- **Ornstein-Uhlenbeck process**: Stationary Gaussian Markov process with autocovariance c(t) = c(0)e^{-α|t|}. Models mean-reverting dynamics; limit of Langevin equation (damped random walk).

- **Itô's formula (§13.9)**: For smooth f and Itô process dX = μdt + σdW:
  df(X(t)) = f'(X)dX + ½f''(X)σ²dt
  Key: the extra ½f''σ²dt term (absent in ordinary calculus) arises because dW ~ √dt (variance ∝ dt).

- **First passage times (§13.4)**: TX = min{t: W(t) = x}. For standard Brownian motion: E(TX) = ∞ (recurrent but null-recurrent in 1D). Distribution: P(TX ≤ t) = 2P(W(t) ≥ x).

- **Brownian bridge (§13.6)**: W(t) conditioned on W(T)=0; used in statistics and path sampling.

## Key Concepts

- **Wiener process** — canonical Brownian motion model; Gaussian, independent increments, continuous paths
- **Quadratic variation** — [W,W]_t = t for standard BM (makes Itô term appear)
- **Itô integral** — ∫₀ᵗ f(s)dW(s); defined as L² limit, is a martingale when f is adapted
- **Itô's formula** — stochastic chain rule: df = f'dX + ½f''(dX)² where (dW)² = dt
- **Generator** — L = μ∂_x + ½σ²∂_{xx}; the operator governing evolution of E[f(X(t))|X(0)=x]
- **Kolmogorov equations** — backward: ∂u/∂t = Lu; forward (Fokker-Planck): ∂p/∂t = L*p
- **Feynman-Kac formula** — E[f(X(T))·exp(∫₀ᵀ V(X)dt)|X(0)=x] solves PDE with generator L
- **Lévy processes** — generalization: stationary independent increments, may have jumps
- **Subordinator** — non-decreasing Lévy process; creates time changes for other processes

## Mental Models

- Brownian motion is the "square root of time": variance grows linearly, but displacement grows like √t. This makes it irregular everywhere.
- Itô's formula: in stochastic calculus, Taylor expansion must include the (dW)² = dt term because the second derivative contributes at first order.
- Ornstein-Uhlenbeck as "noisy rubber band": pulled back toward 0 with force proportional to displacement + random noise.

## Key Takeaways

1. Wiener process W has continuous paths but is nowhere differentiable — classical calculus fails.
2. Itô's formula: df(W) = f'(W)dW + ½f''(W)dt. The extra dt term is essential.
3. Quadratic variation [W,W]_t = t: it's this non-zero QV that creates the Itô correction.
4. First passage times for BM on ℝ: finite a.s. but with infinite expectation (null recurrent in 1D).
5. OU process is the only stationary Gaussian Markov process (with exponential covariance).

## Connects To

- **Ch06**: Continuous-time Markov chains → diffusion limit via scaling.
- **Ch09**: Gaussian processes, OU process, Wiener process as special Gaussian processes.
- **Ch12**: Itô integral is a continuous-time martingale; Itô's formula is the continuous OST framework.
