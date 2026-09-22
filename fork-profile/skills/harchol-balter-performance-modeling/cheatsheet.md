# Cheatsheet — Formulas and Hermes Mapping

## Hermes (read this first)

| Problem | Model | Action |
|---------|-------|--------|
| Cron slot packing | M/G/1, remaining known | **SRPT** minimises mean sojourn |
| Heavy-tail jobs | measure C² | **C²>1 ⇒ SRPT over FCFS** (PS/FB if size unknown) |
| WAL / write lock | M/G/1 | hold **ρ<0.7**; if C² high, isolate elephants |
| Skill router, one reasoning slot | **PS** (or FB if DFR/age) | all skills time-share; do not FCFS |

## Little / Brumelle / PASTA
```
E[N] = λ E[T]                 # open, any ergodic system
N    = X E[T]                 # closed
E[R] = N/X − E[Z]             # closed interactive
H    = λ G                    # Brumelle; L=λW is the occupancy case
a_n  = p_n                    # PASTA iff Poisson arrivals
```

## Utilisation
```
ρ = λ E[S] = λ/μ              # single server; need ρ<1
P(idle) = 1−ρ                 # work-conserving
Target ρ<0.7 for latency-critical M/G/1
M/M/1: E[N]=ρ/(1−ρ)  (knee after ~0.5–0.6; 0.8→0.9 hurts more than 0.7→0.8)
```

## M/M/1
```
π_n=(1−ρ)ρ^n
E[N]=ρ/(1−ρ)     Var(N)=ρ/(1−ρ)²
E[T]=1/(μ−λ)=E[S]/(1−ρ)
E[T_Q]=ρ/(μ−λ)
```

## M/G/1 FCFS (P-K)
```
C_S² = Var(S)/E[S]²
E[S_e] = E[S²]/(2E[S]) = (E[S]/2)(C²+1)
E[T_Q] = λ E[S²] / (2(1−ρ)) = [ρ/(1−ρ)](E[S]/2)(C²+1)
E[T]   = E[S] + E[T_Q]
Var(T_Q) = (E[T_Q])² + λ E[S³]/(3(1−ρ))
```
ρ=0.5, E[S]=1, C²=25 ⇒ E[T_Q]=13. High C² poisons FCFS at "low" load.

## M/G/1 transforms
```
N^(z) = S~(λ−λz)(1−ρ)(1−z) / [S~(λ−λz) − z]
T~(s) = S~(s)(1−ρ)s / (λ S~(s) − λ + s)
Exp(μ)~ : μ/(μ+s)
A_S^(z) = S~(λ(1−z))
```

## PS (insensitive)
```
E[T]=E[S]/(1−ρ)     E[T(x)]=x/(1−ρ)     E[Slowdown(x)]=1/(1−ρ)
beats FCFS on mean T  iff  C²>1
```

## SRPT (size x)
```
ρ_x = λ ∫_0^x t f(t) dt
E[Wait(x)] = [λ∫_0^x t²f(t)dt + λ x²(1−F(x))] / [2(1−ρ_x)²]
E[Res(x)]  = ∫_0^x dt/(1−ρ_t)
E[T(x)]    = Wait + Res
```
Minimises mean T on every sample path. Does not minimise mean slowdown. All-Can-Win vs PS under HT.

## FB / LAS (unknown size, DFR)
```
E[T(x)] = [x(1−ρ_x) + (λ/2)E[S_x²]] / (1−ρ_x)²
```
S_x = min(S,x). SEPT ≈ FB when DFR.

## Priority NP (class k, 1=highest)
```
E[T_Q(k)] = (λ E[S²]/2) / [(1−∑_{i<k}ρ_i)(1−∑_{i≤k}ρ_i)]
```

## Policy rank (high C², preempt OK)
SRPT < PSJF < FB < PS=PLCFS < SJF < FCFS   (mean T)
Var among size-blind NP: FCFS < RANDOM < LCFS

## Heavy tails
```
Pareto(α): P(X>x)=x^{-α} (x≥1, 0<α<2), r(x)=α/x DFR
α≤1 infinite mean; 1<α≤2 infinite var
Weibull α<1: DFR, C² free
Elephants: top ~1% of jobs ≈ most of the work
```

## Square-root staffing (M/M/k)
```
k* ≈ R + c√R ,  R=λ/μ
α=P_Q : 0.8→c≈0.17; 0.5→0.51; 0.2→1.06; 0.1→1.42
```

## Work-conserving
Same remaining work and ρ; **not** same E[T]. Never idle with a queue; never manufacture work.

## Slowdown
Slowdown=T/S≥1. PS fair. SRPT not slowdown-optimal. Prefer slowdown when sizes span decades.
