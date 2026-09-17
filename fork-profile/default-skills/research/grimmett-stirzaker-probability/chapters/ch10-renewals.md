# Chapter 10: Renewals

## Core Idea
A renewal process models a sequence of i.i.d. waiting times between events. The renewal equation and its limit theorems give the long-run rate of events and the asymptotic distribution of "time until next event," directly applicable to cache refresh, retry scheduling, and regenerative systems.

## Frameworks Introduced

- **Renewal process N(t)**: Interarrival times X₁, X₂, … iid with distribution F, mean μ = E(X₁).
  N(t) = max{n: X₁+…+Xn ≤ t} = number of renewals by time t.

- **Renewal function m(t) = E[N(t)]**: Satisfies the renewal equation:
  m(t) = F(t) + ∫₀ᵗ m(t−x) dF(x)

- **Elementary renewal theorem**: m(t)/t → 1/μ as t → ∞.

- **Key renewal theorem (§10.2.7)**: For non-arithmetic F and integrable h:
  ∫₀ᵗ h(t−x) dm(x) → (1/μ) ∫₀^∞ h(x) dx  as t → ∞.

- **Excess lifetime E(t)** (§10.3): Time until next renewal after t. As t → ∞:
  P(E(t) > x) → (1/μ) ∫_x^∞ (1−F(y)) dy.
  The limiting mean excess = E(X₁²)/(2μ) — larger for heavy-tailed X₁.

- **Renewal-reward processes (§10.5)**: Reward Rn at nth renewal. Long-run reward rate = E(Rn)/μ (provided E|Rn| < ∞).

- **Alternating renewal process**: Machine alternates between working (Zi) and repair (Yi) periods. P(working at t) → E(Z)/(E(Z)+E(Y)) as t → ∞.

## Key Concepts

- **Renewal** — each event "starts fresh"; return times of Markov chains form a renewal process
- **Renewal equation** — Fredholm equation relating m(t) to F; solved by convolution
- **Non-arithmetic distribution** — span 0 (continuous) or aperiodic discrete; needed for key renewal theorem
- **Excess lifetime** — time from t to next renewal; has limiting distribution (1−F(x))/μ
- **Inspection paradox** — interval containing a fixed time t is longer in distribution than a typical interval (size-biased sampling)
- **Superposition of renewals** — sum of independent renewal processes is renewal iff both are Poisson

## Mental Models

- Rate = 1/mean: in steady state, events arrive at rate 1/μ regardless of distribution shape.
- Inspection paradox: at a random time t you fall in the middle of a long interval — so the observed interval is biased toward longer ones. Mean observed interval = E(X²)/E(X) ≥ E(X).
- Renewal as regeneration: any process that "restarts" at renewal epochs inherits renewal limit theorems.

## Anti-patterns

- **Arithmetic distributions**: Key renewal theorem fails for arithmetic distributions without the lattice version. Always check span.
- **Ignoring inspection paradox**: The limiting excess lifetime does NOT have the same distribution as X₁. Its mean is E(X₁²)/(2μ), not μ/2.

## Worked Example

**Cache refresh scheduling**: Model cache TTL as i.i.d. exponential(λ). N(t) = Poisson(λt). Mean time between refreshes = 1/λ. Excess lifetime at time t = Exp(λ) (memoryless property). For non-exponential TTL distribution with mean μ and variance σ², steady-state expected wait until next refresh = (μ² + σ²)/(2μ) — smaller variance → smaller expected wait.

## Key Takeaways

1. Elementary renewal theorem: E[N(t)]/t → 1/μ. Long-run rate depends only on mean interarrival time.
2. Key renewal theorem: asymptotic averages of renewal integrals computable from F alone.
3. Inspection paradox: at steady state, the interval containing a fixed time has mean E(X²)/E(X) ≥ E(X).
4. Renewal-reward: long-run reward rate = E(reward per cycle)/E(cycle length).
5. Alternating renewal: availability → E(Z)/(E(Y)+E(Z)) regardless of distributions (beyond means).

## Connects To

- **Ch06**: Return times of Markov chains are i.i.d. → form a renewal process. Limit theorem for Markov chains uses renewal theory.
- **Ch12**: Wald's equation E(ST) = μ·E(T) is the martingale version of the renewal-reward theorem.
- **Ch11**: Queues analyzed via renewal theory (busy/idle cycles).
