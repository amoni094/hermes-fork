---
name: harchol-balter-performance-modeling
description: Use when queueing, scheduling, or contention. M/G/1, SRPT
version: 1.0.0
author: Hermes Agent
license: MIT
triggers:
  - queueing theory / M/M/1 / M/G/1 analysis
  - SRPT, FCFS, PS, FB, SJF, LCFS scheduling
  - heavy-tail workloads, Pareto, Weibull, C² > 1
  - Little's Law, PASTA, Pollaczek-Khinchin
  - resource contention, utilisation bounds, tail latency
  - cron slot scheduling and job prioritisation
related_skills:
  - puterman-mdp
  - hermes-cron-and-agents
  - information-theory-for-agents
  - lattimore-bandit-algorithms
metadata:
  hermes:
    tags: [queueing, scheduling, performance, mg1, srpt, research]
    related_skills: [puterman-mdp, hermes-cron-and-agents, information-theory-for-agents]
---

# Performance Modeling and Design of Computer Systems
**Author**: Mor Harchol-Balter | **Year**: 2013 | **Pages**: 574 | **Chapters**: 33
**Source**: Cambridge, *Queueing Theory in Action*. Synthesized from the PDF; not a verbatim extract.

<!-- why: front-load decision rules so compaction cannot drop the scheduling toolkit -->

## When to Use

Load this skill to reason about concurrent load, scheduling policy choice, utilisation targets, or sojourn/tail latency. Do **not** use for MDP policy iteration (use `puterman-mdp`) or bandit exploration (use `lattimore-bandit-algorithms`).

**Load a chapter before answering** if the question is not covered in Core Frameworks below.

## Core Frameworks

### Little's Law (always first)

For any ergodic open system, no assumptions on arrivals, service, topology, or order:

```
E[N] = λ E[T]
```

Closed system (N = multiprogramming level, X = throughput):

```
N = X · E[T]
E[R] = N/X − E[Z]     # Response-Time Law; Z = think time
```

Apply to **any subsystem** (queue only, server only, disk+queue). Distribution-independent: only means.

**Brumelle / Generalized Little.** Higher-moment analogues of L=λW exist only under restrictive order (jobs leave in arrival order, e.g. single FCFS). Brumelle (1972) generalizes L=λW to H=λG (time-average cost = arrival rate × expected cost per customer). Do **not** write E[N²]=λ E[T²] in general. Distributional Little's Law holds for M/G/1 FCFS (Ch 26).

### Utilisation and stability

```
ρ = λ E[S] = λ/μ          # single server
stable iff ρ < 1
P(idle) = 1 − ρ            # work-conserving single server
```

M/M/1 mean number explodes after ρ ≈ 0.5–0.6; jump 0.8	o0.9 hurts more than 0.7	o0.8. **Target ρ < 0.7** for latency-sensitive single-server resources (WAL, lock, one-writer log). High C² makes even ρ=0.5 dangerous under FCFS.

### PASTA

Poisson Arrivals See Time Averages: a_n = p_n = d_n when arrivals are Poisson (one-at-a-time). Counterexample: deterministic/uniform interarrivals can have a_n ≠ p_n. Never sample occupancy only at arrivals unless PASTA applies.

### M/M/1 (Kendall: memoryless / memoryless / 1 server)

```
π_n = (1−ρ) ρ^n
E[N] = ρ/(1−ρ)
Var(N) = ρ/(1−ρ)²
E[T]  = 1/(μ−λ)
E[T_Q] = ρ/(μ−λ)
```

### M/G/1 FCFS — Pollaczek–Khinchin (tagged job + excess)

Inspection paradox: random observer sees excess Se of residual service,

```
E[S_e] = E[S²] / (2 E[S]) = (E[S]/2) (C_S² + 1)
C_S² = Var(S)/E[S]² = E[S²]/E[S]² − 1
```

P-K waiting time:

```
E[T_Q] = [ρ/(1−ρ)] · E[S_e] = λ E[S²] / (2(1−ρ))
E[T]   = E[S] + E[T_Q]
Var(T_Q) = (E[T_Q])² + λ E[S³] / (3(1−ρ))
```

ith moment of delay tracks (i+1)th moment of service. **If C_S² is huge, E[T_Q] is huge even at low ρ.** Example from the book: ρ=0.5, E[S]=1, C²=25 ⇒ E[T_Q]=13.

Doubling λ and μ does **not** preserve E[T] under M/G/1 FCFS (P-K is not linear that way) — check Ch 23 Ex 23.2.

### Work-conserving ≠ same E[T]

Work-conserving: always serve someone if work exists; never create work. Remaining **work** and **utilisation** are identical across work-conserving policies. **E[N] and E[T] are not** — serving shortest vs longest changes E[N], hence E[T] via Little.

### Scheduling decision (M/G/1, work-conserving)

| Policy | Size used? | Preempt? | Mean T vs C² | Use when |
|--------|------------|----------|--------------|----------|
| FCFS | no | no | blows up with C² | C²≤1, fairness of arrival order, non-preemptible |
| LCFS / RANDOM | no | no | same E[T] as FCFS; Var(T): FCFS < RANDOM < LCFS | LCFS worst tails |
| PS | no | yes | **insensitive** to C²; E[T]=E[S]/(1−ρ) like M/M/1 | unknown sizes, time-share one slot |
| P-LCFS | no | yes | same mean as PS | — |
| FB / LAS | age only | yes | good iff DFR (Pareto/Weibull α<1) | unknown size, heavy tail |
| SJF | original size | no | better at high ρ; still hurt by residual of a giant | known size, cannot preempt |
| PSJF | original size | yes | better than SJF | known size |
| **SRPT** | remaining | yes | **minimises mean sojourn on every sample path** | known remaining size |

**Trigger:** C² > 1 ⇒ abandon FCFS; prefer PS if sizes unknown, **SRPT if remaining size known**, FB if only age known and DFR.

C²=1 (exponential): FCFS and PS have the same E[T]. C²<1 (deterministic-ish): FCFS beats PS.

### SRPT formulas (size-x job)

ρ_x = λ ∫_0^x t f(t) dt  (load of jobs smaller than x)

```
E[T(x)] = E[Wait(x)] + E[Res(x)]
E[Wait(x)] = [λ ∫_0^x t² f(t) dt + λ x² (1−F(x))] / (2 (1−ρ_x)²)
E[Res(x)]  = ∫_0^x dt / (1−ρ_t)
```

Residence is **not** x/(1−ρ_x) (that is PSJF). Under SRPT priority **improves** as remaining time drops.

**All-Can-Win (fairness):** at ρ<1, under heavy-tailed Bounded Pareto, even Mr. Max (largest job) prefers SRPT to PS. No true starvation when ρ<1 (busy periods finite). Fear of starving large jobs is usually wrong for HT workloads.

**Slowdown** Slowdown = T/S ≥ 1. SRPT minimises mean T, **not** mean slowdown (Ex 2.3). PS gives E[Slowdown(x)] = 1/(1−ρ) for all x (fair). FB lowers slowdown of small jobs when DFR.

### SEPT (not named in the book; use with FB/SJF)

When **true size unknown**, Shortest Expected Processing Time (SEPT) / SERPT serve the job with smallest **expected** remaining time. For DFR, younger ⇒ smaller expected remaining ⇒ FB/LAS is the practical SEPT. For IFR, older jobs should run first (opposite of FB).

### Heavy tails

**Pareto(α)** for x≥1: P(X>x)=x^{-α}, 0<α<2. Failure rate r(x)=α/x (DFR). α≤1: infinite mean; 1<α≤2: finite mean, infinite variance. UNIX CPU lifetimes: α≈0.8–1.2.

**Bounded Pareto(k,p,α)** truncates both ends so all moments exist; still elephant/mice.

**Heavy-tail property:** largest ~1% of jobs hold most of the work (vs ~5% for Exponential).

**Weibull** F(x)=exp(-(x/λ)^α): α<1 ⇒ DFR, C² arbitrarily large. Book's policy plots use Weibull mean 1, C²=10, and ρ=0.7 slices.

Log-log CCDF linear ⇒ power law. Do not model computer jobs as Exponential without checking C².

### Transforms (sojourn distributions)

Laplace of continuous X: X~(s)=E[e^{-sX}]. Exponential(λ): λ/(λ+s). Moments by differentiating at 0 ("peeling the onion").

z-transform of discrete N: N^(z)=∑ π_i z^i. Poisson arrivals in time t: e^{-λt(1-z)}. Arrivals during service S: S~(λ(1-z)).

M/G/1 FCFS sojourn transform (Pollaczek–Khinchin transform):

```
T~(s) = S~(s) (1−ρ) s / [λ S~(s) − λ + s]
```

Cannot convert N↔T via Little except for means; use this transform for Var(T) and tails.

### Server farms

M/M/k: square-root staffing k* ≈ R + c√R, R=λ/μ. For P(queue)<0.2, c≈1. One fast server of speed s vs n of speed s/n: **the single fast machine wins** on mean T (no split of a job across slow cores unless PS/network effects).

M/G/1/PS: E[N], E[T] same as M/M/1 (insensitivity). BCMP: product-form networks of PS/Cox servers.

## Hermes applications

1. **Cron slot scheduling** — remaining-time known ⇒ **SRPT** (shortest remaining cron/job first) minimises mean sojourn. Do not FCFS a mixed bag of 2s healthchecks and 30min sweeps.
2. **Heavy-tail job detection** — measure C². **C²>1 ⇒ SRPT over FCFS** (or PS/FB if size unknown).
3. **WAL / single-writer contention** — model as M/G/1; hold **ρ<0.7**. If C² high, drop ρ further or isolate elephant writes.
4. **Skill router scoring** — many skills compete for one reasoning slot ⇒ **PS** (time-share) or **FB** if long-running skills should yield to new short ones. Not FCFS prompt stuffing.

## Chapter Index

| # | File | Key |
|---|------|-----|
| 1 | [ch01](chapters/ch01-motivating-examples.md) | why models beat voodoo constants |
| 2 | [ch02](chapters/ch02-queueing-terminology.md) | open/closed, ρ, throughput, slowdown |
| 3–5 | [ch03-05](chapters/ch03-05-probability-background.md) | expectation, LLN, time vs ensemble avg |
| 6 | [ch06](chapters/ch06-littles-law.md) | Little, forced flow, Brumelle |
| 7 | [ch07](chapters/ch07-modification-analysis.md) | closed-system what-if, asymptotic bounds |
| 8–10 | [ch08-10](chapters/ch08-10-markov-chains.md) | DTMC, ergodicity, z-transform chains |
| 11–12 | [ch11-12](chapters/ch11-12-exponential-ctmc.md) | memoryless, Poisson merge/split, CTMC |
| 13 | [ch13](chapters/ch13-mm1-pasta.md) | M/M/1, PASTA |
| 14–15 | [ch14-15](chapters/ch14-15-server-farms.md) | M/M/k, Erlang, square-root staffing |
| 16–19 | [ch16-19](chapters/ch16-19-networks.md) | Burke, Jackson, BCMP-prep, MVA |
| 20 | [ch20](chapters/ch20-heavy-tails.md) | Pareto, Bounded Pareto, DFR |
| 21–22 | [ch21-22](chapters/ch21-22-ph-ps-bcmp.md) | PH, matrix-analytic, PS insensitivity |
| 23 | [ch23](chapters/ch23-mg1-inspection.md) | Inspection paradox, P-K |
| 24 | [ch24](chapters/ch24-task-assignment.md) | server-farm task assignment |
| 25–26 | [ch25-26](chapters/ch25-26-transforms.md) | Laplace, z, M/G/1 T~(s) |
| 27 | [ch27](chapters/ch27-power-optimization.md) | busy period, setup cost |
| 28 | [ch28](chapters/ch28-performance-metrics.md) | T, T_Q, slowdown, work-conserving |
| 29–30 | [ch29-30](chapters/ch29-30-non-size-scheduling.md) | FCFS/LCFS/PS/FB |
| 31–32 | [ch31-32](chapters/ch31-32-size-based-scheduling.md) | priority, SJF, PSJF |
| 33 | [ch33](chapters/ch33-srpt-fairness.md) | SRPT, All-Can-Win |

## Topic Index

- **Brumelle / H=λG** → ch06
- **Busy period** → ch27, ch29
- **C² / SCV** → ch20, ch23, ch33
- **FB / LAS** → ch29-30, ch33
- **FCFS / LCFS** → ch29-30
- **Heavy tail / Pareto / Weibull** → ch20, ch33
- **Little's Law / PASTA** → ch06, ch13
- **M/G/1 / P-K** → ch23, ch25-26
- **M/M/1** → ch13
- **PS / insensitivity** → ch21-22, ch29-30
- **SEPT** → ch29-30, cheatsheet
- **Slowdown / tail latency** → ch28, ch33
- **SRPT** → ch33
- **Square-root staffing** → ch14-15
- **Transforms** → ch25-26
- **Utilisation ρ** → ch02, ch13, cheatsheet
- **Work-conserving** → ch28

## Supporting Files

- [glossary.md](glossary.md)
- [patterns.md](patterns.md)
- [cheatsheet.md](cheatsheet.md)

## Scope & Limits

Covers Harchol-Balter 2013 only. 17 PDF pages were image/blank (part dividers). SEPT is included as the size-unknown analogue; it is **not** a named chapter. Combine with live measurements of λ, E[S], C² before changing a scheduler.
