# Chapter 32: Exact Monte Carlo Sampling

## Core Idea
Ordinary MCMC is only correct *after* an unknown mixing time. Coupling from the past (Propp–Wilson) uses coalescence of coupled chains started in the past, with reused randomness, to produce a sample that is *exactly* from the equilibrium distribution — or tells you to go further back.

## Key Concepts
- **The MCMC problem**: after T steps the law is P^{(T)}, not P. “Has it converged?” is usually unanswerable.
- **Coalescence**: chains that share one RNG can merge; after merge they stay together. If *all* starts coalesce, the chain has forgotten its initial condition.
- **Forward coalescence is not enough**: the state at first meeting is biased (e.g. always at a wall if merges only happen at walls).
- **Coupling from the past (CFTP)**: simulate from T_0 < 0 to time 0. If coalescence happened before 0, x(0) ~ π exactly. If not, double |T_0| and *reuse the same random numbers* on the overlapping interval.
- **Perfect simulation**: another name for exact sampling via CFTP.
- **Monotonicity / bounding chains**: you cannot start from every state in a huge space; if updates preserve order, it is enough to run the min and max states.

## Frameworks and Methods
- **Shared randomness**: one proposal stream drives every chain. Design the coupling so coalescence is possible (and, for efficiency, likely).
- **Doubling schedule**: T_0 = −1, −2, −4, … . Nested reuse means a successful long run is consistent with all shorter ones.
- **Why “from the past”**: if the infinite past would have coalesced, the present is a draw from the unique stationary law, independent of x(−∞).
- **Ising / attractive spin systems**: monotone CFTP is practical; this is the headline application after the toy {0,…,20} random walk.

## Key Equations
- Target: x ~ π with π Q = π (stationary of the kernel).
- Coupled update: x' = Φ(x, U), same U ~ Uniform for all chains.
- Coalescence: Φ(·, U_t) ∘ … ∘ Φ(·, U_{t+k}) is a constant map.
- Unbiasedness: if coalescence occurs on [T_0, 0], then x(0) ~ π.
- Complexity: expected |T_0| is on the order of the mixing time (you pay mixing, but you *know* you paid enough).

## Algorithms and Techniques
**Coupling from the past**
1. Choose T_0 < 0. Draw (or look up) random numbers U_t for t = T_0,…,−1.
2. Start a chain from every state (or from bounds) at t = T_0.
3. Update all chains with the *same* U_t.
4. If all trajectories have coalesced by t = 0, output x(0).
5. Else set T_0 ← 2 T_0, keep previously used U_t on the old interval, fill in the new past, repeat.

**Monotone CFTP (Ising-style)**
1. Partial order on configurations (e.g. spinwise ±1).
2. Use an update Φ that is monotone in x.
3. Run only the all-up and all-down chains; their coalescence implies all others have coalesced.

## Anti-patterns
- **Sampling at the first forward meeting time** and calling it exact — that law is concentrated on meeting places.
- **Fresh RNG when extending into the past** — breaks nested consistency; you can bias the output.
- **CFTP on a chain that cannot coalesce** (bad coupling, or deterministic cycles).
- **Ignoring that expected runtime can have heavy tails** near criticality: exactness ≠ cheap.

## Key Takeaways
1. Asymptotic correctness of MCMC is not a certificate for a finite run.
2. Coalescence + coupling from the past gives a *proof* that the sample is from π.
3. Reuse randomness; double the horizon.
4. Bounding chains make CFTP feasible on 2^{N} Ising spaces.
5. Use exact sampling to validate approximate MCMC, or when unbiasedness is non-negotiable.

## Connects To
- **Ch 29**: Metropolis, Gibbs, the unanswered mixing question.
- **Ch 31**: Ising is the practical monotone example.
- **Ch 30**: efficiency still matters; CFTP does not remove mixing cost.
- **Ch 26**: exact *inference* on graphs vs exact *sampling* of a chain.
