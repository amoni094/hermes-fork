# Ch 6 — Little's Law and Operational Laws

**Use when**: converting occupancy ↔ sojourn, or applying forced-flow / device-demand.

## Open
```
E[N] = λ E[T]     # any ergodic open system
```
No assumptions on arrivals, service law, topology, or scheduling.
Also E[N_Q]=λ E[T_Q], E[N_service]=λ E[S]=ρ.

## Closed
```
N = X · E[T]
E[R] = N/X − E[Z]     # Response-Time Law
```

## Generalized Little / Brumelle
You **cannot** in general relate E[N²] to E[T²]. Higher-moment analogues (Brumelle 1972, Bertsimas–Nakazato) need jobs to leave in arrival order (FCFS single queue).

**Brumelle's formula** H=λG: time-average cost rate H equals arrival rate times expected cost G per customer. L=λW is cost=1 while present. Use for cost accounting, not as a free variance converter.

Distributional Little's Law (FCFS M/G/1, Ch 26): number left by a departure ~ Poisson arrivals during T, so N^(z)=T~(λ(1−z)).

## Forced Flow Law
V_i = mean visits to device i per job:
```
X_i = X · V_i
D_i = V_i E[S_i]
```
Bottleneck = argmax D_i. Asymptotic throughput ≤ 1/D_bottleneck.

## Hermes
Count in-flight jobs N̂, measure completion rate X̂, infer E[T]≈N̂/X̂ without start timestamps.
