# Ch 13 — M/M/1 and PASTA

**Use when**: first-cut single-server model with Poisson arrivals and exponential service.

## M/M/1
Kendall: Poisson arrivals, Exp service, 1 server, infinite buffer, FCFS by default. CTMC is birth-death with rates λ, μ. Load ρ=λ/μ < 1 for stability.

```
π_n = (1−ρ) ρ^n
π_0 = 1−ρ
E[N] = ρ/(1−ρ)
Var(N) = ρ/(1−ρ)²
E[T] = 1/(μ−λ) = E[S]/(1−ρ)
E[T_Q] = ρ/(μ−λ)
```

E[N] is almost flat for ρ≲0.5–0.6, then vertical. Increasing ρ from 0.8 to 0.9 hurts far more than 0.7 to 0.8.

## PASTA — Poisson Arrivals See Time Averages
Let p_n = time-average P(N=n), a_n = fraction of arrivals that see n, d_n = fraction of departures that leave n.

- a_n = d_n if one-at-a-time arrivals and services
- a_n = p_n **if arrivals are Poisson** (PASTA)
- Counterexample: Unif(1,2) interarrival, deterministic service 1 ⇒ every arrival sees empty (a_0=1) but p_0 < 1

Do not estimate occupancy from arrival snapshots unless the arrival process is Poisson (or you correct for inspection bias).

## Hermes
WAL / lock / single-threaded writer: start with M/M/1. If measured C²>1, upgrade to M/G/1 FCFS (P-K) or change discipline.
