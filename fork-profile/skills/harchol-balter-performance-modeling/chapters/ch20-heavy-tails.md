# Ch 20 — Tales of Tails (Pareto, Heavy Tails)

**Use when**: workload C²≫1, log-log CCDF is linear, or deciding whether to migrate/kill long jobs.

## Measurement fact
UNIX process CPU lifetimes (Harchol-Balter, mid-90s): for jobs >1s,
```
P(size > x | size > 1) ≈ x^{-α}    α ∈ [0.8, 1.2], typically ≈ 1
```
Straight line on log-log CCDF. Exponential fit fails in the tail.

## Pareto(α), 0<α<2, x≥1
```
P(X>x) = x^{-α}
f(x) = α x^{-α-1}
r(x) = f/F̄ = α/x     # decreasing failure rate (DFR)
```
- α ≤ 1: E[X]=∞, all higher moments ∞, E[remaining | age=a]=∞
- 1 < α ≤ 2: finite mean, infinite variance
- α → 0 most variable / heaviest; α → 2 lightest in this family

α=1: P(life>b | life≥a) = a/b. Half of age-1 jobs reach age 2; P(age T reaches 2T)=1/2.

## Bounded Pareto(k, p, α)
Density truncated to [k,p] and renormalised. All moments finite; still elephant/mice and approximately DFR until the cap.

## Heavy-tail property ("elephants and mice")
Largest ~1% of jobs comprise **most** of the work. Exponential with same mean: largest 1% ≈ 5% of work. Implication: migrate/isolate/SRPT-prioritise a tiny fraction of jobs.

## DFR vs Exponential wisdom
Exponential: remaining life independent of age ⇒ migrate only newborns (cheap). Pareto DFR: older ⇒ stochastically longer remaining ⇒ **active migration of old jobs can pay**, amortising state-transfer over a long residual. Criterion used expected *slowdown*, not T (avoids infinities when α≤1).

## Elsewhere
Web file sizes α≈1.1 (Crovella/Bestavros); Internet node degree (Faloutsos); IP flow packet counts (Rexford et al.). Assume computer workloads are HT until measured otherwise.

## Weibull (used in Ch 33 plots)
```
F̄(x) = exp(−(x/λ)^α)
```
α<1 ⇒ DFR, C² arbitrarily large. Book plots: mean 1, C²=10 vs ρ; and ρ=0.7 vs C².

## Hermes trigger
Estimate C² from recent job durations. **C²>1 ⇒ do not FCFS.** Pair with SRPT/FB (see cheatsheet).
