# Chapter 33: Variational Methods

## Core Idea
When Z and posterior expectations are intractable, approximate P by a tractable family Q(x; θ) and minimize a variational free energy. Gibbs’ inequality makes this a *lower* bound on Z (upper bound on free energy F). Mean-field theory is the separable-Q special case.

## Key Concepts
- **KL / relative entropy**: D_KL(Q||P) = ∑_x Q(x) ln[Q(x)/P(x)] ≥ 0, =0 iff Q=P. Asymmetric.
- **True free energy**: βF = −ln Z.
- **Variational free energy**: β F̃(θ) = ∑ Q ln(Q / e^{−βE}) = β ⟨E⟩_Q − S_Q = D_KL(Q||P) + βF.
- **Mean field**: Q(x; a) = ∏_n q_n(x_n), often q_n(x_n) ∝ exp(a_n x_n) for Ising spins.
- **Bound**: F̃ ≥ F, so Z̃ = e^{−β F̃} ≤ Z. Optimizing θ tightens the bound and yields an approximate posterior.
- **Why F̃ is computable**: for pairwise E and factorized Q, ⟨E⟩_Q and S_Q collapse to sums over single sites and pairs — no 2^N sum.

## Frameworks and Methods
- **Feynman–Bogoliubov variational principle**: physics name for free-energy minimization with a trial ensemble.
- **Mean-field Ising**: self-consistent magnetization m = tanh(β J z m + β h). Predicts a spurious phase transition in 1-D; qualitatively OK in high dimension / infinite range.
- **Variational inference for data models**: same math with −ln P(data, latent | params) as energy. Approximate posterior over latents (and maybe parameters).
- **Unknown Gaussian example**: replace a tricky posterior by a Gaussian Q; match by minimizing KL(Q||P) (not the other way — that is expectation propagation / moment matching).
- **Other variational methods**: not only free energy — e.g. other divergences, bounds on likelihoods, variational approximations to MAP.

## Key Equations
- D_KL(Q||P) ≥ 0  (Gibbs)
- P(x) = e^{−βE}/Z,  Z = ∑ e^{−βE}
- β F̃ = β ⟨E⟩_Q − S_Q = D_KL(Q||P) + βF
- For separable Ising Q: S_Q = ∑_n H_2(q_n),  ⟨x_n⟩ = tanh(a_n)
- ⟨x_m x_n⟩_Q = ⟨x_m⟩⟨x_n⟩ if m≠n (mean field ignores correlations)
- Mean-field fixed point: m = tanh(β ∑_j J_{ij} m_j + β h_i)
- Evidence bound: ln Z ≥ −β F̃  (ELBO in modern names)

## Algorithms and Techniques
**Mean-field / coordinate ascent**
1. Choose Q in a factorized (or structured) family.
2. Write F̃ in closed form (entropies + expected energy).
3. Set ∂F̃/∂θ = 0 or do coordinate ascent on each factor.
4. For Ising: iterate m_i ← tanh(β ∑_j J_{ij} m_j + β h_i) until consistency.
5. Report F̃ as a bound and Q as the approximate posterior.

**Variational Bayes (data modelling)**
1. Energy = −ln P(observations, latents, params).
2. Factor Q(latents) Q(params) or finer.
3. Alternate updates; each is often conjugate and closed form (like EM, which is a special case).

## Anti-patterns
- **Minimizing D_KL(P||Q) when you only have Q-expectations** — you cannot. Free energy uses D_KL(Q||P), which underestimates posterior variance (mean field is overconfident).
- **Trusting mean-field critical T** in 1-D or 2-D Ising — qualitatively wrong location / existence.
- **A Q family that cannot represent the modes you care about** (unimodal Q on a bimodal posterior).
- **Forgetting that a tight F̃ is not the same as calibrated marginals**.

## Key Takeaways
1. Variational methods turn inference into optimization of a bound.
2. Factorized Q makes ⟨E⟩ and S cheap; it also kills correlations.
3. You get a number (bound on ln Z) *and* an approximate distribution.
4. Mean field is the physicist’s name for the same trick used in variational Bayes.
5. Use when MCMC is too slow and Laplace (Ch 27) is too local / Gaussian.

## Connects To
- **Ch 2**: Gibbs’ inequality.
- **Ch 22**: EM as coordinate ascent on a bound.
- **Ch 27**: Laplace — local Gaussian vs global variational family.
- **Ch 28**: model comparison needs Z; variational gives a bound, not Z.
- **Ch 31**: ferromagnetic Ising is the worked mean-field example.
- **Ch 43**: Boltzmann machines — mean field vs sampling for ⟨x_i x_j⟩.
