# Ch 33 — SRPT and Fairness

**Use when**: remaining size is known (or well estimated) and preemption is legal.

## Definition
Always serve the job of **shortest remaining processing time**. A new arrival preempts iff its size < current remaining. Jobs present when j starts cannot overtake j (their remaining ≥ j's remaining).

**Sample-path optimality:** SRPT minimises mean sojourn on **every** arrival sequence (Ex 2.3). It does **not** minimise mean slowdown.

## M/G/1 mean sojourn of size x
```
E[T(x)]^{SRPT} = E[Wait(x)] + E[Res(x)]

E[Wait(x)] = [λ ∫_0^x t² f(t) dt + λ x² (1−F(x))] / [2 (1−ρ_x)²]

E[Res(x)]  = ∫_0^x dt / (1−ρ_t)

ρ_x = λ ∫_0^x t f(t) dt
```
Residence ≠ x/(1−ρ_x) (PSJF). Under SRPT the job's priority **improves** as remaining time falls, so each slice dt is delayed only by load of jobs smaller than current remaining t.

## Comparisons (book, Weibull mean 1, C²=10)
E[T] vs ρ: SRPT best, then PSJF, FB, PS=PLCFS, SJF, FCFS worst.
E[T] vs C² at ρ=0.7: PS=PLCFS **flat** (insensitive); FCFS linear-ish in C²; SRPT almost flat and lowest.
FB needs DFR (high C²); at low C² FB can lose to PS.

SRPT ≤ FB for every x (proved by comparing wait and residence).

## Fairness / All-Can-Win
Objection: SRPT starves giants. At ρ<1 busy periods are finite — no actual starvation.

Vs PS (the "fair" baseline, equal slowdown): for Bounded Pareto (k=332, p=10^{10}, α=1.1) at ρ=0.9, **even Mr. Max (size 10^{10}) prefers SRPT to PS**. ~99.9999% of jobs prefer SRPT by >2×; 99% by >5×. Slowdown at 90th percentile: SRPT 1.28 vs PS 10.

Theorem (All-Can-Win, Wierman/Harchol-Balter): under typical HT loads ρ not too close to 1, every job size x has E[T(x)]^{SRPT} ≤ E[T(x)]^{PS}. The "SRPT is unfair to large jobs" slogan is false for the workloads this book cares about.

## Implementation note
Static web GETs: size = file length, SRPT on outgoing bandwidth is implementable (Apache/Linux). CPU time-sharing defaults to PS out of fear, not optimality.

## Hermes
Cron with known/estimated remaining (progress bars, last-run duration): **SRPT the slot**. Do not FCFS a 30min sweep ahead of a 2s healthcheck. Large nightly jobs still finish; they are not starved at ρ<1, and under HT they often beat PS too.
