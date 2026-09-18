# Chapter 8: Differential Entropy

## Core Idea
Differential entropy h(X) = −∫ f log f is the continuous analog of H, but it is *not* a limit of discrete entropies under naive quantization (an extra −log Δ appears), can be negative, and is not invariant to scaling. Relative entropy and mutual information *do* survive the continuous limit unchanged and stay nonnegative.

## Key Concepts
- **Differential entropy**: h(X) = −∫_S f(x) log f(x) dx, S = {f>0}.
- **Joint / conditional**: h(X,Y) = −∫ f log f,  h(X|Y) = −∫ f(x,y) log f(x|y).
- **Continuous relative entropy**: D(f||g) = ∫ f log(f/g) ≥ 0, equality iff f=g a.e.
- **Continuous mutual information**: I(X;Y) = D(f(x,y)||f(x)f(y)) = h(X)−h(X|Y). Always ≥ 0.
- **AEP for densities**: (1/n) log (1/f(X^n)) → h(X) in probability; typical set has volume ≈ 2^{n h}.
- **Support / quantization**: if X^Δ = ⌊X/Δ⌋ Δ, then H(X^Δ) + log Δ → h(X) as Δ→0 (under regularity).

## Frameworks and Methods
- **Never treat h as discrete H**: use I and D for operational statements; h is a convenient intermediary.
- **Gaussian maximizer**: among fixed-variance densities, N(0,σ^2) maximizes h. This is the engine of AWGN capacity and EPI.
- **Translation invariance, scale covariance**: h(X+c)=h(X); h(aX)=h(X)+log|a|; h(AX)=h(X)+log|det A|.
- **Typical-set volume**: analog of |A|≈2^{nH} is Vol(A)≈2^{n h}. Can be <1 if h<0.

## Key Results and Theorems

**Examples (bits, log2).**
- Uniform[0,a]: h = log a. Negative if a<1.
- Exponential(λ): h = 1 − log λ  (nats: 1−ln λ).
- Normal N(μ,σ^2): h = (1/2) log (2πe σ^2).
- Multivariate N(μ,K): h = (1/2) log ((2πe)^n |K|).

**AEP (Thm 8.2.1).** For i.i.d. continuous X_i with density f,
−(1/n) log f(X^n) → h(X) in probability.

**Quantization relation (Thm 8.3.1).** H(X^Δ) + log Δ → h(X) as Δ→0.

**Theorem 8.6.1.** h(X|Y) ≤ h(X), equality iff independent.

**Theorem 8.6.2 (Chain rule).** h(X1,...,Xn) = ∑ h(Xi | X^{i−1}).

**Theorem 8.6.3.** D(f||g) ≥ 0, I(X;Y) ≥ 0, with the usual equality conditions.

**Theorem 8.6.4.** h(X1,...,Xn) ≤ ∑ h(Xi).

**Theorem 8.6.5 (Gaussian maximum entropy).** If EX=0, E XX^T = K, then
h(X) ≤ (1/2) log ((2πe)^n |K|),
equality iff X ~ N(0,K). Proof: D(f || N(0,K)) ≥ 0 expands to this.

**Linear transforms.** h(AX) = h(X) + log |det A|.

**Hadamard-type.** |K| ≤ ∏ K_{ii}, so jointly Gaussian h(X) ≤ ∑ h(X_i).

## Key Equations
- h(X) = −∫ f log f
- h(aX) = h(X)+log|a|
- N(μ,σ^2): h = ½ log(2πe σ^2)
- I(X;Y) = h(X)−h(X|Y) = D(f(x,y)||f(x)f(y))
- H(X^Δ) ≈ h(X) − log Δ
- max_{EK=K} h = ½ log((2πe)^n |K|)

## Worked Example
X ~ Uniform[0,1/8]: h(X)=log(1/8)=−3 bits. That does *not* mean “negative information”. Quantize to bins of width Δ=1/256: about 32 occupied bins if support is 1/8, H(X^Δ)≈5 bits, and H+log Δ ≈ 5 + log(1/256) = 5−8 = −3 = h.

Two i.i.d. N(0,σ^2): h(X,Y)= log(2πe σ^2). If they are perfectly equal, density is singular, h(X,Y)=−∞, I(X;Y)=∞.

## Anti-patterns
- **Interpreting h<0 as nonsense**: it is a coordinate artifact; I and D are the invariants.
- **Assuming h is discretization-invariant**: changing units changes h by log|a|.
- **Writing C = max h(Y)−h(Y|X) blindly when densities don’t exist**: need I defined as a sup over partitions (Kolmogorov–Pinsker).
- **Maximizing h without a constraint**: unbounded (take large variance).
- **Using H(X) ≤ log|X| for continuous X**: replace by Gaussian / support constraints.

## Key Takeaways
1. h is a useful formula, not an operational entropy; I and D are operational.
2. Gaussians maximize entropy under second-moment constraints — the root of Ch 9–10, 17.
3. Quantization always contributes −log Δ; never compare h to H without it.
4. Chain rules, DPI, and I≥0 carry over verbatim.

## Connects To
- **Ch 2**: discrete prototypes of every identity here.
- **Ch 9**: AWGN capacity = max I(X;X+Z) under power, using Gaussian maxent.
- **Ch 10**: Gaussian rate-distortion uses the same maximizer.
- **Ch 12**: maxent distributions (exponential family).
- **Ch 17**: entropy power inequality, de Bruijn, Fisher information.
