# Chapter 8: Waveform Channels

## Core Idea
A continuous-time channel is reduced to a discrete-time vector channel by expanding signals in an orthonormal basis. White Gaussian noise has i.i.d. Gaussian coefficients; capacity with power and bandwidth constraints follows, as do orthogonal-signal error probabilities and a treatment of nonwhite noise via Karhunen–Loève.

OCR note: narrative body missing from OCR (exercises start at line 17903). Reconstructed from ToC §8.1–8.6, Ch 1/4/5/7 cross-references, and problem headers (orthonormal expansions, white Gaussian noise, independent channels).

## Key Concepts
- Orthonormal expansion: x(t) = ∑ x_i φ_i(t), x_i = ∫ x(t) φ_i(t) dt. Finite energy L_2 signals.
- White Gaussian noise: formal process with independent N(0, N_0/2) coefficients in every orthonormal coordinate (two-sided PSD N_0/2). Exercise 8.1 makes “white” precise via bounded variance of ∫ x(t) z(t) dt for unit-energy x.
- Geometric view: ML decoding in AWGN is minimum Euclidean distance among coefficient vectors.
- Orthogonal signals: M equal-energy waveforms with ⟨s_i, s_j⟩ = 0 for i ≠ j. Error probability has an exact integral; as M → ∞, reliable communication up to C.
- Bandwidth constraint: restrict to approximately 2WT dimensions in time T and baseband width W (heuristic in §8.3). Then C ≈ W ln(1 + P/(N_0 W)) nats/second.
- Karhunen–Loève: eigen-expansion of the noise covariance; coefficients uncorrelated (hence independent if Gaussian). Converts colored noise + linear filters into parallel Gaussians.
- Power-and-frequency constraint: waterfill the noise spectrum (dual of Ch 7.5).
- Fading dispersive channels (§8.6): time-varying linear filters; diversity and noncoherent metrics appear in exercises (Rayleigh, orthogonal waveforms).

## Frameworks and Methods
- Reduce waveforms to vectors, then apply Ch 5 and Ch 7.
- Two-codeword error: Q-function of distance / √(2N_0). Many orthogonal words: union bound or exact M-ary orthogonal formula; exponent vs rate obtained as in Ch 5.
- Heuristic capacity: count degrees of freedom 2WT, energy PT, noise per dimension N_0/2, then (1/2) ln(1+SNR) per dimension.
- Colored noise: filter to whiten, or KL-expand and waterfill eigenvalues.

## Key Results and Theorems
- White Gaussian noise + orthonormal basis ⇒ independent Gaussian coordinates. Inner-product receiver is ML.
- Two equal-energy signals at Euclidean distance d: P_e = Q(d / (2 σ)) with σ^2 = N_0/2 per dimension.
- Orthogonal ensemble: P_e → 0 for rates below the capacity of the infinite-bandwidth AWGN channel, C_∞ = P / N_0 nats/second (natural units; often written P/(N_0 ln 2) bits/s).
- Bandlimited AWGN (heuristic / Shannon formula):
  C = W ln(1 + P/(N_0 W)) nats/s
  = W log_2(1 + P/(N_0 W)) bits/s.
  As W → ∞, C → P/N_0 nats/s.
- Nonwhite Gaussian noise: capacity is waterfilling on the noise PSD: power allocated to frequencies where N(f) < μ.
- Linear filters: equivalent noise after filtering is Gaussian with PSD |H(f)|^2 N(f); KL gives a discrete parallel model.
- Fading: average SNR does not determine C or the exponent; need the fading law. Orthogonal FSK-type waveforms and square-law combining appear as ML for certain Rayleigh models (cf. Exercise 7.2 / 8.21).

## Algorithms and Techniques
Waveform ML in white noise:
1. Choose an orthonormal basis spanning the signal space.
2. Compute correlations y_i = ∫ r(t) φ_i(t) dt.
3. Pick the code waveform whose coefficient vector is closest to y.

Bandlimited design:
1. Fix power P and bandwidth W.
2. Operate at R < W ln(1 + P/(N_0 W)).
3. Use a discrete-time code of block length ~ 2WT on ~2W samples/second.

Colored noise:
1. Estimate noise PSD.
2. Waterfill P(f) = (μ − N(f))_+.
3. Code in the eigenmodes (approximately: OFDM-like independent subchannels).

## Anti-patterns
- Treating analog waveforms as a DMC of samples without an orthonormal / sampling theorem justification.
- Using C = (1/2) ln(1+SNR) per sample at an arbitrary sampling rate (double-counting dimensions).
- Infinite-bandwidth reasoning at finite W: the last bits of bandwidth buy little once P/(N_0 W) is small.
- Whitening without coloring the signal constraint; waterfill jointly.
- Designing only for average fading SNR; deep fades dominate P_e unless diversity/coding is matched to the fade law.

## Key Takeaways
1. Geometry + white Gaussian coefficients is the whole continuous-time story.
2. Bandwidth is a dimension count; power is energy per dimension; waterfilling is dimension-dependent SNR allocation.
3. Orthogonal signaling is the explicit construction that meets the infinite-bandwidth limit.
4. Colored and fading channels are parallel or compound Gaussian models, not new information measures.

## Connects To
- Ch 7: each coordinate is a discrete-time Gaussian channel.
- Ch 5: error exponents for two words and for orthogonal sets.
- Ch 6: the “channel digits” of a convolutional/sequential decoder can be these coordinates.
- Ch 9: Gaussian process sources with MSE are the source dual of waveform channels.
- Ch 4.6: memory in waveforms (filters, fading) vs interlacing.
