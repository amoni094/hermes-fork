# Major Theorems — Cover & Thomas, 2nd ed. (2006)

Statements follow Cover & Thomas. Logs are base 2 unless noted. Each entry: Statement / Proof sketch / Significance / Chapter.

---

## AEP theorem (Thm 3.1.1)

**Statement.** If X1,X2,… are i.i.d. ~ p(x), then
−(1/n) log p(X1,…,Xn) → H(X) in probability.

**Typical-set consequences (Thm 3.1.2).** A_ε^{(n)} = {x^n : 2^{−n(H±ε)} bounds p(x^n)} satisfies P(A)→1, |A| ≤ 2^{n(H+ε)}, and |A| ≥ (1−ε)2^{n(H−ε)} for n large.

**Proof sketch.** −log p(X_i) are i.i.d. with mean H; WLLN. Size bounds: 1 ≥ P(A) ≥ |A| 2^{−n(H+ε)}.

**Significance.** Turns H into a counting statement: ~2^{nH} typical sequences, each of probability ~2^{−nH}. Engine of source coding.

**Chapter.** 3. Almost-sure ergodic form: Shannon–McMillan–Breiman, Ch 16.

---

## Source coding theorem (noiseless)

**Statement (operational).** For i.i.d. discrete X ~ p, the minimum expected code length per symbol L_n^*/n satisfies H(X) ≤ L_n^* < H(X)+1/n, hence → H(X). No uniquely decodable code has expected length < H (one-shot: L ≥ H_D).

**Kraft / Shannon (Thm 5.2.1, 5.3.1, 5.4.1–2).** Prefix (and UD) D-ary lengths satisfy ∑ D^{−l_i}≤1, and L ≥ H_D(X), with Shannon lengths achieving H ≤ L < H+1.

**Huffman (Thm 5.8.1).** Huffman codes are optimal among UD codes.

**Proof sketch.** L−H = D(p||q)+log(∑ D^{−l_i}) ≥ 0 with q_i ∝ D^{−l_i}. Achievability: Shannon/Huffman or typical-set enumeration (Thm 3.2.1).

**Significance.** Entropy is the lossless compression limit.

**Chapter.** 3 (typical-set), 5 (Kraft/Huffman). Universal version: Ch 11, 13.

---

## Channel coding theorem (noisy) (Thm 7.7.1)

**Statement.** For a DMC p(y|x), let C = max_{p(x)} I(X;Y). Every rate R < C is achievable: there exist (2^{nR}, n) codes with Pe^{(n)}→0. Conversely, if Pe^{(n)}→0 then R ≤ C.

**Proof sketch (achievability).** Random codebook i.i.d. ~ p^*(x) achieving C. Jointly typical decoder. Error: true pair atypical (AEP→0) or a wrong codeword jointly typical (≤ 2^{nR} 2^{−n(I−3ε)}→0 if R<I).

**Proof sketch (converse).** nR = H(W) = I(W;Y^n)+H(W|Y^n) ≤ I(X^n;Y^n)+nε_n (Fano) ≤ ∑ I(X_i;Y_i)+nε_n ≤ nC+nε_n.

**Significance.** Shannon’s second theorem; defines the operational meaning of mutual information.

**Chapter.** 7. Gaussian: Ch 9. Feedback does not increase DMC C.

---

## Rate-distortion theorem (Ch 10)

**Statement.** For i.i.d. X~p and bounded distortion d,
R(D) = min_{p(x̂|x): E d(X,X̂)≤D} I(X;X̂).
Rates R > R(D) achieve average distortion D; R < R(D) cannot.

**Special cases.** Bern(p), Hamming: R(D)=H(p)−H(D) for D≤ min(p,1−p). N(0,σ^2), MSE: R(D)=(1/2) log(σ^2/D) for D≤σ^2.

**Proof sketch.** Achievability: random covering codebook ~ p(x̂), strongly typical encoding. Converse: nR ≥ I(X^n;X̂^n) ≥ ∑ I(X_i;X̂_i) ≥ n R^{(I)}(D) by definition and convexity.

**Significance.** Shannon’s third theorem; dual covering to channel packing.

**Chapter.** 10. With decoder SI: Wyner–Ziv, Ch 15.

---

## Data-processing inequality (Thm 2.8.1)

**Statement.** If X→Y→Z (i.e. p(x,y,z)=p(x)p(y|x)p(z|y)), then I(X;Y) ≥ I(X;Z). Equality iff X→Z→Y. In particular I(X;Y) ≥ I(X; g(Y)).

**Proof sketch.** I(X;Y,Z)=I(X;Z)+I(X;Y|Z)=I(X;Y)+I(X;Z|Y). Markov ⇒ I(X;Z|Y)=0; I(X;Y|Z)≥0.

**Significance.** No post-processing creates information about X. Sufficient statistics: I(θ;X)=I(θ;T(X)).

**Chapter.** 2.

---

## Fano’s inequality (Thm 2.10.1)

**Statement.** For any estimator X̂ with X→Y→X̂ and P_e=Pr(X≠X̂),
H(P_e) + P_e log|X| ≥ H(X|X̂) ≥ H(X|Y).
Weaker: P_e ≥ (H(X|Y)−1)/log|X|. Thus H(X|Y)>0 ⇒ P_e>0.

**Proof sketch.** Error bit E=1{X≠X̂}. Expand H(E,X|X̂) two ways: H(X|X̂)+0 = H(E|X̂)+H(X|E,X̂) ≤ H(P_e)+ P_e log|X|. DPI: H(X|X̂)≥H(X|Y).

**Significance.** Converts small error into small residual entropy; converses to almost every coding theorem.

**Chapter.** 2; used in 7, 10, 15.

---

## Chain rules

**Entropy (Thm 2.5.1).** H(X1,…,Xn)=∑_{i=1}^n H(Xi | X^{i−1}).

**Mutual information (Thm 2.5.2).** I(X1,…,Xn; Y)=∑_{i=1}^n I(Xi; Y | X^{i−1}).

**Relative entropy (Thm 2.5.3).** D(p(x,y)||q(x,y))=D(p(x)||q(x))+D(p(y|x)||q(y|x)).

**Differential (Thm 8.6.2).** Same with h.

**Proof sketch.** Factor p(x^n)=∏ p(x_i|x^{i−1}) and take −E log.

**Significance.** Time-sharing, converses, entropy rates (Cesàro on the conditional terms).

**Chapter.** 2, 8.

---

## Information inequality and corollaries (Thm 2.6.3–2.6.6)

**Statement.** D(p||q)≥0, eq. iff p=q. Hence I(X;Y)≥0 (eq. iff independent); H(X)≤ log|X| (eq. iff uniform); H(X|Y)≤H(X) (eq. iff independent); H(X^n)≤∑ H(X_i) (eq. iff independent).

**Proof sketch.** Jensen on −log, or D(p||u)=log|X|−H(X).

**Chapter.** 2.

---

## Entropy power inequality (Ch 17.8)

**Statement.** Independent real X,Y with densities:
2^{2 h(X+Y)} ≥ 2^{2 h(X)} + 2^{2 h(Y)}
(h in bits). Equality iff X,Y are Gaussian. Vector form uses entropy power N(X)=(1/(2πe)) exp(2h/n).

**Proof sketch.** Stam: Fisher informations of independent summands satisfy a parallel-resistor inequality; integrate de Bruijn’s identity along the heat flow to a Gaussian.

**Significance.** Gaussian extremals for additive noise; alternative proofs of AWGN C and Gaussian R(D); analog of Brunn–Minkowski.

**Chapter.** 17 (tools in 8–9).

---

## Slepian–Wolf theorem (Thm 15.4.1)

**Statement.** Separate encoders of i.i.d. pairs (X_i,Y_i), joint decoder: (R1,R2) achievable iff
R1 ≥ H(X|Y),  R2 ≥ H(Y|X),  R1+R2 ≥ H(X,Y).

**Proof sketch.** Achievability: randomly bin X^n into 2^{nR1} bins and Y^n into 2^{nR2}; decoder seeks the unique jointly typical pair in the two bins. Errors vanish if the three inequalities hold (joint AEP). Converse: Fano, treating one source as side information, plus H(X^n,Y^n)=n H(X,Y).

**Significance.** Correlation helps even when encoders do not communicate. Dual of the MAC region.

**Chapter.** 15.

---

## Other named theorems (short)

- **Jensen (2.6.2).** f convex ⇒ E f(X) ≥ f(EX).
- **Log-sum (2.7.1).** ∑ a_i log(a_i/b_i) ≥ (∑a) log(∑a/∑b).
- **McMillan (5.5.1).** UD codes satisfy Kraft.
- **Gaussian maxent (8.6.5).** EK=K ⇒ h(X)≤ (1/2) log((2πe)^n |K|), eq. iff N(0,K).
- **AWGN capacity (Ch 9).** C=(1/2) log(1+P/N).
- **MAC capacity (15.3.1).** Convex hull of R1<I(X1;Y|X2), R2<I(X2;Y|X1), R1+R2<I(X1,X2;Y) over p(x1)p(x2).
- **Sanov (Ch 11).** P(P̂∈E)≐ 2^{−n inf_{P∈E} D(P||Q)}.
- **Chernoff–Stein (11.8.3).** (1/n) log β_n^* → −D(P1||P2).
- **Cramér–Rao (11.10.1).** var(T)≥1/J(θ) unbiased.
- **Maxent (12.1.1).** Moment constraints ⇒ exponential family uniquely maximizes h.
- **Burg (Ch 12).** Maxent given p autocorrelations = Gauss–Markov p.
- **LZ78 optimality (13.5.3).** l(X^n)/n → H a.s. for binary stationary ergodic sources.
- **Kolmogorov invariance (14.2.1).** K_U ≤ K_A + c_A; E K(X^n|n)→ nH (14.3.1).
- **Wyner–Ziv (Ch 15).** R_{X|Y}(D)= min I(X;U|Y) over U→X→Y, Ed≤D.
- **Gelfand–Pinsker (Ch 15).** C=max[I(U;Y)−I(U;S)].
- **Log-optimal portfolio KT (16.2.1).** E[X_i/(b^{*T}X)]≤1.
- **SMB / general AEP (16.8).** −(1/n) log p(X^n)→H a.s. ergodic.
- **Han’s inequality (17.6).** Average k-subset entropy rates decrease in k.
- **Hadamard (17.9).** |K|≤∏ K_{ii} for K≽0.
