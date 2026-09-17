# Chapter 8: Random Processes (Overview)

## Core Idea
Chapter 8 provides an overview of process types — stationary, renewal, queues, Wiener — before the in-depth chapters. The existence theorem (Kolmogorov consistency) guarantees stochastic processes can be constructed from consistent finite-dimensional distributions.

## Key Concepts
- **Stochastic process** {X(t): t∈T}: collection of r.v.s indexed by time
- **Stationary process**: finite-dimensional distributions shift-invariant in time
- **Kolmogorov existence theorem** (§8.9.3): Consistent family of fdds → process exists
- **Wiener process**: introduced here as the canonical continuous-time process (details in Ch13)
- **Lévy process**: stationary independent increments + continuous in probability; includes BM and Poisson
- **Subordinator**: non-decreasing Lévy process; used for time changes
- **Self-similar process**: X(at) =^d a^H X(t); Brownian motion is self-similar with H=1/2
- **Stationary independent increments**: each increment W(t+s)−W(t) ~ same distribution, independent of history

## Key Takeaways
1. Kolmogorov: specify consistent fdds → process exists. Consistency = marginalization is compatible.
2. Lévy processes unify BM (continuous) and Poisson process (jump). Key property: stationary independent increments.
3. Self-similarity: BM looks the same at all scales (H=1/2). Fractional BM has H≠1/2 for memory.

## Connects To
- **Ch09**: Stationary processes in depth (spectral theory, ergodic theorem).
- **Ch10**: Renewal processes in depth.
- **Ch13**: Brownian motion and diffusions in depth.
