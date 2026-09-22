# Ch 29–30 — FCFS, LCFS, PS, P-LCFS, FB (no true size)

**Use when**: size unknown, or policy must not look at size.

## Non-preemptive, size-blind (Ch 29)
FCFS, LCFS, RANDOM: **same E[T] and same law of N** (embedded argument does not use order). They are **not** equal in Var(T):
```
Var(T_FCFS) < Var(T_RANDOM) < Var(T_LCFS)
```
LCFS wait = busy period started by excess S_e (new arrivals jump ahead). Heavy tails make LCFS sojourn catastrophic.

## Processor-Sharing (Ch 30)
Time-share equally. Insensitive:
```
E[T] = E[S]/(1−ρ)           # = M/M/1, any G
E[T(x)] = x/(1−ρ)
E[Slowdown(x)] = 1/(1−ρ)
```
PS beats FCFS on E[T] **iff C_G² > 1**. Not better on every sample path (two equal jobs: FCFS wins).

Ages of all jobs seen by an arrival ~ i.i.d. equilibrium.

## Preemptive LCFS
Same mean T as PS (another insensitive policy). Different sojourn *path*.

## FB / LAS (Foreground-Background, Least-Attained-Service)
Always run the job(s) of **lowest age** (PS among ties). UNIX MLPS is a finite-level approximation.

Rationale: under **DFR** (Pareto, Weibull α<1), low age ⇒ smaller expected remaining ⇒ FB ≈ SEPT without knowing size. Under IFR, FB is wrong.

```
E[Slowdown(x)]_{PS} = 1/(1−ρ)     # flat in x
FB: smaller x get better slowdown when DFR
```

E[T(x)]^{FB} uses truncated size S_x (mass above x piled at x):
```
E[T(x)]^{FB} = [x(1−ρ_x) + (λ/2) E[S_x²]] / (1−ρ_x)²
```
with ρ_x = λ E[min(S,x)]. SRPT dominates FB for every x (Ch 33).

## SEPT (not a book name; the size-unknown cousin)
SEPT = serve smallest **expected** remaining processing time. SERPT = preemptive version.
- DFR: younger jobs win ⇒ implement SEPT as **FB/LAS**
- IFR: older jobs win (opposite)
- Known size: SEPT degenerates to SJF/SRPT

Hermes skill router with unknown runtimes: **PS** (fair, C²-immune mean) or **FB** (bias to new short skills) rather than FCFS.
