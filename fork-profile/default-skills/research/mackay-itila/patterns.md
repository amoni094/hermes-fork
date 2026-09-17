# Patterns — Algorithms and Techniques (MacKay ITILA)

Each entry: when to use, how it works, trade-offs, MacKay’s key insight.

## Huffman coding

**When to use**: Known discrete symbol distribution; you need a prefix code; alphabet not huge; you can tolerate integer lengths.

**How it works**: Merge the two smallest probabilities iteratively; assign 0/1 on the tree. Length l_i ≈ log2(1/p_i). Satisfies Kraft.

**Trade-offs**: Optimal among *symbol* codes. Wastes up to almost 1 bit/symbol if one p≈1. Bad for adaptive or huge alphabets. Not for channels (that is error-correction).

**MacKay’s insight**: The bound is H ≤ L < H+1 per symbol. If that +1 hurts, switch to stream codes (Ch 5–6). Huffman is not “the” compressor.

## Arithmetic coding

**When to use**: You have P(x_t | x_<t) (even adaptive); you want to approach H without blocking.

**How it works**: Represent the sequence as a subinterval of [0,1) whose width is the sequence probability; send enough bits to name a point in the interval.

**Trade-offs**: Near-optimal, handles fractional bits, easy to couple to any generative model. Implementation care (precision, termination). Patent history (less relevant now).

**MacKay’s insight**: Compression *is* probabilistic modelling. Any P you can evaluate, you can arithmetic-code. Guessing game ≡ coding (Ch 6).

## Lempel–Ziv

**When to use**: Unknown source, one-pass, no explicit model; files/text.

**How it works**: Parse into unseen phrases; send pointer + new symbol (LZ78) or match length into a window (LZ77). Universal: rate → H for ergodic sources.

**Trade-offs**: Asymptotically optimal, no prior. Slow to approach H on small data; worse than a good arithmetic+model on short text.

**MacKay’s insight**: Universality is real but not magic — a well-matched model still wins at practical N (Ch 6).

## LDPC decoding (belief propagation / sum–product)

**When to use**: Sparse H, memoryless channel, large N; you want near-Shannon performance.

**How it works**: Iterate bit↔check messages (tanh rule on LLRs). Stop when H t̂ = 0 or iteration cap. Density evolution designs degree distributions.

**Trade-offs**: Linear time per iteration, excellent waterfall. Error floors from trapping sets. Not ML. Needs sparsity and large N. Encoding needs extra structure if you want O(N).

**MacKay’s insight**: Random sparse graphs + message passing *are* the constructive Shannon theorem. Algebraic perfect codes were a detour (Ch 1, 13, 47).

## Turbo decoding

**When to use**: Concatenated convolutional codes; similar regime to LDPC.

**How it works**: Two BCJR decoders exchange extrinsic LLRs through an interleaver.

**Trade-offs**: Excellent for moderate N; error floors if the interleaver/weight spectrum is poor. Recursive systematic constituents matter.

**MacKay’s insight**: Iterative APP decoding on a loopy graph, not a better Viterbi, is what approaches C (Ch 25, 48).

## Repeat–accumulate encoding/decoding

**When to use**: You want a Shannon-good code that is trivial to explain and encode.

**How it works**: Repeat q, permute, accumulate. Decode: BCJR on the accumulator + equality nodes.

**Trade-offs**: Rate 1/q unless punctured. Error floor around 10^{−4} block in simple regular RA. Decoding-time power laws.

**MacKay’s insight**: Complexity of the *description* is not complexity of the *code* (Ch 1 vs 49).

## Digital fountain (LT) encoding/decoding

**When to use**: Erasures, unknown/variable f, broadcast, streaming; packet networks.

**How it works**: Emit endless random sparse XORs with a soliton-like degree distribution. Peel degree-1 packets.

**Trade-offs**: Rateless, ~5% overhead, O(K log K). For noisy (non-erasure) channels use LDPC/turbo, not LT as-is.

**MacKay’s insight**: Feedback ACKs are Shannon-redundant; the coupon collector is what you get if you never XOR (Ch 50).

## EM algorithm

**When to use**: Latent-variable models with tractable P(latent|data,θ) and tractable complete-data M-step (mixtures, etc.).

**How it works**: E: compute responsibilities. M: maximize expected complete log-likelihood. Equivalent to coordinate ascent on a variational bound.

**Trade-offs**: Monotone in likelihood; local maxima; no posterior uncertainty on θ. Soft K-means is EM with tied spherical covariances.

**MacKay’s insight**: EM is not a rival to Bayes — it is incomplete Bayes (point θ, averaged latents) (Ch 22, 33).

## Gibbs sampling

**When to use**: Full conditionals are easy (Ising, Dirichlet-multinomial, conjugate GMMs, Boltzmann machines).

**How it works**: For i in 1..d: x_i ~ P(x_i | x_{−i}). Stationary distribution is the joint.

**Trade-offs**: No tuning of proposals. Slow if variables are tightly coupled (random walk along the long axis). Overrelaxation or blocking helps.

**MacKay’s insight**: Acceptance probability 1 does not mean mixing is fast (Ch 29, 31).

## Metropolis–Hastings

**When to use**: You can evaluate P(x) up to Z; conditionals are ugly.

**How it works**: Propose x′~Q(·|x); accept with a=min(1, P(x′)Q(x|x′)/[P(x)Q(x′|x)]).

**Trade-offs**: Universal. Random-walk Q crawls in high-D (time L²/ε²). Step size: too small slow, too large rejected.

**MacKay’s insight**: The algorithm is easy; *diagnosing mixing* is the subject (Ch 29). Exact sampling (Ch 32) is how you know you are done.

## Hamiltonian Monte Carlo

**When to use**: Continuous θ, cheap ∇ log P, high dimension.

**How it works**: Draw momentum p; leapfrog L steps; MH on Hamiltonian. Requires symplectic reversible integrator.

**Trade-offs**: Huge ESS gain vs RWM. Tune ε, L, mass M. Discrete spaces: not applicable (use cluster/Gibbs).

**MacKay’s insight**: Momentum exists to *suppress* random walk. L=1 leapfrog is just Langevin (Ch 30).

## Coupling from the past

**When to use**: You need unbiased samples and a monotone (or small) state space — Ising, some perfect-simulation settings.

**How it works**: Coupled updates from T0<0 with reused RNG; double |T0| until all (or bound) chains coalesce by time 0.

**Trade-offs**: Exactness. Runtime tails can be nasty near criticality. Forward coalescence alone is biased.

**MacKay’s insight**: Mixing time is unknown — so construct a proof of equilibrium instead of a heuristic (Ch 32).

## Laplace approximation

**When to use**: Unimodal posterior, large N, you need evidence and local error bars (neural nets, hyperparameters).

**How it works**: Mode w_MP; A=∇∇M; Gaussian N(w_MP, A^{−1}); ln Z ≈ −M + ½ ln(2π)^k / det A.

**Trade-offs**: Fast, differentiable evidence. Fails on multimodality, heavy tails, discrete variables. Overconfident if Hessian misses flat directions.

**MacKay’s insight**: This is how Occam’s razor becomes a number you can optimize for α (Ch 27–28, 41).

## Variational Bayes / mean field

**When to use**: Intractable Z; you want a bound and a fast approximate posterior; factorized Q is acceptable.

**How it works**: Minimize F̃ = ⟨E⟩_Q − S_Q over Q in a family (often fully factorized). Coordinate ascent; often conjugate updates.

**Trade-offs**: Optimization, not sampling. Bound on ln Z (direction D_KL(Q||P) underestimates variance). Mean-field Ising has the wrong critical behaviour in low-D.

**MacKay’s insight**: Mean-field physics *is* variational inference; Gibbs’ inequality is the whole justification (Ch 33).

## Gaussian process regression

**When to use**: Nonlinear regression/classification with N ≲ 10^3, need error bars and a transparent prior on functions.

**How it works**: Choose C_θ; K=C(X,X)+σ²I; ȳ_*= C_* K^{−1} t; var from Schur complement. Learn θ by evidence.

**Trade-offs**: O(N³), O(N²) storage. Classification needs Laplace/EP/MCMC. Kernel choice is the model.

**MacKay’s insight**: Infinite MLPs *are* GPs — stop optimizing w and condition the process (Ch 44–45).

## Optimal linear (Wiener) deconvolution

**When to use**: Known blur R, roughly Gaussian noise, you need a baseline reconstructor.

**How it works**: f_MP = (R^T R + λ C)^{−1} R^T d. In Fourier domain if R is convolution.

**Trade-offs**: Closed form, error bars. Negative flux, ringing — prior mismatch. Not a law of nature.

**MacKay’s insight**: “Optimal linear” is posterior mean under a bad image model; change P(f), not the linear algebra (Ch 46).

## ICA (ML unmixing)

**When to use**: Linear mixtures, square, little noise, independent non-Gaussian sources (audio, sensors).

**How it works**: a=Wx; z=φ(a); ΔW ∝ W^{−T} + z x^T (or natural gradient).

**Trade-offs**: Permutation/scale ambiguity. Gaussian sources unidentifiable. Noise-free assumption is brittle.

**MacKay’s insight**: Decorrelation is not enough; non-Gaussianity breaks rotational symmetry (Ch 34).
