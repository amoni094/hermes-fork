# Chapter 43: Boltzmann Machines

## Core Idea
Replace Hopfield’s deterministic descent with Gibbs sampling of P(x|W) ∝ exp(x^T W x). Maximum-likelihood learning matches pairwise correlations in data to pairwise correlations under the model: wake minus sleep. Visible-only machines capture only second-order statistics; hidden units are required for higher-order structure (chairs, the shifter ensemble).

## Key Concepts
- **Stochastic Hopfield / Boltzmann machine**: P(x_i=1 | rest) = σ(a_i); this *is* Gibbs sampling for the Ising / Hopfield energy.
- **Partition function Z(W)**: ln Z’s derivative is the model’s ⟨x_i x_j⟩ — the usual exponential-family moment.
- **ML gradient**: ∂ ln P(data|W)/∂w_{ij} = N ( ⟨x_i x_j⟩_Data − ⟨x_i x_j⟩_{P(x|W)} ).
- **Wake / sleep**: increase weights with real-world correlations; decrease with dream (model) correlations. Equilibrium when they match.
- **Hebb as first step**: at W=0, model correlations vanish, so one gradient step *is* the Hebb rule.
- **Hidden units**: extra unobserved neurons; clamp visibles to data during wake (average over hiddens), free-run during sleep. Needed because ⟨x_i x_j⟩ cannot express XOR-like / shift structure.

## Frameworks and Methods
- **Exponential family view**: Boltzmann machines are Markov random fields with pairwise potentials; ML is moment matching.
- **Monte Carlo gradient**: estimate ⟨x_i x_j⟩_model by running the activity rule (Gibbs) — expensive, mixing issues (Ch 29, 31).
- **Criticism of visible-only nets**: second-order statistics (pixel pairwise) fail for images of chairs vs carrots; they also fail for the *shifter ensemble* (bottom row = shifted copy of top row) unless you add latents that represent “shift = {−1,0,+1}”.
- **Full Bayes vs ML**: MacKay notes a posterior over W would be better (as in Ch 41) but derives ML.

## Key Equations
- E(x) = − x^T W x   (symmetric W, zero diag)
- P(x|W) = exp(x^T W x) / Z(W)
- Activity: P(x_i = +1 | rest) = 1 / (1 + exp(−2 a_i))  (for ±1 spins; logistic for 0/1)
- ∂ ln Z / ∂w_{ij} = ⟨x_i x_j⟩_{P(x|W)}
- ∂ ln P(D|W) / ∂w_{ij} = N ⟨x_i x_j⟩_Data − N ⟨x_i x_j⟩_model
- Hebb at origin: w_{ij} ← η ⟨x_i x_j⟩_Data
- With hiddens: ⟨x_i x_j⟩_Data becomes ⟨x_i x_j⟩_{P(h|x_data,W)}  (clamped)

## Algorithms and Techniques
**Visible Boltzmann ML**
1. Compute data correlations C_{ij}^{data} = ⟨x_i x_j⟩.
2. Gibbs-sample the net with current W; estimate C_{ij}^{model}.
3. w_{ij} ← w_{ij} + η (C_{ij}^{data} − C_{ij}^{model}).
4. Repeat until the two correlation matrices match.

**Hidden units**
1. **Wake / positive phase**: clamp visible x to a datapoint; sample (or mean-field) hiddens; accumulate correlations among all units.
2. **Sleep / negative phase**: unclamp; sample all units from the model; accumulate correlations.
3. Gradient = positive − negative.

## Anti-patterns
- **Visible-only BM on data whose information is in higher-order statistics**.
- **One Hebb pass and stop** — Hebb matches correlations only at W=0, not at the ML W.
- **Short Gibbs runs for the model term** — biased gradients, same mixing failure as Ising.
- **Asymmetric W** — you leave the energy-based model.

## Key Takeaways
1. Boltzmann machines make the Hopfield energy a proper generative model.
2. ML = match pairwise moments; Hebb is the first gradient step.
3. The hard term is the model’s correlations (Z, mixing).
4. Hiddens are not a luxury; they are how you escape second-order statistics.
5. Wake–sleep is the conceptual ancestor of later contrastive / energy-based training.

## Connects To
- **Ch 22**: mixture models — another latent generative story.
- **Ch 29–31**: Gibbs on Ising-like systems.
- **Ch 33**: mean-field instead of sleep-phase MC.
- **Ch 42**: deterministic limit / energy.
- **Ch 34**: ICA — different latents, still generative.
