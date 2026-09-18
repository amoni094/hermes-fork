# Cheatsheet — MacKay ITILA

## Entropy formulas (log base 2 unless noted)

| Quantity | Formula | Notes |
|---|---|---|
| Information content | h(x) = log 1/P(x) | Optimal length |
| Entropy | H(X) = ∑ p(x) log 1/p(x) | H≥0 |
| Joint | H(X,Y) = H(X)+H(Y\|X) | Chain rule |
| Conditional | H(X\|Y) = H(X,Y)−H(Y) | 0 if X det. of Y |
| Mutual information | I(X;Y)=H(X)−H(X\|Y)=H(Y)−H(Y\|X)=H(X)+H(Y)−H(X,Y) | ≥0 |
| KL | D_KL(Q\|\|P)=∑ Q log Q/P | ≥0, =0 iff Q=P; asymmetric |
| Binary entropy | H_2(p)= −p log p −(1−p)log(1−p) | bits |

**Relationships**
- H(X,Y) ≤ H(X)+H(Y), equality iff independent
- I(X;Y)= D_KL(P(x,y)\|\|P(x)P(y))
- Chain: H(X1…Xn)= ∑ H(Xi\|X<i)
- I(X;Y\|Z) analogously

## Key inequalities

| Name | Statement |
|---|---|
| Max entropy | H(X) ≤ log \|X\|, = iff uniform |
| Gibbs | D_KL(Q\|\|P) ≥ 0 |
| Jensen (convex) | f(E x) ≤ E f(x) |
| Data processing | X—Y—Z Markov ⇒ I(X;Z) ≤ I(X;Y) |
| Fano (sketch) | H(X\|X̂) ≤ H_2(Pe)+Pe log(\|X\|−1) |
| Kraft | prefix ⇒ ∑ 2^{−l_i} ≤ 1 |
| Source coding | L ≥ H; typical set size ≈ 2^{NH} |
| Channel coding | Pe→0 possible iff R ≤ C |

## Channel capacity (common models)

| Channel | C (bits/use) |
|---|---|
| BSC(f) | 1 − H_2(f) |
| BEC(f) | 1−f |
| q-ary erasure | (1−f) log2 q |
| Z-channel | depends on P(x=1); not 1−H_2 |
| AWGN power P, noise N | ½ log2(1 + P/N)  per real use |
| Constrained noiseless | lim (1/T) log N(T)  (Ch 17) |

Capacity-achieving input: uniform for BSC/BEC; Gaussian for AWGN.

## Source coding

- Optimal length l(x) = log2 1/p(x)  (possibly fractional)
- Huffman: best integer prefix lengths; H ≤ L < H+1
- Arithmetic: L/n → H
- LZ: L/n → H for ergodic unknown P, large n
- Lossy / typical-set: ~2^{nH} typical strings

## When to use which code

| Need | Use |
|---|---|
| Known discrete P, simple | Huffman (Ch 5) |
| Sequential / fractional bits / any P | Arithmetic (Ch 6) |
| Unknown source, one pass | Lempel–Ziv (Ch 6) |
| Integers, unknown range | Elias / Ch 7 codes |
| Noisy bits, large N, approach C | LDPC (Ch 47) or turbo (Ch 48) |
| Tiny encoder, still good | RA (Ch 49) |
| Packet erasures, unknown f, broadcast | Fountain / LT (Ch 50) |
| Streaming with trellis decoder | Convolutional + Viterbi/BCJR (Ch 48) |
| Tiny N, algebraic | Hamming etc. (Ch 1, 13) — not Shannon-good |

## Inference method selection

| Situation | Method | Ch |
|---|---|---|
| Discrete, tiny | Enumerate | 21 |
| Tree / trellis / low treewidth | Sum–product / junction tree | 25–26 |
| Unimodal continuous, evidence needed | Laplace | 27 |
| Compare models H | Evidence P(D\|H), not MLE | 28 |
| Latents, point θ OK | EM | 22 |
| Need distribution, conditionals easy | Gibbs | 29 |
| Density known up to Z, continuous | MH; HMC if gradients | 29–30 |
| Must be unbiased, monotone space | CFTP | 32 |
| Bound + speed, factorized OK | Variational / mean field | 33 |
| Neural classifier, error bars | MC or Laplace on w | 41, 44 |
| Nonlinear regression, N modest | GP | 45 |
| Linear blur, Gaussian image | Wiener / linear-Gaussian | 46 |

## Monte Carlo method selection

| Goal | Tool | Avoid |
|---|---|---|
| E[f] in 1-D with envelope | Rejection / quadrature | — |
| Low-D, good q covering p | Importance sampling | High-D IS (weight collapse) |
| General P(x) | MH | Tiny steps in high-D |
| Easy conditionals | Gibbs | Highly correlated coordinates without blocking/overrelaxation |
| Continuous + ∇log P | HMC | L=1 “HMC”; non-symplectic integrators |
| Mode finding | Annealing / optimizer | Claiming annealed chain is posterior at T=1 |
| Evidence Z | AIS / thermodynamic integration / Laplace / variational bound | Harmonic mean of likelihoods |
| Exact π | CFTP | Forward coalescence sample |

ESS ≈ T / τ_int. Always: multiple starts, traces, more than one functional.

## Neural / learning crib

| Model | Activity | Learning | Capacity / note |
|---|---|---|---|
| Logistic neuron | y=σ(w·x) | ∇ log-loss + weight decay | 2 bits/weight (threshold) Ch 40 |
| MLP | tanh hiddens | backprop / Bayes on w | complexity in \|w\| not H |
| Hopfield | x←Θ(Wx) async | Hebb outer products | ~0.14 N patterns (Hebb) |
| Boltzmann | Gibbs σ(a) | ⟨xx⟩_data − ⟨xx⟩_model | needs hiddens for high-order |
| GP | n/a (function) | evidence on kernel | infinite-net limit |

Predict with ∫ y(x;w) P(w|D) dw, not y(x;w_MP).

## Bayesian identities (always)

- Posterior ∝ likelihood × prior
- P(D|H)=∫ P(D|θ,H) P(θ|H) dθ  (Occam)
- Predictive = average over posterior, not MAP
- p-value ≠ P(H0|D)
- Linear U ⇒ decide on posterior means; buy data only if it can change the action
