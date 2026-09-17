# Cheatsheet — Cover & Thomas EIT (2nd ed.)

Logs base 2 (bits) unless noted. 0 log 0 = 0.

## Entropy identities and chain rules

- H(X) = −∑ p log p ≥ 0;  H(X) ≤ log|X| (eq. iff uniform)
- H(X,Y) = H(X)+H(Y|X) = H(Y)+H(X|Y)
- H(X|Y) ≤ H(X)  (eq. iff independent) — *average* only
- H(X1…Xn) = ∑ H(Xi|X^{i−1}) ≤ ∑ H(Xi)
- I(X;Y) = H(X)−H(X|Y) = H(Y)−H(Y|X) = H(X)+H(Y)−H(X,Y)
- I(X;Y) = D(p(x,y)||p(x)p(y)) ≥ 0  (eq. iff independent)
- I(X;Y|Z) = H(X|Z)−H(X|Y,Z) ≥ 0  (eq. iff X⟂Y|Z)
- I(X1…Xn; Y) = ∑ I(Xi; Y | X^{i−1})
- D(p(x,y)||q(x,y)) = D(p(x)||q(x)) + D(p(y|x)||q(y|x))
- Binary entropy: H(p)= −p log p −(1−p)log(1−p), max 1 at p=1/2
- h(X)= −∫ f log f;  h(aX)=h(X)+log|a|;  h(AX)=h(X)+log|det A|
- N(μ,σ^2): h = (1/2) log(2πe σ^2)
- N(μ,K): h = (1/2) log((2πe)^n |K|)
- I and D formulas identical in discrete/continuous

## Key inequalities

- D(p||q) ≥ 0, eq. iff p=q  (information inequality)
- DPI: X→Y→Z ⇒ I(X;Y) ≥ I(X;Z)
- Fano: H(P_e)+P_e log|X| ≥ H(X|Y);  P_e ≥ (H(X|Y)−1)/log|X|
- Jensen: f convex ⇒ E f ≥ f(E)
- Log-sum: ∑ a log(a/b) ≥ (∑a) log(∑a/∑b)
- Independence bound: H(X^n) ≤ ∑ H(Xi)
- EPI: independent X,Y ⇒ 2^{2h(X+Y)} ≥ 2^{2h(X)}+2^{2h(Y)}
- Pinsker: D(p||q) ≥ (1/(2 ln 2)) ||p−q||_1^2
- Hadamard: |K| ≤ ∏ K_{ii}  (K≽0)
- Cramér–Rao: var(T) ≥ 1/J(θ)  (unbiased)
- Gaussian maxent: EK=K ⇒ h ≤ (1/2) log((2πe)^n |K|)

## AEP / types

- AEP: −(1/n) log p(X^n) → H in probability (i.i.d.)
- Typical set: |A_ε^{(n)}| ≤ 2^{n(H+ε)}, P(A)→1, p(x^n)≈2^{−nH}
- Smallest high-probability set has (1/n) log |B| ≥ H − o(1)
- Types: |T(P)| ≐ 2^{nH(P)},  Q^n(T(P)) ≐ 2^{−n D(P||Q)}
- # types ≤ (n+1)^{|X|}
- Sanov: P(P̂∈E) ≐ 2^{−n inf_{P∈E} D(P||Q)}
- SMB: −(1/n) log p(X^n) → H a.s. (stationary ergodic)

## Source coding (lossless)

- Kraft: ∑ D^{−l_i} ≤ 1  (prefix; also UD by McMillan)
- L ≥ H_D(X);  H ≤ L^* < H+1;  blocks: H ≤ L_n^*/n < H+1/n
- Shannon: l=⌈log 1/p⌉; Huffman optimal
- Wrong code q: L ≈ H(p)+D(p||q)
- LZ78: l(X^n)/n → H a.s. (stationary ergodic)
- Minimax redundancy = C(θ; X) of the parameter channel
- Parametric mixture redundancy ~ (k/2) log n

## Capacity formulas

- DMC: C = max_{p(x)} I(X;Y)
- BSC(p): C = 1 − H(p)
- BEC(α): C = 1 − α
- Noiseless |X|-ary: C = log|X|
- Symmetric: C = log|Y| − H(row of p(y|x)) at uniform input
- AWGN, power P, noise N: C = (1/2) log(1+P/N)
- Parallel Gaussian: waterfill P_i=(ν−N_i)^+, C=∑ (1/2) log(1+P_i/N_i)
- Bandlimited W Hz, noise PSD N0/2: C = W log(1+P/(N0 W)) bits/s
- W→∞: C → (P/N0) log_2 e  bits/s
- DMC feedback: C_FB = C
- Separation: i.i.d. source through DMC iff H < C

## Rate distortion

- R(D) = min_{E d ≤ D} I(X;X̂)
- Bern(p), Hamming: R(D)= H(p)−H(D) for 0≤D≤p (p≤1/2); 0 for D≥p
- N(0,σ^2), MSE: R(D)=(1/2) log(σ^2/D) for D≤σ^2; 0 for D≥σ^2
- Distortion-rate Gaussian: D(R)= σ^2 2^{−2R}
- Reverse waterfill independent Gaussians: D_k=min(λ,σ_k^2)
- D=0 discrete invertible d: R(0)=H(X)

## Networks (highlights)

- MAC: R1<I(X1;Y|X2), R2<I(X2;Y|X1), R1+R2<I(X1,X2;Y) over p1(x1)p2(x2), then convex hull
- Gaussian MAC sum: (1/2) log(1+∑P_i/N)
- Slepian–Wolf: R1≥H(X|Y), R2≥H(Y|X), R1+R2≥H(X,Y)
- Degraded BC: R2≤I(U;Y2), R1≤I(X;Y1|U), U→X→(Y1,Y2)
- Wyner–Ziv: min I(X;U|Y) s.t. U→X→Y, Ed≤D
- Gelfand–Pinsker: max[I(U;Y)−I(U;S)]
- Cut-set: R_S ≤ I(X_S; Y_{S^c} | X_{S^c})

## Gambling / portfolios

- Horse race: b^*=p,  W^*=∑ p_i log o_i − H(p);  W(p)−W(b)=D(p||b)
- Even odds m horses: W^*= log m − H
- Side info horse race: ΔW = I(X;Y);  markets: ΔW ≤ I(X;Y)
- Portfolio: W(b)=E log(b^T X);  KT: E[X_i/(b^{*T}X)]≤1
- Universal portfolio extra rate ~ ((m−1)/2)(log n)/n

## Kolmogorov

- K_U(x) ≤ K_A(x)+c_A;  |{K<k}|<2^k
- E K(X^n|n) → n H(X)  (finite alphabet i.i.d.)
- P_U(x) ≈ 2^{−K(x)};  ∑ 2^{−K} ≤ 1 (prefix)
