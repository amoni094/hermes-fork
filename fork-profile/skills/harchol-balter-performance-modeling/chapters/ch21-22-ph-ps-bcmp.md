# Ch 21–22 — Phase-Type, Matrix-Analytic, PS / BCMP

**Use when**: fitting a general distribution with exponentials, or a time-sharing (PS) server farm.

## Phase-type (PH)
Any distribution on [0,∞) can be approximated by a CTMC absorbing time (Coxian, hyperexponential H2, Erlang). H2 (two-phase hyperexponential) matches high C² with a "mice/elephant" mixture — the right first model of HT jobs.

SCV: C_X² = Var(X)/E[X]². Hyperexponential: C²>1; Erlang-k: C²=1/k<1.

## Matrix-analytic
QBD (quasi-birth-death) for M/PH/1 or time-varying load: repeating levels, rate matrix R, π_{i+1}=π_i R. Use when load fluctuates (day/night λ) and you need numerical π, not a closed form.

## Processor-Sharing M/G/1/PS
Quantum → 0 round-robin. **Insensitivity:**
```
P(N=n) = (1−ρ) ρ^n          # same as M/M/1, any Coxian G
E[N] = ρ/(1−ρ)
E[T] = E[S]/(1−ρ)
E[T(x)] = x/(1−ρ)
E[Slowdown(x)] = 1/(1−ρ)    # fair across sizes
```
Mean T does **not** grow with C². PS beats FCFS iff C_G² > 1.

Ages seen by an arrival are i.i.d. equilibrium/excess (inspection paradox on every job).

## BCMP
Product-form networks if each station is FCFS-exponential, or PS / LCFS-preemptive / infinite-server with general service. Tandem of M/G/1/PS servers: each still looks M/M/1-like in occupancy.

Hermes skill router: one reasoning slot shared by many skills ≈ **PS**. Insensitive to heavy-tailed skill runtimes for *mean occupancy*. Unfairness of FCFS stuffing is the failure mode.
