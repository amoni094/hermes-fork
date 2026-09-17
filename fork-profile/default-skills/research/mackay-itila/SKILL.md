---
name: mackay-itila
description: "Knowledge base from Information Theory, Inference, and Learning Algorithms by David MacKay (2003). Use when applying information theory concepts, channel coding, source coding, Bayesian inference, neural networks, or referencing MacKay frameworks."
related_skills:
  - shannon-1948
  - cover-thomas-eit
  - gallager-itrc
---

# MacKay ITILA

David J.C. MacKay, *Information Theory, Inference, and Learning Algorithms* (CUP, 2003). One book, one thesis: **probability is the calculus of inference; information measures are expected log-probabilities; codes that work are sparse graphs + message passing; learning is inference of parameters or functions.**

When working a problem, prefer MacKay’s move: write P(data | hypothesis), say what is latent, then pick an algorithm from the cheatsheet (exact → Laplace/variational → MCMC → message passing).

## Core Frameworks

### Shannon entropy and information measures
h(x)=log 1/P(x) is the ideal code length. H(X)=E[h(X)] is the average. Joint/conditional entropies obey the chain rule; I(X;Y)=H(X)−H(X|Y) is reduction in uncertainty (also KL between the joint and the product of marginals). Gibbs: D_KL(Q||P)≥0. Data processing: no post-processing of Y increases I(X;·). Typical sets of size ~2^{nH} carry essentially all probability — this is the engine of both source and channel theorems.

### Source coding (noiseless)
You cannot beat H bits/symbol for iid ~P (Ch 4). Huffman: optimal *integer* prefix lengths, waste <1 bit/symbol (Ch 5). Arithmetic: interval coding, L/n→H, plugs into any sequential model (Ch 6). Lempel–Ziv: universal, no explicit P, slower to approach H. Compression *is* modelling: a better P is a better code.

### Channel coding (noisy)
A channel is P(y|x). Capacity C=max_{P(x)} I(X;Y). BSC: C=1−H_2(f). BEC: C=1−f. AWGN: ½ log(1+SNR). Shannon: R<C achievable with Pe→0 using random codes; R>C impossible (Ch 9–10). Practical codes that approach C are **sparse-graph codes** decoded by iterative sum–product, not algebraic perfect codes: LDPC/Gallager (Ch 47), turbo (Ch 48), repeat–accumulate (Ch 49), digital fountains for erasures (Ch 50). Hamming/BCH are pedagogy and short-block tools (Ch 1, 13).

### Bayesian inference
P(θ|D)∝P(D|θ)P(θ). Predictions integrate the posterior, they do not plug in θ_MAP. Model comparison uses the evidence P(D|H)=∫P(D|θ,H)P(θ|H)dθ — this *is* Occam’s razor (Ch 28). Laplace turns a mode+Hessian into an evidence estimate (Ch 27). p-values are not posterior probabilities (Ch 37). Decision theory is trivial: maximize E[U|a]; experiments have value only if they can change the action (Ch 36).

### Monte Carlo and approximations
When you cannot sum: importance/rejection (low-D), MH, Gibbs, HMC (kill random-walk), annealing for modes, CFTP for exact samples (Ch 29–32). Variational free energy F̃=⟨E⟩_Q−S_Q≥F gives a bound and a factorized (mean-field) posterior (Ch 33). EM is coordinate ascent on that bound with a point estimate of θ (Ch 22).

### Neural networks and learning
Specify architecture, activity rule, learning rule (Ch 38). A logistic neuron is logistic regression / Gaussian posterior odds (Ch 39); threshold capacity is 2 bits/weight (Ch 40). Regularized training M(w)=G+αE_W is −log posterior; predict by averaging (Ch 41). Hopfield: symmetric recurrent energy, Hebb memory, ~0.14N patterns (Ch 42). Boltzmann: Gibbs on that energy; ML matches pairwise moments; hiddens for higher-order stats (Ch 43). MLPs: backprop; complexity lives in weight scales, not H; large-H Bayes nets are GPs (Ch 44–45). Deconvolution is inference of f given blur R, not “inverting a matrix” (Ch 46).

## Chapter Index

| Ch | Title | Key topics |
|----|-------|------------|
| 1 | Introduction to Information Theory | BSC, repetition vs Hamming, Shannon limit |
| 2 | Probability, Entropy, and Inference | ensembles, H, Gibbs, Jensen |
| 3 | More about Inference | bent coin, model comparison, legal evidence |
| 4 | The Source Coding Theorem | typicality, H as compressibility |
| 5 | Symbol Codes | Kraft, Huffman, integer-length gap |
| 6 | Stream Codes | arithmetic, LZ, guessing game |
| 7 | Codes for Integers | prefix codes for unbounded alphabets |
| 8 | Dependent Random Variables | H(X,Y), I(X;Y), chain rule |
| 9 | Communication over a Noisy Channel | C=max I(X;Y), inference of inputs |
| 10 | The Noisy-Channel Coding Theorem | jointly typical, achievability |
| 11 | Error-Correcting Codes and Real Channels | Gaussian channel, practical codes |
| 12 | Hash Codes | retrieval, collisions, birthday |
| 13 | Binary Codes | distance, perfect codes, union bound |
| 14 | Very Good Linear Codes Exist | random linear, hashing as compression |
| 15 | Further Exercises on Information Theory | extra drills |
| 16 | Message Passing | path counting, min-sum |
| 17 | Constrained Noiseless Channels | capacity via counting / eigenvalues |
| 18 | Crosswords and Codebreaking | language models as sources |
| 19 | Why have Sex? | information acquisition, mutation load |
| 20 | Clustering | soft K-means |
| 21 | Exact Inference by Complete Enumeration | discrete Bayes nets, burglar alarm |
| 22 | Maximum Likelihood and Clustering | GMM, EM |
| 23 | Useful Probability Distributions | Gaussian, Gamma, periodic |
| 24 | Exact Marginalization | Gaussian mean/variance |
| 25 | Exact Marginalization in Trellises | BCJR, Viterbi |
| 26 | Exact Marginalization in Graphs | sum–product, junction tree |
| 27 | Laplace’s Method | Gaussian evidence |
| 28 | Model Comparison and Occam’s Razor | evidence, MDL |
| 29 | Monte Carlo Methods | IS, rejection, MH, Gibbs, slice |
| 30 | Efficient Monte Carlo Methods | HMC, overrelaxation, annealing |
| 31 | Ising Models | magnets, C∝var(E), MC vs exact Z |
| 32 | Exact Monte Carlo Sampling | coupling from the past |
| 33 | Variational Methods | free energy, mean field |
| 34 | Independent Component Analysis | latent linear mixing, non-Gaussian |
| 35 | Random Inference Topics | Benford, Luria–Delbrück, causation |
| 36 | Decision Theory | expected utility, value of information |
| 37 | Bayesian Inference and Sampling Theory | p-values vs posterior |
| 38 | Introduction to Neural Networks | associative vs RAM; three rules |
| 39 | The Single Neuron as a Classifier | logistic, weight space, regularization |
| 40 | Capacity of a Single Neuron | 2 bits/weight, T(N,K) |
| 41 | Learning as Inference | M(w) as −log posterior, predict by averaging |
| 42 | Hopfield Networks | Hebb, energy, capacity ~0.14 |
| 43 | Boltzmann Machines | wake–sleep, hidden units |
| 44 | Supervised Learning in Multilayer Networks | MLP, backprop, Bayes, Neal limit |
| 45 | Gaussian Processes | kernel regression, evidence on C |
| 46 | Deconvolution | Wiener filter, image priors |
| 47 | Low-Density Parity-Check Codes | Gallager, BP, density evolution |
| 48 | Convolutional Codes and Turbo Codes | taps, trellis, iterative BCJR |
| 49 | Repeat–Accumulate Codes | repeat–permute–accumulate |
| 50 | Digital Fountain Codes | LT, rateless erasures |

## Topic Index

- arithmetic coding → 6
- Bayesian inference / posterior / prior / likelihood → 2, 3, 21, 28, 37, 41
- Boltzmann machine → 43
- capacity (channel) → 9–11, 17
- capacity (neuron / Hopfield) → 40, 42
- clustering / EM / mixtures → 20, 22
- convolutional / turbo → 25, 48
- decision theory / utility → 36
- deconvolution / Wiener → 46
- entropy, H(X), H(X,Y), H(X|Y), I(X;Y) → 2, 4, 8
- fountain / LT / erasures → 50
- Gaussian processes / kernels → 45
- Gibbs / MH / HMC / MCMC → 29–32
- Hopfield / Hebb / associative memory → 38, 42
- Huffman → 5
- ICA / latent variables → 22, 34, 43
- Ising / partition function / heat capacity → 31
- Laplace / Occam / MDL / evidence → 27, 28
- LDPC / Gallager / BP → 26, 47
- Lempel–Ziv → 6
- message passing / sum–product / trellis → 16, 25, 26
- Monte Carlo exact (CFTP) → 32
- multilayer perceptron / backprop → 44
- p-values / sampling theory → 37
- RA codes → 49
- source coding theorem → 4
- variational / mean field → 33

## Supporting files

- [glossary.md](glossary.md) — terms with chapter refs
- [patterns.md](patterns.md) — algorithms: when / how / trade-offs / MacKay insight
- [cheatsheet.md](cheatsheet.md) — formulas, capacity, method selection
- [chapters/](chapters/) — one file per chapter (`chNN-slug.md`)
