# Ch 6 — Markov Chains and Random Walks

## 2-SAT via random walk (Ch 6.1)

From an assignment, pick a violated clause, flip a random literal. Distance to a fixed satisfying assignment is a walk on `{0,…,n}` with a drift toward 0. Expected hitting time `O(n²)`. Monte Carlo: run `O(n²)` steps; amplify.

## Markov chains (Ch 6.2)

State space `Ω`, transition `P`. Irreducible + aperiodic ⇒ unique stationary `π`, `π P = π`. Reversible iff `π_i P_{ij} = π_j P_{ji}` (detailed balance).

Mixing: `Δ(t) = max_x ‖P^t(x,·) − π‖_{TV} → 0`. Relaxation time `1/(1−λ_*)` where `λ_*` is the second-largest eigenvalue modulus.

## Random walks on graphs (Ch 6.3–6.5)

Simple random walk on undirected `G=(V,E)`, `|V|=n`, `|E|=m`: `P_{uv}=1/d(u)` for `uv∈E`. Stationary `π_v = d(v)/(2m)`.

- **Hitting time** `h_{st} = E[time to t from s]`.
- **Cover time** `C_G = max_s E[time to visit all vertices from s]`.
- **Commuting time** `h_{st} + h_{ts}`.

**Electrical networks (Ch 6.4).** Resistance `R_{st}` of unit resistors on edges:

`h_{st} + h_{ts} = 2m R_{st}`.

**Cover times (Ch 6.5).** `C_G ≤ 2m(n−1)` (Aleliunas–Karp–Lipton–Lovász–Rackoff). Hence `O(n³)` cover on simple graphs. Markov inequality: a walk of length `2 C_G` covers with probability `≥ 1/2`; amplify.

## Graph connectivity (Ch 6.6)

Undirected `s`–`t` connectivity in **RL** (random log-space): walk `O(n³)` steps from `s`; accept if `t` is hit. Reingold’s deterministic log-space algorithm is later (2005); Motwani gives the randomised algorithm.

## Expanders and rapid mixing (Ch 6.7)

Expansion `h(G) = min_{|S|≤n/2} |∂S|/|S|`. Cheeger: `h²/2 ≤ 1−λ₂ ≤ 2h`. Large expansion ⇒ `λ₂` bounded away from 1 ⇒ rapid mixing, `t_mix = O(log n)`.

## Probability amplification by expander walks (Ch 6.8)

Standard amplification of a BPP/RP algorithm with error `1/2` needs `k` independent runs = `k` blocks of random bits.

Expander walk: one random start vertex + `k` random neighbours on an expander whose vertices are seeds. Error drops exponentially in `k` while extra bits are `O(k)` (edge labels), not `O(k · seed length)`.

Pairs with the concentrators of Thm 5.7.

## Hermes

- 2-SAT-style local search: expected `O(n²)` flips; timeout via Markov on hitting time.
- “Has this graph/component been fully explored”: cover time `≤ 2m(n−1)`, then Markov.
- Amplify a Monte Carlo skill-router with few random bits: expander walk, not `k` independent seeds.
