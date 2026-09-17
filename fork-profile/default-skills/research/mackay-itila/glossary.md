# Glossary — MacKay ITILA

Alphabetical terms with chapter references. Definitions follow MacKay’s usage.

- **Activity / activation (neuron)**: activation `a = w·x`; activity/output `y = f(a)`. Do not conflate. Ch 39, 42.

- **Activity rule**: short-timescale neural dynamics (how units update given weights). Ch 38–43.

- **Architecture (neural net)**: variables and topology (who connects to whom). Ch 38.

- **Arithmetic code**: stream code that encodes a sequence as an interval in [0,1) with length ≈ P(sequence); approaches H bits/symbol without blocking. Ch 6.

- **Automatic relevance determination (ARD)**: separate weight-decay / kernel lengthscale per input; unused inputs get large α or large ℓ. Ch 44–45.

- **Bayes factor**: P(D|H0)/P(D|H1); the likelihood ratio after integrating parameters. Ch 3, 28, 37.

- **Bayesian inference**: P(θ|D) ∝ P(D|θ) P(θ). Answer questions with the posterior, not a point estimate. Ch 2–3, 21, 28, 37, 41.

- **BCJR / forward–backward**: sum–product on a trellis; bit APPs. Ch 25, 48–49.

- **Belief propagation**: see sum–product. Ch 26, 47.

- **Benford’s law**: P(first digit d) = log10(1+1/d); scale-invariant ignorance. Ch 35.

- **Bias (neuron)**: weight w0 on a clamped input x0=1. Ch 39.

- **Boltzmann distribution**: P(x) = e^{−βE(x)}/Z. Ch 31, 33, 43.

- **Boltzmann machine**: stochastic Hopfield net implementing P(x) ∝ exp(x^T W x); ML matches pairwise correlations (wake−sleep). Hidden units for higher-order stats. Ch 43.

- **Capacity C**: max I(X;Y) over input distributions; bits per use. Also: neuron capacity 2 bits/weight (Ch 40); Hopfield Hebb ~0.14 N patterns (Ch 42). Ch 9–11, 17, 40, 42.

- **Channel coding theorem**: rates R < C are achievable with Pe→0; R>C are not. Ch 9–10.

- **Clustering / mixture model**: latent class labels; K-means, soft K-means, EM for Gaussian mixtures. Ch 20, 22.

- **Coalescence / coupling from the past**: coupled MCMC trajectories merge; simulating from the past until merge by t=0 yields an exact sample from π. Ch 32.

- **Conditional entropy H(X|Y)**: E[−log P(X|Y)] = H(X,Y)−H(Y). Uncertainty in X given Y. Ch 8.

- **Confidence interval**: sampling-theory set with advertised coverage P(θ ∈ C(X)|θ). Not a posterior probability. Ch 37.

- **Content-addressable / associative memory**: complete a pattern from a noisy cue. Hopfield. Ch 38, 42.

- **Convolutional code**: linear shift-register encoder; trellis decoded. Recursive systematic form used in turbo. Ch 48.

- **Covariance function / kernel C(x,x′)**: GP covariance; encodes smoothness and scales. Ch 45.

- **Data processing inequality**: I(X;Z) ≤ I(X;Y) if X—Y—Z is a Markov chain. Ch 8.

- **Decision theory**: a* = argmax_a E[U(x,a)|a]; value of information is extra expected U from an experiment. Ch 36.

- **Deconvolution**: infer image f from d = R f + n. Wiener filter if Gaussian prior. Ch 46.

- **Density evolution**: track message PDFs of LDPC BP vs iteration; predicts thresholds. Ch 47.

- **Detailed balance**: P(x) Q(x′|x) a(x,x′) = P(x′) Q(x|x′) a(x′,x); implies P stationary for MH. Ch 29.

- **Digital fountain / LT code**: rateless XOR packets; decode from any K′≈K received on erasures. Ch 50.

- **EM algorithm**: coordinate ascent on a variational bound; E-step posterior over latents, M-step maximize expected complete log-likelihood. Ch 22, 33.

- **Entropy H(X)**: ∑ p(x) log 1/p(x). Average surprise; noiseless coding lower bound. Ch 2, 4.

- **Error-correcting code**: map K bits to N>K so that typical channel noise is correctable. Ch 1, 9–14, 47–50.

- **Evidence / marginal likelihood**: P(D|H) = ∫ P(D|θ,H) P(θ|H) dθ. Occam factor lives here. Ch 27–28, 41, 45.

- **Extrinsic information**: decoder output LLR minus channel minus prior; what turbo partners exchange. Ch 48.

- **Factor graph**: bipartite variables—factors; sum–product / min–sum. Ch 26, 47–50.

- **Feedforward network**: DAG of neurons (MLP). Ch 38, 44.

- **Free energy (variational)**: F̃ = ⟨E⟩_Q − S_Q ≥ F; minimizing F̃ tightens a lower bound on Z. Ch 33.

- **Gallager code**: synonym for LDPC. Ch 47.

- **Gaussian process (GP)**: distribution on functions; finite marginals Gaussian. Regression = linear algebra on K=C(X,X)+σ²I. Ch 45.

- **Gibbs sampling**: MCMC that draws each coordinate from its full conditional; acceptance 1. Ch 29, 31, 43.

- **Gibbs’ inequality**: D_KL(Q||P) ≥ 0. Ch 2, 33.

- **Hamming code / distance**: minimum Hamming distance d_min; can correct ⌊(d_min−1)/2⌋ errors. Ch 1, 13.

- **Hamiltonian / hybrid Monte Carlo (HMC)**: auxiliary momentum, leapfrog Hamiltonian dynamics, MH correction; kills random-walk. Ch 30.

- **Hash code**: linear map for retrieval / compression; collisions as birthday problem. Ch 12, 14.

- **Heat capacity**: C = dĒ/dT = k_B β² var(E). Fluctuation–dissipation. Ch 31.

- **Hebb rule**: Δw_ij ∝ x_i x_j; Hopfield outer-product memory. Ch 42–43.

- **Hidden Markov model**: latent chain + observations; forward–backward. Ch 25, 34.

- **Hopfield network**: symmetric recurrent net; energy E=−½x^T W x; associative memory. Ch 42.

- **Huffman code**: optimal prefix symbol code for a known discrete P; builds a tree by merging smallest masses. Ch 5.

- **ICA**: x = G s with independent non-Gaussian s; recover W=G^{−1} by ML. Ch 34.

- **Importance sampling**: E_p[f] ≈ ∑ (p/q) f(x), x~q. Dies in high-D. Ch 29.

- **Information content**: h(x) = log 1/P(x); optimal code length. Ch 4–5.

- **Intrinsic correlation function**: smoothness kernel in an image prior, distinct from blur R. Ch 46.

- **Ising model**: ±1 spins with neighbour coupling J; ferromagnet/antiferromagnet; Z, phase transition. Ch 31.

- **Joint entropy H(X,Y)**: H(X)+H(Y|X). Ch 8.

- **Junction tree**: exact inference on triangulated graphs; exponential in treewidth. Ch 26.

- **Kraft inequality**: ∑ 2^{−l_i} ≤ 1 for prefix codes. Ch 5.

- **Laplace approximation**: fit a Gaussian at a mode using the Hessian; evidence ≈ e^{−M} (2π)^{k/2} / √det A. Ch 27, 41.

- **Latent variable**: unobserved cause (class, source s, hidden unit). Ch 22, 34, 43.

- **LDPC code**: linear code with sparse H; BP decoding. Ch 47.

- **Learning rule**: long-timescale weight dynamics. Ch 38.

- **Lempel–Ziv**: universal sequential compressor; builds a dictionary of seen phrases. Ch 6.

- **Likelihood**: P(D|θ). Function of θ once D is fixed. Ch 2, 37.

- **Likelihood principle**: if two experiments yield proportional likelihood functions, inference about θ should match. Ch 37.

- **Logistic / sigmoid**: y=1/(1+e^{−a}); P(t=1|x,w) for a neuron. Ch 11, 39, 41.

- **Luria–Delbrück distribution**: heavy-tailed mutant counts; means are terrible estimators. Ch 35.

- **MAP / MP**: maximum a posteriori / most probable w_MP. A mode, not the predictive. Ch 41.

- **Markov chain Monte Carlo (MCMC)**: sample P by a chain with stationary P (MH, Gibbs, HMC). Ch 29–32.

- **MDL (minimum description length)**: model comparison via two-part codes; MacKay treats it as a cousin of evidence, inferior when priors/parameters are mishandled. Ch 28.

- **Mean field**: variational Q fully factorized; m = tanh(β J z m + …). Overconfident. Ch 33.

- **Message passing**: sum–product, min–sum, count-paths on graphs/trellises. Ch 16, 25–26.

- **Metropolis–Hastings**: propose from Q, accept with min(1, [P(x′)Q(x|x′)]/[P(x)Q(x′|x)]). Ch 29.

- **Min-sum / Viterbi**: replace sum by min (or max-product); ML path. Ch 16, 25, 48.

- **Mixture of Gaussians**: ∑ π_k N(μ_k, Σ_k); EM. Ch 22.

- **Model comparison**: posterior P(H|D) ∝ P(D|H) P(H); Occam penalty automatic in P(D|H). Ch 3, 28.

- **Monte Carlo**: E[f] ≈ (1/T) ∑ f(x^{(t)}), x~P. Ch 29.

- **Mutual information I(X;Y)**: H(X)−H(X|Y) = D_KL(P(x,y)||P(x)P(y)). Ch 8–9.

- **Noisy-channel coding**: communicate at rate R with Pe→0 iff R≤C. Ch 9–10.

- **Occam’s razor (Bayesian)**: complex models spread prior mass; P(D|H) penalizes unused flexibility. Ch 28.

- **Optimal linear filter / Wiener**: posterior mean of f under Gaussian image+noise; f̂ = W d. Ch 46.

- **Overrelaxation**: Gibbs step through the conditional mean to kill random walk. Ch 30.

- **p-value**: P(T as extreme as observed | H0). Not P(H0|data). Ch 37.

- **Parity-check matrix H**: codewords satisfy H t = 0. Ch 1, 13, 47.

- **Partition function Z**: ∑_x e^{−βE}; −ln Z = βF. Ch 31, 33, 43.

- **Posterior**: P(θ|D). Ch 2.

- **Predictive distribution**: ∫ P(t|x,w) P(w|D) dw. Ch 41, 44–45.

- **Prefix / symbol code**: uniquely decodable per-symbol code; Huffman. Ch 5.

- **Prior**: P(θ) before data. Invariance (Ch 35) and Occam (Ch 28) constrain it.

- **RA (repeat–accumulate) code**: repeat, permute, accumulate; turbo-like sparse graph. Ch 49.

- **Random-walk Metropolis**: local Gaussian proposals; mixing time ~ L²/ε². Ch 29–30.

- **Rate R**: K/N for a block code; source bits per transmission. Ch 1, 9.

- **Regularization / weight decay**: α‖w‖²; Gaussian prior. Ch 39, 41, 44.

- **Rejection sampling**: propose q, accept with p/(M q). Needs tight envelope. Ch 29.

- **Relative entropy / KL**: D_KL(Q||P)=∑ Q log Q/P. Ch 2, 33.

- **Repeat code**: naive channel code; RA is its clever cousin. Ch 1, 49.

- **Soft K-means**: assignments are responsibilities; EM for equal-variance spherical Gaussians. Ch 20, 22.

- **Source coding theorem**: you cannot compress iid ~P below H(P) bits/symbol (noiseless, typical-set). Ch 4.

- **Sparse-graph code**: LDPC, turbo, RA, fountain; decoded by iteration on a sparse factor graph. Ch 47–50.

- **Spin glass**: Ising with heterogeneous J_mn; Hopfield/Boltzmann. Ch 31, 42.

- **Sum–product algorithm**: exact on trees; loopy BP on codes. Ch 26, 47.

- **Syndrome**: z = H r; decoding as inferring noise. Ch 13, 25, 47.

- **Tanner graph**: variable/check graph of an LDPC. Ch 47.

- **Trellis**: chain-structured state diagram of a code. Ch 25, 48–49.

- **Turbo code**: parallel concatenated RSC codes + interleaver; iterative BCJR. Ch 48.

- **Typical set**: sequences with −(1/N)log P(x) ≈ H; almost all probability mass. Ch 4, 10.

- **Utility U(x,a)**: payoff; decisions maximize expected U. Ch 36.

- **Variational Bayes / variational inference**: optimize Q in a family to minimize F̃ or KL(Q||P). Ch 33.

- **Viterbi**: ML path on a trellis. Ch 25, 48.
