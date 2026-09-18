# Chapter 9: Stationary Processes

## Core Idea
A stationary process has time-shift invariant distributions. In the wide-sense, this means constant mean and autocovariance c(t) depending only on lag. The spectral representation connects time-domain (autocovariance) to frequency-domain (spectral density). The ergodic theorem generalizes the LLN to stationary processes.

## Key Concepts
- **Strictly stationary**: all fdds shift-invariant
- **Weakly (wide-sense) stationary**: E(X(t)) = const, cov(X(s),X(t)) = c(s−t)
- **Autocovariance function c(t)**: real, symmetric c(t)=c(−t), non-negative definite
- **Spectral density f(λ)**: c(t) = ∫ e^{iλt} f(λ)dλ; f(λ)≥0 (Bochner's theorem)
- **Ergodic theorem**: time average → ensemble average for ergodic stationary processes
- **Linear prediction**: best linear predictor of X(t+h) given {X(s): s≤t} uses spectral density
- **Gaussian process**: all fdds are multivariate normal; stationary iff weakly stationary
- **Ornstein-Uhlenbeck**: stationary Gaussian Markov process; c(t) = σ²e^{-α|t|}
- **Wiener process**: Gaussian process with c(s,t) = min(s,t) — NOT stationary (variance grows)

## Key Takeaways
1. Bochner's theorem: c is a valid autocovariance iff non-negative definite ↔ c is Fourier transform of a non-negative measure (spectral measure).
2. Ergodic theorem: for ergodic processes, time average of f(X(t)) → E[f(X(0))] a.s.
3. For Gaussian processes: weakly stationary ↔ strictly stationary.
4. OU process: unique stationary Gaussian Markov process with exponentially decaying covariance.

## Connects To
- **Ch07**: Ergodic theorem is the process analog of the strong LLN.
- **Ch13**: Wiener process as a Gaussian process; OU process via Langevin SDE.
