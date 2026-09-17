# Chapter 10: Rate Distortion Theory

## Core Idea
Lossy compression asks: given distortion measure d(x,x̂), what is the minimum rate R(D) to achieve E d(X,X̂) ≤ D? Shannon’s answer is the information rate-distortion function R(D) = min_{p(x̂|x): E d ≤ D} I(X;X̂). Joint typicality now *covers* the source typical set with distortion balls (the dual of channel packing).

## Key Concepts
- **Distortion measure**: d: X×X̂ → [0,∞). Single-letter; block distortion d(x^n,x̂^n)=(1/n)∑ d(x_i,x̂_i).
- **(2^{nR}, n) rate-distortion code**: encoder i: X^n → {1..2^{nR}}, decoder x̂^n(i). Achieves distortion D if E d(X^n, X̂^n) ≤ D (or, in probability versions, P(d>D)→0).
- **Rate-distortion function (operational)**: R(D) = inf{R : (R,D) achievable}.
- **Information R(D)**: R^{(I)}(D) = min_{p(x̂|x): ∑∑ p(x)p(x̂|x) d(x,x̂) ≤ D} I(X;X̂).
- **Hamming distortion**: d=1{x≠x̂}. Squared error: d=(x−x̂)^2.
- **Strong typicality**: empirical joint type close to p(x,x̂); needed because distortion is an empirical average, not just a log-probability.
- **Blahut–Arimoto**: alternating minimization to compute R(D) or C.

## Frameworks and Methods
- **Covering, not packing**: throw 2^{nR} random codewords ~ p(x̂); a source x^n is “good” if some codeword is jointly typical / distortion-typical with it. Success when R > I(X;X̂).
- **Converse**: nR ≥ I(X^n;X̂^n) ≥ ∑ I(X_i;X̂_i) ≥ n R^{(I)}(D) by convexity of I and definition of R^{(I)}, using the test channel that realizes the observed distortion.
- **D=0 discrete**: R(0)=H(X) if d(x,x̂)=0 iff x=x̂, recovering lossless coding.
- **Reverse waterfilling**: independent Gaussians of variances σ_k^2 described to distortion D_k = min(λ, σ_k^2).

## Key Results and Theorems

**Rate-distortion theorem.** For i.i.d. source ~ p(x) and bounded distortion,
R(D) = min_{p(x̂|x): E d(X,X̂)≤D} I(X;X̂).
Achievability: random codebook of size 2^{n(R)}, jointly strongly typical encoding. Converse: Fano-style / information inequalities as above.

**Binary source, Hamming distortion.** X~Bern(p), p≤1/2.
R(D) = H(p) − H(D) for 0 ≤ D ≤ p, and R(D)=0 for D≥p.
Test channel: X̂ ~ Bern(p), X = X̂ + Z, Z~Bern(D) independent (or the backward BSC).

**Gaussian source, squared error.** X~N(0,σ^2),
R(D) = (1/2) log(σ^2/D) for 0 < D ≤ σ^2, and 0 for D≥σ^2.
Achieved by X̂ = (1−D/σ^2) X + noise, or equivalently backward: X = X̂ + Z, Z~N(0,D) independent of X̂~N(0,σ^2−D).

**Independent Gaussians (reverse waterfill).**
R(D) = ∑ (1/2) log(σ_k^2 / D_k),  D_k = min(λ, σ_k^2),  ∑ D_k = D.

**Properties.** R(D) convex, nonincreasing, continuous in D (under mild conditions). R(D)=0 iff D ≥ D_max = min_{x̂} E d(X,x̂).

**Shannon lower bound (differential).** For difference distortion d(x−x̂),
R(D) ≥ h(X) − max_{E d(Z)≤D} h(Z).
Equality for Gaussian + squared error.

**Blahut–Arimoto.** Iterate p(x̂) ↔ p(x̂|x) ∝ p(x̂) exp(−λ d(x,x̂)) to compute R(D); dual of capacity computation.

## Key Equations
- R(D) = min_{Ed≤D} I(X;X̂)
- Bern(p), Hamming: R(D)=H(p)−H(D), D≤p
- N(0,σ^2), MSE: R(D)=½ log(σ^2/D), D≤σ^2
- D=σ^2 2^{−2R}  (Gaussian distortion-rate)
- Reverse waterfill: D_k = min(λ, σ_k^2)

## Worked Example
Gaussian N(0,1), want D=1/4. R = ½ log(1/(1/4)) = 1 bit. So 1 bit per sample of a unit Gaussian achieves MSE 0.25 — e.g. a well-designed 2-level quantizer is worse (1-bit scalar quantizer MSE is 2/π ≈ 0.36); the extra gain is from *block* descriptions (geometry of non-rectangular grids). Cover’s elephant-and-chicken: independent problems do not have independent optimal descriptions.

Binary p=1/2, D=0.11: R = 1−H(0.11)≈0.5 bits. Numerically the BSC capacity of Ch 7: the test channel is a BSC, and R(D)+C_BSC(D)=1.

## Anti-patterns
- **Scalar quantization as R(D)**: R(D) is *block* Shannon limit; scalar quantizers have a gap (high-rate ~ 0.25 bit MSE Gaussian).
- **Using weak typicality only**: distortion is not a continuous function of probability in the weak topology; need strong typicality / types.
- **Forgetting D_max**: you can always achieve D_max at rate 0 by emitting a constant.
- **Minimizing I without the distortion constraint**: gives 0 at independent X̂.
- **Assuming separation with distortion automatically**: there is a source–channel theorem with distortion (Problem 10.17), but it needs the rate-distortion function, not entropy.

## Key Takeaways
1. R(D) = min I(X;X̂) s.t. Ed≤D is the third Shannon theorem.
2. Binary Hamming and Gaussian MSE have closed forms that dualize BSC and AWGN.
3. Joint descriptions beat separate descriptions even for independent Gaussians (reverse waterfill / packing geometry).
4. Strong typicality is the right typicality for empirical averages like distortion.

## Connects To
- **Ch 5**: D=0 lossless special case.
- **Ch 7**: packing vs covering; Blahut–Arimoto computes both C and R(D).
- **Ch 9**: Gaussian channel waterfill vs Gaussian source reverse waterfill.
- **Ch 11**: types make the covering lemma finite-alphabet clean.
- **Ch 15**: Wyner–Ziv rate distortion with side information; multiple descriptions.
