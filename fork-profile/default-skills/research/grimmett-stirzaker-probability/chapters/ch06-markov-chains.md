# Chapter 6: Markov Chains

## Core Idea
A Markov chain is a random process where the future depends only on the present, not the past. The entire long-run behavior — classification of states, stationary distributions, convergence rates — follows from the transition matrix P.

## Frameworks Introduced

- **Markov property**: P(Xn = s | X0,...,Xn-1) = P(Xn = s | Xn-1) for all n, s.
  - When to use: Any system where the current state is a sufficient statistic for the future.
  - How: Define state space S (countable), transition matrix P = (pij) where pij = P(Xn+1=j | Xn=i).

- **Chapman-Kolmogorov equations**: P(m, m+n+r) = P(m, m+n)·P(m+n, m+n+r), so n-step matrix = Pⁿ.
  - When to use: Computing long-run transition probabilities from short-run ones.

- **Classification of states**:
  - **Transient**: P(eventual return) < 1 → pii(n) → 0
  - **Recurrent** (null): P(return) = 1 but E[return time] = ∞
  - **Positive recurrent**: P(return) = 1 and E[return time] = μi < ∞

- **Stationary distribution π (Theorem 6.4.3)**:
  - Unique stationary π exists iff chain is irreducible and positive recurrent.
  - π satisfies πP = π, Σπi = 1, πi = 1/μi.
  - For irreducible, positive recurrent, aperiodic chains: pij(n) → πj as n → ∞.

- **Reversibility (detailed balance)**: π is stationary and chain is reversible iff πi·pij = πj·pji for all i,j. Faster to verify than πP=π.

- **MCMC (§6.14)**: Construct a Markov chain with target stationary distribution π. Metropolis-Hastings acceptance rule makes any proposal chain reversible with respect to π.

## Key Concepts

- **State space S** — countable set of values the chain takes
- **Transition matrix P** — stochastic matrix: non-negative entries, rows sum to 1
- **n-step transition** — pij(n) = (Pⁿ)ij
- **Irreducible** — every state is reachable from every other state
- **Aperiodic** — gcd of return times = 1 (no periodic oscillation)
- **Mean return time μi** — E[first return to state i starting from i]
- **Mixing time τmix(ε)** — min n such that max_i ||Pⁿ(i,·) − π||_TV ≤ ε
- **Coupling** — joint process (Xn, Yn) where both chains run independently until they meet
- **Spectral gap** — 1 − λ₂ where λ₂ is second-largest eigenvalue of P; controls mixing rate

## Mental Models

- "Mixing time" = how long until the chain forgets its start. Governs convergence of Monte Carlo estimates.
- Use stationary distribution as the "equilibrium" prediction: after long time, P(Xn = i) ≈ πi regardless of start.
- Reversibility (detailed balance) is the easiest path to proving a distribution is stationary.
- Think of transient states as "visited finitely often a.s." — the chain drifts away never to return.

## Anti-patterns

- **Forgetting aperiodicity**: An irreducible positive recurrent chain has a stationary distribution but may NOT converge (oscillates). Mixing requires aperiodicity too.
- **Confusing stationary distribution with limiting distribution**: They coincide for aperiodic chains; for periodic chains the limit doesn't exist in the usual sense.
- **Infinite state space**: Positive recurrence is NOT automatic — random walk on ℤ is recurrent but null recurrent (μi = ∞).

## Worked Example

**Wright-Fisher model** (§6.1.11): Population size N, Xn = number of copies of allele A. Transition:
pij = C(N,j)(i/N)^j(1-i/N)^(N-j). State space {0,...,N}. States 0 and N are absorbing (positive recurrent). All other states transient. Stationary distribution places all mass on absorbing states.

## Key Takeaways

1. n-step transition matrix = Pⁿ (Chapman-Kolmogorov). Long-run behavior computable from matrix powers.
2. Irreducible + positive recurrent → unique stationary distribution with πi = 1/μi.
3. Add aperiodicity → pij(n) → πj (convergence to stationarity).
4. Mixing time quantifies how fast convergence occurs; spectral gap controls exponential mixing rate.
5. MCMC builds a chain with desired πi as stationary distribution — correctness guaranteed by detailed balance.

## Connects To

- **Ch07**: Harmonic functions of a Markov chain yield martingales (ψ(Xn) is a martingale if Pψ = ψ).
- **Ch12**: Optional stopping theorem applied to Markov chain martingales computes absorption probabilities.
- **Ch10**: Return times of Markov chains form a renewal process.
- **Ch13**: Continuous-time Markov chains → diffusion processes in the limit.
