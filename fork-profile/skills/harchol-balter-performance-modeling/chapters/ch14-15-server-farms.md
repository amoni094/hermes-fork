# Ch 14–15 — M/M/k, Loss, Square-Root Staffing

**Use when**: sizing a pool of identical servers (agent workers, GPU replicas).

## M/M/k/k (Erlang-B loss)
k servers, no extra buffer: arrival that finds all busy is lost. Time-reversible CTMC. Blocking P_block = Erlang-B(R,k), R=λ/μ.

## M/M/k (Erlang-C)
Infinite queue, k servers. P_Q = P(wait>0). Mean wait
```
E[T_Q] = P_Q · (1/μ) / (k(1−ρ))     # ρ=λ/(kμ)
E[T] = E[S] + E[T_Q]
```
Three organisations (same total capacity): (1) one M/M/1 of speed kμ, (2) M/M/k of speed μ, (3) k separate M/M/1 with random split. **(1) best, (3) worst** for E[T]. Don't shard a FCFS queue unless you must.

## Square-root staffing (Thm 15.2)
Want P_Q < α, R=λ/μ large:
```
k* ≈ R + c √R
c Φ(c)/φ(c) = (1−α)/α
```
Rule of thumb: α=0.2 ⇒ c≈1.06 ≈ 1, so k ≈ R + √R. Other c: α=0.8 → 0.17; 0.5 → 0.51; 0.1 → 1.42.

Approximation is accurate even for small R (off by at most 1).

## Hermes
N parallel subagents: provision R + √R, not "one per task." Idle capacity of order √R is the price of a queueing probability ~20%.
