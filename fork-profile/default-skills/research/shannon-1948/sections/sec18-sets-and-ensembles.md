# Section 18: Sets and Ensembles of Functions

## Core Idea
Part III treats continuous messages and signals. Shannon will not aim at “the extreme rigor of pure mathematics,” but notes the theory can be axiomatized to cover discrete, continuous, and other cases (Appendix 7). The right objects are ensembles of functions — sets equipped with probability measure — because a communication system is designed for an ensemble, not a particular waveform.

## Key Concepts
- **Set of functions**: a class of functions of time, given explicitly or by a property. Examples: f_θ(t)=sin(t+θ); all functions with no frequencies over W; bandlimited and amplitude-limited to A; all English speech waveforms.
- **Ensemble of functions**: a set plus a probability measure. “In mathematical terminology the functions belong to a measure space whose total measure is unity.” Example: sin(t+θ) with a distribution P(θ) on phase.
- **Further ensemble examples**:
  1. Finite set f_k(t) with probabilities p_k.
  2. Finite-dimensional family f(α1…αn; t) with density p(α). Example: ∑ ai sin i(ωt+φ_i) with normal independent amplitudes and uniform independent phases.
  3. f(ai; t) = ∑_{n=−∞}^{∞} a_n [sin π(2Wt−n)] / [π(2Wt−n)] with ai i.i.d. normal, variance N: “white” noise, bandlimited 0 to W, average power N.
  4. Poisson impulse (shot) noise: ∑ f(t+t_k).
  5. English speech with measure = frequency of occurrence in ordinary use.
- **Stationary**: shifting every function by a fixed time leaves the ensemble invariant. Uniform phase on the sinusoid is stationary; a fixed phase is not.
- **Ergodic**: stationary, and no subset of probability other than 0 or 1 is stationary. The pure sinusoid with uniform phase is ergodic. a sin(t+θ) with random a (normal) and uniform θ is stationary but not ergodic (the subset 0<a<1 is stationary). Examples 3 and 4 are ergodic; 5 “may perhaps be considered so.”
- **Ergodic theorem**: ensemble average of any statistic equals (with probability 1) the time average along a particular function. Citations: Birkhoff, von Neumann, Koopman; Wiener, Hopf, Hurewicz.
- **Operations on ensembles**: g = T f; measure pushed forward. Physical: filter, rectifier, modulator.
- **Invariant operator**: shifting input only shifts output. Filters and rectifiers are invariant under all translations; modulation is invariant under multiples of the carrier period. If T is invariant and the input is stationary (resp. ergodic), so is the output (Appendix 5).
- **Wiener**: invariance + linearity ⇒ Fourier analysis is the right tool. Communication theory is “heavily indebted to Wiener”; NDRC report *Interpolation, Extrapolation and Smoothing of Stationary Time Series*; also *Cybernetics*. “Communication theory is properly concerned, as has been emphasized by Wiener, not with operations on particular functions, but with operations on ensembles of functions.”

## Key Results
White noise is defined by the cardinal-series representation with i.i.d. Gaussian coefficients — “fewer limiting operations than do definitions that have been used in the past.” Shannon notes the name is optically unfortunate (white light is flat in wavelength, not frequency).

A communication system is designed “not for a particular speech function and still less for a sine wave, but for the ensemble of speech functions.”

## Key Equations
- f_θ(t) = sin(t+θ)
- bandlimited white noise: f(t) = ∑ a_n sinc(2Wt − n),  Var(a_n)=N

## Significance
This section imports stochastic-process language into communication: stationarity, ergodicity, invariant operators. It is the bridge from discrete Markoff sources to continuous sources/noise. Wiener is acknowledged as the source of the statistical time-series viewpoint.

## Connects To
- Sec 5: discrete ergodicity.
- Sec 19: sampling theorem places ensembles in 2TW-dimensional space.
- Sec 21–23: entropy of ensembles, filters, sums.
- Appendix 5: invariant operators preserve stationarity and ergodicity.
