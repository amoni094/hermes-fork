# Cheatsheet — Shannon 1948 formulas

Log is whatever base defines the unit (bit if 2, nat if e). Shannon’s notation: H(x), Hx(y), Hy(x). Modern: H(X), H(Y|X), I(X;Y)=H(X)−H(X|Y).

## Entropy (discrete)
```
H(x)     = −∑ pi log pi
H(x,y)   = −∑ p(i,j) log p(i,j)
Hx(y)    = −∑ p(i,j) log pi(j)
H(x,y)   = H(x) + Hx(y) = H(y) + Hy(x)
H(x,y)  ≤ H(x) + H(y)          eq. iff independent
Hx(y)   ≤ H(y)                 eq. iff independent
0 ≤ H ≤ log n                  n = alphabet size
binary:  h(p) = −p log p − (1−p) log(1−p)
```

Source (finite-state): H = −∑_{i,j} Pi pi(j) log pi(j)
GN → H, FN → H, FN ≤ GN
relative entropy = H / log n
redundancy = 1 − relative entropy

AEP: typical set size ~ 2^{HN}, each p ~ 2^{−HN}

## Rate and capacity (discrete)
```
R = H(x) − Hy(x) = H(y) − Hx(y) = H(x) + H(y) − H(x,y)
C = Max R
```
Theorem 9:  symbols/s ≤ C/H, and (C/H − ε) is achievable.
Theorem 11: H≤C ⇒ Pe→0; H>C ⇒ Hy(x) ≥ H−C.
Theorem 12: C = lim (log N(T,q))/T,  q∈(0,1).

Noiseless C = lim (log N(T))/T = log W.

## Standard discrete channels (from Sec 16 formulas)
BSC (cross p), symmetric, m=2, pi = (1−p, p):
```
C = 1 − h(p)     bits/use
```
(Shannon’s uniform-line formula C = log m + ∑ pi log pi.)

BEC (erasure probability e): not named; treat as 2 inputs / 3 outputs, or group formula. Modern: C = 1−e.

Fig. 11 (1 clean + 2 confused with χ=h(p)):
```
C = log(2 + 2^χ) − χ
```
Isolated groups of capacities Cn:
```
C = log ∑ 2^{Cn} ,   Pn ∝ 2^{Cn}
```
Hamming 7-bit single-error channel: C = 4/7 bits/symbol, achieved by (7,4).

## Continuous entropy
```
H = −∫ p log p
H_Gaussian(σ) = log √(2π e σ²)
H_n(aij)      = (n/2) log(2π e) − (1/2) log |aij|
H(y) = H(x) − E[log |J|]
```
Maxent: variance σ² → Gaussian; mean a on [0,∞) → (1/a)e^{−x/a}, H=log(e a); volume v → log v.

## Sampling, entropy power
```
f(t) = ∑ Xn sinc(2Wt − n),   Xn = f(n/(2W))
dim = 2TW
H′ = lim (−1/n) ∫ p log p          per degree of freedom
H  = 2W H′                          per second
white: H = W log(2π e N)
N1 = exp(2H′) / (2π e)             entropy power
N1 ≤ N  (eq. iff white)
```
Filter: H2 = H1 + (1/W)∫ log |Y(f)|² df
EPI: N̄1 + N̄2 ≤ N̄3 ≤ N1 + N2

## Continuous channel
```
R = ∬ p(x,y) log[ p(x,y)/(p(x)p(y)) ] dx dy
additive: R = H(y) − H(n)
C = Max R
```
**AWGN / Theorem 17 (Shannon–Hartley):**
```
C = W log((P+N)/N) = W log(1 + P/N)
```
**Arbitrary noise, entropy power N1, power N:**
```
W log((P+N1)/N1) ≤ C ≤ W log((P+N)/N1)
```
Colored Gaussian: N1 = exp((1/W) ∫_W log N(f) df)

**Peak power S (Theorem 20):**
```
C ≥ W log(2S/(π e N))
C ≤ W log[(2/πe)(S+N)/N (1+ε)]     large S/N
C ∼ W log(1+S/N)                    S/N → 0
```

## Rate vs fidelity (Part V)
```
v = ∬ ρ(x,y) P(x,y) dx dy
R1 = Min I(x;y)  s.t.  E[ρ] = v1
R1 ≤ C ⇔ fidelity v1 is achievable
```
White source, RMS, allowed MSE N, power Q, band W1:
```
R = W1 log(Q/N)
```
General source, entropy power Q1:
```
W1 log(Q1/N) ≤ R ≤ W1 log(Q/N)
```
Backward kernel (best encoding): Py(x) = B(x) e^{−λ ρ(x,y)}

## Duality
```
C = Max_{P(x)}    I(x;y)     (Px(y) fixed, maybe power constraint)
R = Min_{Px(y)}   I(x;y)     (P(x) fixed, fidelity constraint)
```

## Inequalities (quick)
```
0 ≤ R ≤ min(H(x), H(y))
R(x;v) ≤ R(x;y)                 data processing (App. 7)
H′ ≤ log √(2π e N)              given power N
C_AWGN = W log(1+SNR)
C_peak / C_avg → 2/(π e)        high SNR (peak vs same numerical S=P)
```

## Limits
```
T→∞ typical sets / volumes
q≠0,1 packing rates = C or H
P→∞  arbitrary-noise C ∼ W log((P+N)/N1)
S/N→0  peak C ∼ W log(1+S/N)
```
