# Chapter 30: Efficient Monte Carlo Methods

## Core Idea
Random-walk Metropolis crawls in high dimension. Efficiency comes from using gradient information, suppressing random-walk, or changing temperature: overrelaxation, Hamiltonian / hybrid Monte Carlo, simulated annealing, and thermodynamic integration. The aim is larger ESS per unit compute.

## Frameworks Introduced
- **Overrelaxation (Adler / ordered overrelaxation)**: when sampling Gaussians or conditionals, step *through* the mean to negatively correlate successive samples, killing random-walk.
- **Hybrid / Hamiltonian Monte Carlo (HMC)**: introduce momentum p, simulate Hamiltonian dynamics of (θ,p) with gradient ∇ log P, then Metropolis-correct. Long trajectories propose far-away points with high acceptance.
- **Simulated annealing**: lower temperature T slowly so the chain finds modes of P^{1/T}; a *mode finder*, not a sampler at T=1 unless you raise T back.
- **Annealed importance sampling / thermodynamic integration**: a ladder of temperatures to estimate evidence Z.

## Key Concepts
- **Random-walk time**: to travel distance L with step ε takes (L/ε)² steps. HMC travels in ~L/ε gradient steps.
- **Leapfrog integrator**: symplectic, reversible, volume-preserving — required for HMC’s MH correction to be valid with Jacobian 1.
- **Step size / trajectory length**: too large ε, energy error, rejections; too short trajectories, random-walk remains.
- **Auxiliary momentum**: p ~ Normal(0,M); Hamiltonian H=−log P(θ) + (1/2) p^T M^{−1} p.
- **Overrelaxation parameter α ∈ [−1,1]**: α=−1 is perfect reflection through the conditional mean.

## Key Equations
- Random-walk mixing time ~ L²/ε²
- HMC: dθ/dt = M^{−1} p,  dp/dt = ∇ log P(θ)
- Leapfrog: p+= (ε/2)∇logP; θ+=ε M^{−1}p; p+= (ε/2)∇logP
- Accept a=min(1, exp(H_old − H_new))
- Overrelaxation (scalar Gaussian): x' = μ − α (x−μ) + σ√(1−α²) ξ
- Thermodynamic integration: log Z = ∫_0^1 E_{P_β}[log P_unnorm] dβ  (schematic)

## Algorithms and Techniques
**HMC**
1. Draw p ~ Normal(0,M).
2. Leapfrog L steps of size ε.
3. Flip p (makes proposal reversible); MH on Hamiltonian energy.
4. Tune ε so acceptance is roughly 60–90%; tune L so trajectories traverse the typical set.

**Ordered overrelaxation Gibbs**
1. For each coordinate, apply the overrelaxed conditional draw with α≈−1.
2. Especially effective on highly correlated Gaussians.

**Annealing to a mode**
1. Sample at high T.
2. Reduce T (geometric schedule).
3. At T≈0 you have a MAP, not posterior samples.

## Mental Models
- If you can compute ∇ log P, you should almost never use random-walk MH.
- Momentum is there to *suppress* diffusion, not to add noise.
- Annealing finds modes; a temperature ladder *with samples at T=1* estimates Z.
- Overrelaxation is the cheap trick when Gibbs is already available.

## Worked Example
2-D highly correlated Gaussian, correlation 0.99. Random-walk MH with isotropic proposals: tiny steps, ESS miserable. Gibbs: still random-walks along the long axis. Overrelaxed Gibbs: bounces along the axis, ESS jumps. HMC with decent L: one trajectory traverses the cigar, ESS ~ T.

Ising (Ch 31): HMC is less natural (discrete); use cluster algorithms / Gibbs / simulated annealing instead. Match the sampler to the state space.

## Anti-patterns
- **HMC with L=1 leapfrog step** (this is just Langevin / random-walk with gradient).
- **Non-symplectic integrators** in HMC (Jacobians, bias).
- **Annealing and claiming you have posterior samples at T=1** after only cooling.
- **One ε for all parameters when scales differ** — precondition M, or reparameterize.

## Key Takeaways
1. Kill random-walk: overrelaxation or HMC.
2. HMC needs gradients, a symplectic integrator, and tuned (ε,L,M).
3. Annealing ≠ sampling unless you include T=1 (and the ladder for Z).
4. Efficiency is ESS per gradient/eval, not raw T.
5. Discrete spaces want other tricks (Ch 31–32).

## Connects To
- **Ch 29**: the slow baseline.
- **Ch 31**: where you see mixing failure visually (magnetization traces).
- **Ch 32**: exact sampling, another way to know you are unbiased.
- **Ch 41**: HMC on neural-net weights.
