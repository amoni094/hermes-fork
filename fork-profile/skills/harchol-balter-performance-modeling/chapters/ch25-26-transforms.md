# Ch 25–26 — Transform Analysis of M/G/1

**Use when**: you need Var(T), sojourn distribution, or tail — means are not enough.

## Laplace (continuous)
```
X~(s) = E[e^{-sX}] = ∫ e^{-st} f(t) dt
Exp(λ): λ/(λ+s)
constant a: e^{-sa}
Unif(a,b): (e^{-sa}−e^{-sb}) / (s(b−a))
```
Moments: E[X^n] from nth derivative at s=0 (sign/(-1)^n). "Peel the onion."

Linearity: independent sum ⇒ product of transforms. Conditioning: X~(s)=E[X~(s)|Y].

M/M/1 sojourn is Exp(μ−λ): T~(s)=(μ−λ)/(μ−λ+s).

## z-transform (discrete)
```
N^(z) = ∑ π_i z^i = E[z^N]
```
Poisson(λt) count: e^{-λt(1-z)}.
Arrivals during service S: A_S^(z) = S~(λ(1−z)).

## M/G/1 number transform (embedded at departures)
Embedded DTMC X_i = number left by ith departure. PASTA + a_n=d_n ⇒ π^{embed}=π^{M/G/1}.

```
N^(z) = S~(λ−λz) (1−ρ)(1−z) / [S~(λ−λz) − z]
```

## M/G/1 sojourn transform
Number seen by a departure = arrivals during T, so N^(z)=T~(λ(1−z)). Change s=λ(1−z):
```
T~(s) = S~(s) (1−ρ) s / (λ S~(s) − λ + s)
```
Differentiate (L'Hôpital twice for the mean) to recover P-K. T = S+T_Q independent in FCFS ⇒ T~(s)=S~(s) T_Q~(s).

Distributional Little: this is the FCFS M/G/1 case of relating law(N) and law(T).

## Hermes
For SLO/tail (P(T>x)), do not stop at E[T]. If E[S³] is huge, Var(T_Q) is huge under FCFS even at modest ρ. SRPT/PS cut the tail of mice; FCFS does not.
