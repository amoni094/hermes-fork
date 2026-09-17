# Section 19: Band Limited Ensembles of Functions

## Core Idea
A function limited to frequencies 0…W Hz is determined by its samples at rate 2W. Functions of band W and duration T live in a space of 2TW dimensions; ensembles become probability densities on that space.

## Key Concepts
- **Degrees of freedom**: 2TW coordinates for duration T, band W.
- **Function space**: each bandlimited f corresponds to one point (the sample vector); the cardinal basis is orthogonal.
- **Energy balls**: functions of total energy ≤ E correspond to a 2TW-dimensional sphere of radius √(2WE).
- **Ensembles of limited duration and band**: density p(x1,…,xn) on n-space. If not time-limited, the 2TW coordinates in an interval T represent “substantially the part of the function in the interval T.”

## Key Results
**Theorem 13 (sampling theorem).** Let f(t) contain no frequencies over W. Then

f(t) = ∑_{n=−∞}^{∞} X_n  [sin π(2Wt − n)] / [π(2Wt − n)]

where X_n = f(n/(2W)).

Proof deferred to Shannon’s companion paper “Communication in the Presence of Noise,” Proc. IRE 37(1), Jan. 1949, pp. 10–21. (Nyquist and Whittaker are in the background; Shannon’s statement is the communication-theory form.)

A function “substantially limited to a time T” has all X_n outside that interval zero, hence all but 2TW coordinates zero.

## Key Equations
- f(t) = ∑ X_n sinc(2Wt − n),  X_n = f(n/(2W))
- dimension = 2TW
- energy ≤ E  ⇔  radius r = √(2W E)

## Significance
This is the Nyquist–Shannon sampling theorem as used in information theory: it converts continuous-time problems into finite-dimensional geometry. Capacity, entropy power, and sphere-packing arguments in Parts IV–V all live in this 2TW-space. PCM and digital audio rest on it.

## Connects To
- Sec 18: white noise as i.i.d. Gaussians on the samples.
- Sec 21: entropy per degree of freedom H' on p(x1…xn); H = 2W H'.
- Sec 24–26: continuous channel capacity in the same coordinates.
- IRE 1949 paper: geometric proof and the sphere-packing picture of Theorem 17.
