# Ch 28 — Performance Metrics

**Use when**: choosing what to optimise (mean T vs slowdown vs tail vs fairness).

## Traditional
```
E[T]     sojourn / response / time in system
E[T_Q]   wait = E[T]−E[S]     # "100× better wait" may barely move T if E[S]≫E[T_Q]
E[N], E[N_Q]
```
Always convert wait improvements into T using E[S].

## Work in system vs utilisation
Work remaining and device utilisation are identical for all **work-conserving** policies:
- always serve *some* job when work exists
- never create extra work (no re-run, no idle-while-queue)

They do **not** share E[T]. Shortest-first vs longest-first: same work process, different E[N] ⇒ different E[T] by Little.

## Slowdown
```
Slowdown = T/S ≥ 1
```
Preferable when job sizes span orders of magnitude: a 1s job delayed 10s is a disaster; a 1000s job delayed 10s is not. Mean slowdown is **not** minimised by SRPT (Ex 2.3).

PS: E[Slowdown(x)]=1/(1−ρ) for every x (fair). FB aims to reduce slowdown of small jobs under DFR.

## Tails / today's metrics
Var(T), P(T>x), SLA percentiles. FCFS/LCFS: same mean T among size-blind non-preemptive, but **Var(T): FCFS < RANDOM < LCFS**. LCFS is the tail villain.

Starvation/fairness: compare E[T(x)] or E[Slowdown(x)] across x, against PS as the fairness baseline.

## Deriving metrics
Usually derive E[T(x)] (sojourn of a job of size x) then uncondition: E[T]=∫ E[T(x)] f(x) dx. Little then gives E[N].
