# Ch 16–19 — Burke, Jackson, Classed & Closed Networks

**Use when**: jobs visit multiple devices (CPU→disk→CPU) or a closed think-loop.

## Burke
In M/M/1 FCFS, the departure process is Poisson(λ), and the number left behind is independent of past departures. Tandem M/M/1s therefore have product-form: each node looks like an independent M/M/1 with its own ρ_i (arrivals are Poisson into each).

## Jackson open networks
Poisson external arrivals, exponential servers, probabilistic routing. Traffic equations:
```
λ_j = λ_j^{ext} + ∑_i λ_i p_{ij}
```
Product form π(n) = ∏ (1−ρ_j) ρ_j^{n_j} with ρ_j=λ_j/μ_j < 1 all j. Local balance, not just global.

## Classed Jackson (Ch 18)
Multiple job classes with class-dependent routing (ATM, CPU-bound vs I/O-bound). Still product form. Use classes when two populations share a server at different rates.

## Closed networks (Ch 19)
Gordon–Newell product form, but the normalising constant is painful. **Mean Value Analysis (MVA)**: Arrival Theorem — a job arriving to a queue in a closed network of N jobs sees the mean occupancy of the N−1 system. Iterate E[T_i(n)], X(n) from n=1..N.

Hermes: a tool pipeline (search→read→write) is a Jackson tandem if each stage is exponential/PS; use product form rather than one giant M/G/1.
