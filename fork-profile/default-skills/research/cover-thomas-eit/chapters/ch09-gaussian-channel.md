# Chapter 9: Gaussian Channel

## Core Idea
The AWGN channel Y = X+Z, Z~N(0,N), with power constraint (1/n)∑ X_i^2 ≤ P, has capacity C = (1/2) log(1+P/N). Bandlimited continuous-time AWGN with bandwidth W and power P has C = W log(1+P/(N0 W)) bits per second. Parallel/colored Gaussian channels waterfill; feedback at most half a bit (and at most a factor of 2) for nonwhite Gaussian noise.

## Key Concepts
- **Discrete-time AWGN**: Y_i = X_i + Z_i, Z_i i.i.d. N(0,N), independent of X. Power: ∑ X_i^2 ≤ nP.
- **Without power or with N=0**: C=∞ (pack infinitely many far-apart points).
- **Waterfilling**: for parallel channels with noises N_k and total power, put P_k = (ν − N_k)^+ so the “water level” ν is constant on used channels.
- **Bandlimited channel**: W Hz, two-sided noise PSD N0/2, capacity W log(1+P/(N0 W)) bits/s. As W→∞, C→ (P/N0) log e nats/s.
- **Colored noise**: waterfill in the eigenbasis (or frequency domain).
- **Feedback**: C ≤ C_no FB + (1/2) bit, and C ≤ 2 C_no FB, for additive Gaussian noise (Cover–Pombra). Feedback does help colored noise, not memoryless AWGN.

## Frameworks and Methods
- **Converse first**: I(X^n;Y^n) ≤ h(Y^n) − h(Z^n) ≤ ∑ (1/2)log(2πe (P_i+N)) − (n/2)log(2πe N), then Jensen on log(P_i+N) with ∑ P_i ≤ nP.
- **Achievability**: Gaussian random codebooks ~ N(0,P−ε); jointly typical / nearest-neighbor decoding. Power constraint holds with high probability.
- **Waterfilling as KKT**: maximize (1/2)∑ log(1+P_k/N_k) s.t. ∑ P_k = P, P_k≥0.
- **Sphere packing intuition**: noise spheres of radius √(nN) inside a sphere of radius √(n(P+N)); ratio of volumes gives (1/2)log(1+P/N).

## Key Results and Theorems

**Capacity of the power-constrained AWGN channel.**
C = max_{EX^2 ≤ P} I(X; X+Z) = (1/2) log(1 + P/N),
achieved at X~N(0,P).

Proof of the max: I(X;Y)=h(Y)−h(Z). h(Z)=(1/2)log(2πe N) is fixed. h(Y) ≤ (1/2)log(2πe (P+N)) by Gaussian maxent (Thm 8.6.5), since EY^2 = EX^2 + N ≤ P+N.

**Coding theorem.** All rates R < C are achievable with Pe→0 under the power constraint; conversely R≤C.

**Bandlimited (Shannon).** C = W log(1 + P/(N0 W)) bits per second. (Cover–Thomas use 2W real samples/s of a W-Hz baseband signal.)

**Infinite bandwidth.** lim_{W→∞} C = (P/N0) log_2 e bits/s.

**Parallel Gaussian channels.**
C = max_{∑ P_i ≤ P} ∑_i (1/2) log(1 + P_i/N_i),
with P_i = (ν − N_i)^+.

**Colored Gaussian noise.** Diagonalize the noise covariance; waterfill on eigenvalues. Frequency-domain: S_X(f) = (ν − N(f))^+.

**Feedback (Cover–Pombra).** For additive Gaussian noise (possibly nonwhite),
C_n,FB ≤ C_n + (1/2) bit
and C_FB ≤ 2 C_noFB. Memoryless AWGN: feedback does not increase C (Ch 7 applies).

## Key Equations
- Y = X+Z, Z~N(0,N), EX^2≤P
- C = ½ log(1+P/N)
- SNR = P/N; C = ½ log(1+SNR)
- Waterfill: P_i = (ν − N_i)^+, ∑ P_i = P
- Continuous time: C = W log(1+P/(N0 W)) bits/s
- Infinite BW: C∞ = P/(N0 ln 2) bits/s

## Worked Example
P=N ⇒ SNR=1 ⇒ C = 1/2 bit per transmission. A (2^{n/4}, n) code (R=1/4) is achievable; R=3/4 is not.

Two parallel channels, N1=1, N2=4, P=5. Water level: try both on, P1=ν−1, P2=ν−4, sum 2ν−5=5 ⇒ ν=5, P2=1, P1=4. C = ½ log(1+4/1)+½ log(1+1/4)= ½ log 5 + ½ log(5/4). If instead you dump all power on channel 1, P1=5, C=½ log 6, which is smaller (log 6 ≈ 2.58, log5+log(5/4)≈ 2.32+0.32=2.64 nats comparison: ½ log6≈1.29, ½(log5+log1.25)≈1.32 bits).

## Anti-patterns
- **Forgetting the power constraint**: unconstrained Gaussian channel has infinite capacity.
- **Waterfilling on gains instead of noise**: write channel as gain g_i with noise 1, then waterfill on 1/g_i^2.
- **Assuming feedback helps AWGN**: not the memoryless case.
- **Mixing bits and nats**: ½ ln(1+SNR) nats = ½ log2(1+SNR) bits.
- **Using 2W log(1+P/N0 W) extra factor carelessly**: Cover–Thomas already fold 2W samples into W log(1+P/(N0 W)) with appropriate N0 convention.

## Key Takeaways
1. Gaussian maxent + power constraint ⇒ the log(1+SNR) formula.
2. Waterfilling is the unique power allocation for parallel/colored Gaussian.
3. Bandwidth vs power: infinite bandwidth still finite capacity, linear in P/N0.
4. Feedback is essentially useless for memoryless AWGN, mildly useful for colored noise.

## Connects To
- **Ch 7**: same coding theorem, Gaussian specialization.
- **Ch 8**: h(N(0,σ^2)) and maxent.
- **Ch 10**: Gaussian R(D)=½ log(σ^2/D) is the dual waterfill (reverse waterfill).
- **Ch 15**: Gaussian MAC/broadcast/relay; superposition and dirty paper.
- **Ch 17**: EPI gives alternative proofs of Gaussian inequalities.
