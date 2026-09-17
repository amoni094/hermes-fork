# Section 22: Entropy Loss in Linear Filters

## Core Idea
Passing an ensemble through a linear filter Y(f) adds (1/W) ∫_W log |Y(f)|² df to the entropy per degree of freedom — the log of the geometric-mean power gain. Entropy power is multiplied by that mean gain.

## Key Concepts
- **Filter as linear coordinate change**: frequency components are multiplied by Y(f); the Jacobian is diagonal in sine/cosine coordinates.
- **Entropy power factor**: output N1 times exp((1/W)∫ log |Y|²). If gain is in dB, entropy power (dB) increases by the arithmetic mean dB gain over W.
- **Table I**: entropy power factor, dB, and impulse response for several ideal |Y| on [0,1] (phase 0, W=1/2). Examples include (1−ω), (1−ω²), (1−ω³), √(1−ω²), etc. First case factor 1/e² ≈ −8.69 dB.

## Key Results
**Theorem 14.** If an ensemble with entropy H1 per degree of freedom in band W is passed through a filter with characteristic Y(f), the output has entropy

H2 = H1 + (1/W) ∫_W log |Y(f)|² df

Proof: n sine + n cosine components; J = ∏ |Y(f_i)|² → exp((1/W)∫ log |Y|²). J constant, so E[log J] = log J; apply the coordinate-change formula of Sec 20.

**Corollaries.** Measure-preserving warps of the frequency axis leave the factor unchanged: a linearly increasing gain G(ω)=ω and a sawtooth between 0 and 1 have the same loss as 1−ω. Reciprocal gain ⇒ reciprocal factor. Raising gain to a power raises the factor to that power.

## Key Equations
- H2 = H1 + (1/W) ∫ log |Y(f)|² df
- N1,out = N1,in · exp((1/W) ∫ log |Y|² df)
- J = ∏ |Y(f_i)|²

## Significance
This is the information-theoretic accounting for linear filtering: the geometric mean of |Y|², not the arithmetic mean power gain, governs entropy. It is used in Sec 26 (triangular filter for peak-limited ensembles) and underlies later waterfilling intuition (entropy is additive in log-spectrum).

## Connects To
- Sec 20.9: H(y)=H(x)+log|A| for linear maps.
- Sec 18: invariant linear operators and Fourier analysis (Wiener).
- Sec 26: triangular |Y| with ∫ log G² = −2W, used to enforce a peak constraint at all t.
