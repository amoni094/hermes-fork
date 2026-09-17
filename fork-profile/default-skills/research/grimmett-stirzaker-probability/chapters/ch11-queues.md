# Chapter 11: Queues

## Core Idea
Queueing theory models waiting systems using arrival and service processes. The M/M/1 queue (Poisson arrivals, exponential service) is the simplest tractable model. Key results: stability requires ρ = arrival_rate/service_rate < 1; mean queue length diverges as ρ → 1.

## Key Concepts
- **M/M/1 queue**: Poisson(λ) arrivals, Exp(μ) service, 1 server. Stable iff ρ = λ/μ < 1.
  Stationary distribution: πk = (1−ρ)ρk. Mean queue length = ρ/(1−ρ).
- **M/G/1 queue**: Poisson arrivals, general service distribution G with mean 1/μ and variance σ².
  Pollaczek-Khinchine formula: E[queue length] = ρ + ρ²(1+Cₛ²)/(2(1−ρ)) where Cₛ²=variance/mean².
- **Little's Law**: L = λW (mean customers in system = arrival rate × mean time in system). Always true.
- **G/G/1 heavy traffic**: as ρ→1, scaled queue length → reflected Brownian motion.
- **Networks of queues**: Jackson networks have product-form stationary distribution.
- **Utilization ρ** = λ/μ: must be < 1 for stability

## Key Takeaways
1. Stability requires ρ = λ/μ < 1. Mean waiting time diverges as ρ → 1 (heavy traffic).
2. Little's Law L = λW holds regardless of arrival/service distributions.
3. M/G/1: service variance increases mean queue length. High variance = worse performance.
4. Reflected Brownian motion approximates heavy-traffic queues — connects to Ch13.

## Connects To
- **Ch06**: M/M/1 is a birth-death Markov chain with stationary distribution computable from detailed balance.
- **Ch10**: M/G/1 analyzed via embedded renewal process at service completions.
- **Ch13**: Heavy traffic limit → reflected Brownian motion.
