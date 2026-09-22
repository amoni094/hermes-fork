# Ch 2 — Queueing Theory Terminology

**Use when**: defining open vs closed, load ρ, throughput, slowdown.

## Single-server network
Jobs arrive, wait in a buffer, occupy a server for service time S, then depart. Response time T = T_Q + S (queue wait + service).

## Kendall notation
`A/S/k[/K][/policy]`: arrival law / service law / servers [/capacity] [/discipline].
- M = memoryless (exponential / Poisson)
- G = general
- D = deterministic
Absence of 4th field: infinite buffer, FCFS.

## Open vs closed
- **Open**: external Poisson (or other) arrivals; throughput X = λ in stability.
- **Closed**: fixed N jobs (interactive terminals + think time Z, or batch). Throughput X determined by the system.

Interactive: N = X (E[R] + E[Z]). Batch: think time 0.

## Metrics
```
ρ = λ E[S]                 # utilisation; work-conserving single server busy fraction
X = throughput             # completions per time
E[T]  sojourn / response
E[T_Q] wait in queue
E[N], E[N_Q]
Slowdown(j) = T(j) / S(j) ≥ 1
```

Stability of a single server: ρ < 1. If ρ ≥ 1 the queue grows without bound (open).

## Open vs closed modeling trap
A closed model with large N looks open locally, but *what-if* (faster CPU) behaves differently: closed systems re-circulate, so speeding one device can move the bottleneck. Always ask whether the workload is a closed user population.
