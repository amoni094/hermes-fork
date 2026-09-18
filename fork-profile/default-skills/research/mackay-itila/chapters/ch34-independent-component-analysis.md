# Chapter 34: Independent Component Analysis and Latent Variable Modelling

## Core Idea
Many models explain observations x via simpler latent s. ICA is the simplest continuous latent-variable model: x = G s, noise-free, square mixing, independent non-Gaussian sources. Maximum likelihood on W = G^{−1} recovers the sources; a Gaussian prior on s cannot, because of rotational invariance.

## Key Concepts
- **Generative / latent-variable model**: P(observables, latents). Examples: mixtures (Ch 22), HMMs, factor analysis, and *decoding* (s = source bits, G = generator matrix).
- **ICA generative model**: x = G s with s_i iid from p_i(s_i), usually I = J (square).
- **Identifiability**: sources recoverable up to permutation and scaling, *only if* they are non-Gaussian (or at most one Gaussian).
- **Unmixing matrix**: W ≡ G^{−1}; a = W x should look like independent sources.
- **Score function**: φ_i(a_i) = d ln p_i(a_i)/da_i. Popular: φ = −tanh (sparse / super-Gaussian sources).
- **Noise-free assumption**: rare in general latent modelling; it makes the likelihood a Jacobian term plus ∑ ln p_i(W x).

## Frameworks and Methods
- **Latent-variable unification**: clustering, ICA, factor analysis, and channel coding are the same cartoon: independent s, linear or structured G, observed x.
- **ML ICA (Bell–Sejnowski / MacKay gradient)**: maximize ln|det W| + ∑ ln p_i(W x) by stochastic gradient on each datapoint.
- **Why not PCA / Gaussian latents**: φ linear ⇔ Gaussian p_i ⇔ likelihood invariant to rotation of s. PCA finds variance axes, not independent causes.
- **Online rule**: ΔW ∝ [W^{−T} + z x^T] with z_i = φ_i(a_i). Natural gradient often uses ΔW ∝ (I + z a^T) W.

## Key Equations
- x = G s
- P(x,s | G) involves ∏_j δ(x_j − (G s)_j) ∏_i p_i(s_i)
- ln P(x | G) = −ln|det G| + ∑_i ln p_i((G^{−1} x)_i)
- ln P(x | W) = ln|det W| + ∑_i ln p_i(W_{i·} x)
- φ_i(a_i) = d ln p_i / da_i
- ∂ ln P / ∂W_{ij} = G_{ji} + x_j z_i   (z = φ(a))
- ΔW ∝ W^{−T} + z x^T
- Jacobian identities: ∂ ln det W / ∂W_{ij} = W^{-1}_{ji}

## Algorithms and Techniques
**Online ICA (one datapoint)**
1. a ← W x
2. z_i ← φ_i(a_i)  (e.g. −tanh a_i)
3. ΔW ∝ W^{−T} + z x^T   (or natural gradient (I + z a^T) W)
4. Optionally constrain rows of W, or recover scaling separately.

**Batch**
1. Centre (and often whiten) x so covariance is I — reduces W to a rotation.
2. Iterate the gradient / FastICA-style fixed point.
3. Permute/scale outputs to taste.

## Anti-patterns
- **Gaussian sources / linear φ**: algorithm has no preferred alignment.
- **Ignoring permutation/scale ambiguity** when comparing recovered s to ground truth (use correlation, not MSE on raw s).
- **Noise-free ICA on very noisy sensors** — use a noisy generative model (factor analysis / ICA with noise).
- **Assuming I=J when there are more sources than sensors**.

## Key Takeaways
1. ICA is ML in a linear, independent, non-Gaussian latent model.
2. Independence + non-Gaussianity, not mere decorrelation, recovers G.
3. The Jacobian ln|det W| is the volume correction from s-space to x-space.
4. Coding, clustering, and ICA share the latent-variable cartoon; only G and p(s) change.
5. φ encodes your prior on source shape (heavy-tailed vs sub-Gaussian).

## Connects To
- **Ch 22**: mixture models — discrete latents instead of continuous s.
- **Ch 8–10**: G as a coding matrix; decoding is latent inference with known G.
- **Ch 33**: variational treatment when noise or posterior over G is hard.
- **Ch 45**: another route from parametric maps to priors on functions / sources.
