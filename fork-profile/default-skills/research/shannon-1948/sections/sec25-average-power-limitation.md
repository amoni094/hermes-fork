# Section 25: Channel Capacity with an Average Power Limitation

## Core Idea
White thermal noise, band W, average transmitter power ≤ P: capacity is W log((P+N)/N). For arbitrary noise, C is sandwiched between W log((P+N1)/N1) and W log((P+N)/N1) with N1 the noise entropy power. Achieving the white-noise formula requires noise-like encoded signals.

## Key Concepts
- **White thermal noise**: maxent noise of power N; H(n)=W log(2πe N).
- **Entropy power of noise N1**: geometric-mean spectral power when noise is Gaussian but not flat: N1 = exp((1/W)∫_W log N(f) df).
- **Encoding for the ideal**: transmitted signals must “approximate, in statistical properties, a white noise.”

## Key Results
**Theorem 17.** Capacity of a channel of band W perturbed by white thermal noise power N, average transmitter power limited to P:

C = W log((P+N)/N)

“By sufficiently involved encoding systems we can transmit binary digits at the rate W log2((P+N)/N) bits per second, with arbitrarily small frequency of errors. It is not possible to transmit at a higher rate by any encoding system without a definite positive frequency of errors.”

Derivation: received power P+N; max H(y) when received is white of power P+N, achieved by sending white of power P. H(y)=W log(2πe(P+N)), H(n)=W log(2πe N), difference = W log((P+N)/N).

**Random noise codebook.** Construct M=2^s samples of white noise, duration T; assign binary numbers 0…M−1. Transmit the sample for each s-bit group. Receiver picks the sample of least RMS discrepancy (MAP). For almost all selections,

lim_{ε→0} lim_{T→∞} [log M(ε,T)] / T = W log((P+N)/N)

**Independent parallel work.** Formulas similar to C = W log((P+N)/N) “developed independently by several other writers, although with somewhat different interpretations”: N. Wiener, W. G. Tuller, H. Sullivan.

**Theorem 18.** Arbitrary perturbing noise:

W log((P+N1)/N1)  ≤  C  ≤  W log((P+N)/N1)

Upper: H(y) ≤ W log(2πe(P+N)), H(n)=W log(2πe N1). Lower: send white power P; entropy power of the sum ≥ P+N1 (Theorem 15).

As P increases the bounds meet; asymptotic rate W log((P+N)/N1). If the noise is white, N=N1 and Theorem 17 is recovered. If Gaussian but not flat, N1 is the geometric mean of N(f).

**Theorem 19.** Write C = W log((P+N−η)/N1). Then η is monotonic decreasing in P and η→0 as P→∞. Proof: adding extra white power to a good signal cannot decrease the entropy-power gap in the wrong direction; a large white P makes the received ensemble nearly white of power P+N.

## Key Equations
- C = W log((P+N)/N) = W log(1 + P/N)   (white noise)
- W log((P+N1)/N1) ≤ C ≤ W log((P+N)/N1)
- N1 = exp((1/W) ∫ log N(f) df)   (Gaussian colored noise)

## Significance
The Shannon–Hartley formula. It founded the SNR–bandwidth tradeoff, the idea of noise-like signaling (spread spectrum, coded modulation), and the geometric sphere-packing view (developed in the IRE 1949 paper). Theorems 18–19 are the first entropy-power bounds on non-AWGN capacity.

## Connects To
- Theorem 16: C = max H(y)−H(n).
- Theorem 15: EPI for the lower bound.
- Sec 26: peak instead of average power.
- Sec 19: 2TW-dimensional spheres.
