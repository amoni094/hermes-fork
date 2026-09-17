# Chapter 16: Information Theory and Portfolio Theory

## Core Idea
A stock-market vector X of relative price relatives, and a portfolio b in the simplex, produce wealth S=b^T X. The log-optimal (growth-optimal, Kelly) portfolio maximizes W(b,F)=E log(b^T X) and is competitively and asymptotically optimal. Side information raises growth by at most I(X;Y). Universal portfolios achieve the best constant-rebalanced wealth to first order without knowing F. The Shannon–McMillan–Breiman theorem is the AEP for ergodic processes, including markets.

## Key Concepts
- **Market vector** X ∈ R_+^m : X_i = closing/opening price of stock i.
- **Portfolio** b ∈ B = {b≥0, ∑ b_j=1}: fraction of wealth in each stock, rebalanced each period.
- **Wealth**: S_n = ∏_{k=1}^n b_k^T X_k  (or with causal b_k(X^{k−1})).
- **Growth rate**: W(b,F)=E[log b^T X]. W^*(F)=max_b W(b,F).
- **Log-optimal / growth-optimal portfolio** b^*.
- **Causal / nonanticipating strategy**: b_i = b_i(X^{i−1}).
- **Universal portfolio** (Cover): b_{n+1} proportional to the integral of b · S_n(b) over the simplex (wealth-weighted average of constant-rebalanced portfolios).
- **SMB / general AEP**: −(1/n) log p(X^n) → H(X) a.s. for stationary ergodic processes.

## Frameworks and Methods
- **Kuhn–Tucker for W**: at b^*, E[X_i / (b^{*T} X)] ≤ 1, equality on stocks with b_i^*>0. This is the no-arbitrage-of-log-growth condition.
- **Asymptotics**: SLLN ⇒ (1/n) log S_n^* → W^*; any other causal strategy cannot beat this in expectation, and a.s. S_n / S_n^* → 0 if W(b)<W^*.
- **Information bound**: using the wrong density g instead of f costs at most D(f||g) in growth; side information Y yields ΔW ≤ I(X;Y).
- **Universal**: mix all constant-rebalanced b’s with a Dirichlet prior on the simplex; the mixture tracks the best b in hindsight at cost ~ ((m−1)/2) log n.
- **Sandwich proof of SMB**: bound −log p(X^n) between entropy-rate sandwich processes (Algoet–Cover).

## Key Results and Theorems

**Theorem 16.1.1.** For i.i.d. X_k ~ F, S_n^* = ∏ b^{*T} X_k satisfies (1/n) log S_n^* → W^* a.s.

**Lemma 16.1.1.** W(b,F) is concave in b, linear in F; W^*(F) is convex in F.

**Theorem 16.2.1 (Kuhn–Tucker).** b^* is log-optimal iff
E[ X_i / (b^{*T} X) ] ≤ 1  for all i, with equality if b_i^*>0.

**Theorem 16.2.2.** For any other portfolio, E[S / S^*] ≤ 1, and E log(S/S^*) ≤ 0. (Numeraire property of S^*.)

**Theorem 16.3.1 (Asymptotic optimality).** Among causal strategies on i.i.d. markets, b^* maximizes E log S_n and (1/n) log S_n → W^*; no causal scheme has a higher a.s. growth rate.

**Theorem 16.4.1.** Using b_f instead of b_g costs ΔW ≤ D(f||g).

**Theorem 16.4.2.** Side information Y: ΔW ≤ I(X;Y). (Horse race of Ch 6 achieves equality; markets generally have slack.)

**Theorem 16.5.1.** Stationary markets: W_∞^* = lim W^*(X_n | X^{n−1}) exists (Cesàro, as in entropy rate).

**Theorem 16.5.3 (AEP for the stock market).** For stationary ergodic {X_n}, the conditionally log-optimal wealth satisfies
(1/n) log S_n^* → W_∞^*  a.s.,   i.e. S_n^* ≐ 2^{n W_∞^*}.

**Theorem 16.6.1 (Competitive optimality).** With a uniform[0,2] fair randomization U^*,
Pr(U^* S^* ≥ S) ≥ 1/2
for any competing S (Bell–Cover). Log-optimal is game-theoretically undominated even in one period.

**Universal portfolios (Cover 1991; Cover–Ordentlich).** The universal wealth Ŝ_n satisfies
Ŝ_n / S_n(b) ≥ c / n^{(m−1)/2}
uniformly in b, so (1/n) log Ŝ_n − (1/n) log max_b S_n(b) → 0. Horizon-free and finite-horizon versions.

**Shannon–McMillan–Breiman (Section 16.8).** For a stationary ergodic finite-alphabet process,
−(1/n) log p(X^n) → H(X)  a.s.
(Barron, Orey: real-valued densities too.) This is the a.s. AEP promised since Ch 3–4.

## Key Equations
- S = b^T X,  W(b)=E log(b^T X)
- KT: E[X_i/(b^{*T} X)] ≤ 1
- ΔW ≤ D(f||g),  ΔW ≤ I(X;Y)
- S_n^* ≐ 2^{n W^*}
- Universal cost ~ ((m−1)/2) log n
- SMB: −(1/n) log p(X^n) → H a.s.

## Worked Example
Two stocks, X=(1, α) or (α, 1) with probability 1/2 each, α>0. Log-optimal is b=(1/2,1/2) by symmetry. W^* = log((1+α)/2). If α=1, cash-like, W=0. If α=3, W=log 2 = 1 bit/period — wealth doubles on average in the log sense. Buy-and-hold on one stock has E log X_1 = (1/2)log α < log((1+α)/2) unless α=1 (concavity of log).

Side information that names the winner: I=1 bit, ΔW ≤ 1; here you can put all wealth on the winning stock, S=α or 1 depending — actually S= the large component, W= (1/2)log α + (1/2)log 1, which for α=3 is 0.79 < 1, so ΔW < I.

## Anti-patterns
- **Mean-variance / Sharpe as growth**: they optimize a different objective; Samuelson criticizes log-utility, but Cover answers with a.s. growth and competitive optimality.
- **Confusing E S with exp(E log S)**: Jensen, log is concave; maximizing E S is ruinous (Ch 6).
- **Assuming ΔW = I in markets**: only ≤.
- **Universal portfolio as a free lunch**: it tracks the best *constant-rebalanced* b, not the best causal strategy or the omniscient hindsight path.
- **Using in-probability AEP (Ch 3) where a.s. is needed**: SMB is the right theorem for (1/n) log S_n.

## Key Takeaways
1. Log-optimal portfolios are the Kelly theorem in vector form.
2. Information bounds growth: D and I are the currencies.
3. Universal portfolios = universal codes on the simplex.
4. SMB is the general AEP; entropy rate is an almost-sure growth rate of 1/p(X^n).

## Connects To
- **Ch 6**: horse race is m outcomes with orthogonal “stocks”.
- **Ch 4**: entropy rate definitions dual to W_∞^*.
- **Ch 13**: mixture universality, same (k/2)log n.
- **Ch 3**: AEP in probability vs SMB a.s.
- **Ch 14**: universal probability as the ideal mixture.
