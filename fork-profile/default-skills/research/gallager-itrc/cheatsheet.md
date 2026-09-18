# Cheatsheet — Gallager ITRC formulas

Units: ln, nats. Bits: divide rates/exponents by ln 2. Binary entropy in nats: H_b(p) = −p ln p − (1−p) ln(1−p); in bits h_2(p) = H_b(p)/ln 2.

## Mutual information and entropy

H(X) = −∑_x P(x) ln P(x)
I(X;Y) = ∑_{x,y} P(x,y) ln [P(x,y)/(P(x)P(y))] = H(X) − H(X|Y)
I(Q; P) = ∑_{k,j} Q(k) P(j|k) ln [P(j|k) / ∑_i Q(i) P(j|i)]

## Capacity

DMC: C = max_Q I(Q; P)
BSC(ε): C = ln 2 − H_b(ε)   [= 1 − h_2(ε) bits]
AWGN, one real use: C = (1/2) ln(1 + E/σ^2)
Bandlimited AWGN: C = W ln(1 + P/(N_0 W)) nats/s
Infinite-bandwidth AWGN: C = P / N_0 nats/s
Parallel AWGN: E_n = (μ − σ_n^2)_+,  C = ∑ (1/2) ln(1 + E_n/σ_n^2)

Capacity-achieving Q (DMC): I(X=k; Y) ≤ C ∀k, equality whenever Q(k) > 0.

## Random-coding bound

P_e ≤ exp(−N E_r(R))

E_r(R) = max_{ρ ∈ [0,1]} [E_0(ρ, Q*) − ρ R]
Q* maximizes E_0(ρ, ·) (then maximize over ρ).

E_0(ρ, Q) = −ln ∑_y [∑_x Q(x) P(y|x)^{1/(1+ρ)}]^{1+ρ}

DMC letter form: y → j, x → k, P(y|x) → P(j|k).

Properties:
- E_0(0,Q) = 0
- ∂E_0/∂ρ |_{ρ=0} = I(Q;P)
- E_0 increasing, concave in ρ
- E_r(R) > 0 ⇔ R < C (after max over Q)
- ρ = −d E_r / dR at the optimum

## Cutoff rate

R_0 = E_0(1, Q*) = max_Q E_0(1, Q)
For R small enough that ρ* = 1: E_r(R) = R_0 − R
Sequential decoding: operate at R < R_0

## Expurgated bound

P_{e,m} ≤ exp(−N E_ex(R + (ln 4)/N))   (all m)

E_ex(R) = max_{ρ ≥ 1} [E_x(ρ, Q) − ρ R]

E_x(ρ, Q) = −ρ ln ∑_{k,k'} Q(k) Q(k') [∑_j √(P(j|k) P(j|k'))]^{1/ρ}
(Gallager (5.7.12); at ρ = 1, E_x(1,Q) = E_0(1,Q).)

E_ex(R) ≥ E_r(R), better at low R.

## BSC random-coding function (equiprobable Q)

E_0(ρ) = ρ ln 2 − (1+ρ) ln[ ε^{1/(1+ρ)} + (1−ε)^{1/(1+ρ)} ]

## Two-word / Chernoff

P(x → x') ≤ ∑_y √(P(y|x) P(y|x'))     (Bhattacharyya, ρ = 1 pairwise)
AWGN white: P_2 = Q(d / (2σ)), σ^2 = N_0/2 per dimension, d = Euclidean distance.

## Source coding

Kraft: ∑_i D^{−ℓ_i} ≤ 1  (prefix / uniquely decodable)
H / ln D ≤ L < H / ln D + 1   (prefix, one-shot)
Lossless DMS: need rate > H (nats per letter)

## Rate distortion

R(d*) = min_{P(x̂|x): E d(X,X̂) ≤ d*} I(X; X̂)
Binary Hamming: R(d*) = ln 2 − H_b(d*)  (0 ≤ d* ≤ 1/2)
Gaussian MSE: R(d*) = max{ (1/2) ln(σ^2 / d*), 0 }
Separation: distortion d* over a channel is possible iff R(d*) < C

## Linear / convolutional

(N,L) binary: R = (L ln 2)/N nats = L/N bits
x = u G,  x H = 0,  S = y H
Convolutional: R = (λ ln 2)/ν , constraint length N = ν L
Threshold: 2e orthogonal checks ⇒ correct e errors on that bit
Fano metric (BSC): Γ = −d_H(x,y) ln((1−ε)/ε) + length · (ln[2(1−ε)] − B)

## Burst

Burst length b relative to guard g; capability b vs g; interleave r or use g(D^r).
ARQ: error iff noise is a nonzero codeword; fraction 2^{L−N} of sequences.
