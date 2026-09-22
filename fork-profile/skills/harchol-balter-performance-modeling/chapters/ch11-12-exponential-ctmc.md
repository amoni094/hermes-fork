# Ch 11–12 — Exponential, Poisson, CTMC

**Use when**: justifying memoryless service, merging streams, or writing CTMC balance.

## Exponential(μ)
f(t)=μ e^{-μt}, E[S]=1/μ, C²=1. Memoryless: P(S>t+s | S>s)=P(S>t). Remaining time of a running exponential job is still Exp(μ) — this is why M/M/1 is a CTMC on count only.

Min of independent Exp(μ_i) is Exp(∑μ_i); the argmin is μ_k/∑μ_i.

## Poisson process rate λ
N(t)~Poisson(λt); interarrivals Exp(λ).
- Merge independent Poissons: Poisson(∑λ_i)
- Split: each arrival routed with p independently ⇒ Poisson(pλ)
- Uniformity: given N(t)=n, arrival epochs ~ n i.i.d. Unif(0,t)

## CTMC
Spend Exp(q_i) in i, jump i→j with q_{ij}/q_i. Global balance: π Q = 0. Birth-death: local balance π_i λ_i = π_{i+1} μ_{i+1}.
