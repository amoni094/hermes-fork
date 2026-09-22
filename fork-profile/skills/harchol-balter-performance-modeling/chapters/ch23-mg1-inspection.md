# Ch 23 — M/G/1 and the Inspection Paradox

**Use when**: Poisson arrivals, general service, FCFS (or any non-preemptive size-blind policy) — the default WAL/lock model.

## Inspection paradox / excess
Random arrival into a renewal process of intervals S lands in a long interval. Excess (residual) S_e:
```
E[S_e] = E[S²] / (2 E[S]) = (E[S]/2) (C_S² + 1)
```
Age has the same mean (and same law) as excess. Length-biased interval has mean E[S²]/E[S].

If C²=1 (exponential), E[S_e]=E[S] (memoryless). If C²≫1, excess explodes — you "always just miss the bus."

## Tagged-job M/G/1/FCFS
An arrival waits for: residual of the job in service (if busy) + full service of those found in queue. PASTA + remaining-work:
```
E[T_Q] = ρ/(1−ρ) · E[S_e]
```

## Pollaczek–Khinchin (three forms)
```
E[T_Q] = [ρ/(1−ρ)] · E[S²]/(2 E[S])
E[T_Q] = [ρ/(1−ρ)] · (E[S]/2) · (C_S² + 1)
E[T_Q] = λ E[S²] / (2(1−ρ))
E[T]   = E[S] + E[T_Q]
```

Why C² matters: delay is **bunching**. D/D/1: no wait. M/D/1: arrival bunching. M/M/1: plus service variability. M/G/1 high C²: rare elephants freeze the queue.

**Very important:** E[T_Q] can be huge at low ρ if C² is huge. ρ=0.5, E[S]=1, C²=25 ⇒ E[T_Q]=13.

Variance (from transform, Ch 26):
```
Var(T_Q) = (E[T_Q])² + λ E[S³] / (3(1−ρ))
```
ith moment of delay ↔ (i+1)th moment of service. Tail latency tracks E[S³], not just C².

## Hermes WAL
Model the write lock as M/G/1. Measure C² of write bursts. Target ρ<0.7; if C² high, isolate elephants or drop ρ. Switching FCFS→SRPT/PS if preemptible is worth more than a small ρ cut.
