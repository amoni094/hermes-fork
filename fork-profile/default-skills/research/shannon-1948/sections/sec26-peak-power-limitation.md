# Section 26: The Channel Capacity with a Peak Power Limitation

## Core Idea
When the transmitter is limited by peak instantaneous power S rather than average power P, maximizing H(y) − H(n) is harder. Shannon gives a lower bound valid for all S/N, an asymptotic upper bound for large S/N, and shows C ∼ W log(1 + S/N) as S/N → 0 (band starting at 0).

## Key Concepts
- **Constraint**: every f(t) in the ensemble satisfies |f(t)| ≤ √S for all t.
- **Weakening**: limiting power only at the sample points is easier and upper-bounds entropy of the transmitted ensemble.
- **Triangular filter**: unit gain at DC, linear to 0 at W. Converts a sample-peak-limited ensemble into a time-peak-limited one, at a known entropy-power cost (Theorem 14). The cardinal pulse becomes a never-negative sin²/(W t)² pulse, so the worst-case peak is the DC of amplitude √S.

## Key Results
**Theorem 20.** The channel capacity C for a band W perturbed by white thermal noise of power N is bounded by

C ≥ W log (2S / (π e N))

where S is the peak allowed transmitter power. For sufficiently large S/N,

C ≤ W log [ (2/(π e)) ((S+N)/N) (1+ε) ]

where ε is arbitrarily small. As S/N → 0 (and provided the band W starts at 0),

C / [ W log(1 + S/N) ] → 1.

**Upper bound.** Relax the constraint to sample instants only. Max entropy: independent samples uniform on [−√S, √S]; transmitted entropy = W log 4S. Received entropy < W log(4S + 2π e N)(1+ε) as S/N → ∞. Subtract white-noise entropy W log(2π e N):

W log(4S + 2π e N)(1+ε) − W log(2π e N) = W log[ (2/(π e)) ((S+N)/N) (1+ε) ]

This upper-bounds C because the relaxed ensemble is larger.

**Lower bound.** Pass the same sample-uniform ensemble through the triangular filter. Output never exceeds peak S (non-negative pulses; all coefficients +√S reproduces DC of amplitude √S; unit DC gain). Geometric-mean gain:

∫_0^W log G² df = ∫_0^W log((W−f)/W)² df = −2W

Output entropy = W log 4S − 2W = W log(4S/e²). Capacity is then greater than W log(2S/(π e N)).

**Small S/N.** Average power P ≤ S, so C ≤ W log(1 + P/N) ≤ W log(1 + S/N) by Theorem 17. For a matching lower bound: blocks of t samples equal to ±√S at random (probability 1/2), triangular filter (peak still S), average power → S for large t. Theorem 15 (small-signal absorption) applies if √(S/t)/N is small, which is arranged by taking S/N small after t is chosen. Entropy power of signal+noise → S+N, rate → W log((S+N)/N).

## Key Equations
- C ≥ W log((2/(π e)) (S/N))
- C ≤ W log((2/(π e)) (S+N)/N · (1+ε))   (large S/N)
- C ∼ W log(1 + S/N)    (S/N → 0, band from 0)
- sample-uniform entropy: W log 4S
- triangular factor: (1/W) ∫ log G² df = −2

## Significance
Peak constraints are the realistic high-power-amplifier limit. The factor 2/(π e) ≈ 0.234 versus 1 in the average-power formula is the high-SNR peak-to-average information-theoretic penalty. At low SNR, peak and average constraints coincide. Theorem 17 still upper-bounds C because P ≤ S.

## Connects To
- Theorem 14: entropy loss of the triangular filter.
- Theorem 15: small-signal absorption for the S/N → 0 limit.
- Theorem 17: average-power formula C = W log((P+N)/N), which upper-bounds any peak-limited C.
