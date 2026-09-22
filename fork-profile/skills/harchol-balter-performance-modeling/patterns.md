# Patterns — Queueing Decisions in Live Systems

## P1 — Four-tuple before any policy change
Write (λ, E[S], C², preemptible/size-known). Missing C² is the usual bug: people pick FCFS because it "feels fair" while C²=20.

## P2 — Single-writer / lock / WAL = M/G/1
One resource that jobs hold exclusively. Use P-K if FCFS. Cap ρ<0.7. If C²>1 and preemption/batching possible, SRPT or isolate elephants. If not preemptible, SITA-style: don't put huge dumps on the same FCFS WAL as tiny commits.

## P3 — C² trigger
```
C² < 1  → FCFS is fine (even better than PS on mean T)
C² = 1  → FCFS and PS same mean (exponential)
C² > 1  → never FCFS if you can PS/FB/SRPT
C² ≫ 1 → SRPT if remaining known; FB if DFR+age only; PS if you need fairness
```

## P4 — Cron / batch slot = SRPT
Jobs with known last-run duration: schedule shortest remaining first. A 30min sweep must not block a 2s healthcheck. ρ<1 ⇒ the sweep still finishes (no starvation). HT ⇒ even the sweep often prefers SRPT to PS.

## P5 — Skill / reasoning slot = PS (or FB)
Many skills compete for one generation. FCFS prompt stuffing lets one elephant skill freeze mice. PS: time-share the slot (round-robin tools). FB: new short skills outrank a long-running skill that has already burned tokens (DFR-like: long-running ⇒ likely even longer).

## P6 — Don't shard a FCFS queue
One fast server beats k slow FCFS servers of equal total speed. If you must shard FCFS, isolate size classes (SITA). PS/SRPT farms can use JSQ/random.

## P7 — Staffing a worker pool
M/M/k: k ≈ R + √R for ~20% queueing probability (R=λ/μ). Linear "one worker per job" overbuilds; k=R underbuilds (P_Q→1).

## P8 — Closed vs open what-if
Interactive loop with think time Z is closed. Speeding a non-bottleneck does nothing. Open: P-K still sees C². Doubling λ and μ does not freeze E[T] under M/G/1 FCFS.

## P9 — Tail ≠ mean
Same E[T] for FCFS/RANDOM/LCFS (size-blind NP) but Var(T) climbs LCFS-ward. For SLOs use T~(s) or E[S³]. LCFS is forbidden for latency SLOs.

## P10 — Work-conserving conservation is not fairness
Remaining work is policy-invariant among work-conserving schedulers. E[T] is not. "Conservation laws say we cannot help mice without hurting elephants" is the misreading Ch 1/28/33 exist to kill — All-Can-Win.

## P11 — Power/setup
ON/OFF adds a setup busy period. Latency-critical always-on (ON/IDLE) unless idle gaps ≫ setup.

## P12 — Measure, then model
Estimate λ from completion log, E[S] and C² from durations, ρ=λE[S]. If ρ≥1, no scheduler saves you — shed load. If ρ<1 and T is bad, the scheduler (or C²) is the bug.
