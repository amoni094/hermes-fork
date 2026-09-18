# Glossary — Shannon 1948 notation and definitions

Quotations are Shannon’s wording or immediate close paraphrase. He writes H(x), Hx(y), Hy(x) — not H(X), H(Y|X). He does not use the names “mutual information” or “rate-distortion function.”

## Information and units
- **Fundamental problem of communication**: “reproducing at one point either exactly or approximately a message selected at another point.”
- **Semantic irrelevance**: “These semantic aspects of communication are irrelevant to the engineering problem.”
- **Bit**: log base 2; “binary digits, or more briefly bits, a word suggested by J. W. Tukey.”
- **Logarithmic measure**: chosen because (1) engineering parameters vary linearly with log of the number of possibilities, (2) it matches intuition (two punched cards ≈ twice one), (3) limiting operations are simple.

## Discrete entropy
- **Entropy of a set of probabilities**: H = −∑ pi log pi. “If x is a chance variable we will write H(x) for its entropy; thus x is not an argument of a function but a label for a number.”
- **Joint entropy**: H(x,y) = −∑_{i,j} p(i,j) log p(i,j).
- **Conditional entropy** Hx(y) = −∑_{i,j} p(i,j) log pi(j), with pi(j) = p(i,j)/∑j p(i,j). “This quantity measures how uncertain we are of y on the average when we know x.”
- **Chain rule**: H(x,y) = H(x) + Hx(y) = H(y) + Hy(x).
- **Independence bound**: H(x,y) ≤ H(x)+H(y), equality iff p(i,j)=p(i)p(j).
- **Conditioning**: H(y) ≥ Hx(y); “The uncertainty of y is never increased by knowledge of x.”
- **Source entropy per symbol**: H = ∑i Pi Hi = −∑_{i,j} Pi pi(j) log pi(j) (finite-state Markoff source).
- **Entropy per second**: H′ = m H (m = symbols/s). Shannon also uses H′ for continuous entropy per degree of freedom — context distinguishes.
- **GN**: entropy per symbol of N-blocks. **FN**: conditional entropy of the next symbol given N−1 predecessors. Both ↓ H.
- **Relative entropy** (Shannon’s usage, not KL): H / log(alphabet size). “The maximum compression possible when we encode into the same alphabet.”
- **Redundancy**: 1 − relative entropy. English ≈ 50% “not considering statistical structure over greater distances than about eight letters.”

## Typical sequences
- **AEP (Theorem 3)**: (log p^{−1})/N → H for almost all long sequences.
- **Typical set size (Theorem 4)**: “treat the long sequences as though there were just 2^{HN} of them, each with a probability 2^{−HN}.”

## Channel (discrete, noiseless)
- **Discrete channel**: transmits sequences from a finite set of symbols Si of durations ti, possibly with state constraints on allowed sequences.
- **Capacity (noiseless)**: C = lim_{T→∞} (log N(T))/T, N(T) = number of allowed signals of duration T. Equal to log W, W largest real root of the characteristic equation (Appendix 1).
- **Theorem 9**: encode a source of entropy H to send C/H − ε source symbols/s; no faster.

## Noise, equivocation, rate
- **Noise vs distortion**: received signal a definite invertible function of the transmitted ⇒ distortion (invertible). Otherwise noise.
- **Equivocation**: Hy(x), “the average ambiguity of the received signal”; “the amount of this information which is missing in the received signal.”
- **Rate of transmission** (unnamed mutual information):

R = H(x) − Hy(x) = H(y) − Hx(y) = H(x) + H(y) − H(x,y)

“All three expressions have a certain intuitive significance.”
- **Capacity (noisy)**: C = Max [H(x) − Hy(x)], maximum over input sources. Theorem 11: H ≤ C ⇒ arbitrarily small error (or equivocation); H > C ⇒ equivocation ≥ H−C.
- **Theorem 12**: lim (log N(T,q))/T = C for error probability q ≠ 0,1. N(T,q) = max codebook size with P(error) ≤ q.
- **Correction channel (Theorem 10)**: a side channel of capacity Hy(x) can correct all but an arbitrarily small fraction of errors; less capacity cannot.

## Continuous entropy and ensembles
- **Ensemble of functions**: a set of time-functions with a probability measure (“measure space whose total measure is unity”).
- **Stationary**: time-shift invariant. **Ergodic**: no stationary subset of probability other than 0 or 1. Time averages = ensemble averages (probability 1).
- **Continuous entropy**: H = −∫ p(x) log p(x) dx. Relative to coordinates; can be negative. “The scale of measurements sets an arbitrary zero corresponding to a uniform distribution over a unit volume.”
- **Change of coordinates**: H(y) = H(x) − ∫ p(x) log |J(x/y)| dx. Linear: + log |aij|.
- **Gaussian**: H = log √(2π e) σ (1-D); n-D: log (2π e)^{n/2} |aij|^{−1/2}.
- **Sampling theorem (Theorem 13)**: bandlimited to W, f(t) = ∑ Xn sinc(2Wt − n), Xn = f(n/(2W)). Dimension 2TW in time T.
- **Entropy per degree of freedom**: H′ = lim (−1/n) ∫ p log p. **Per second**: H = 2W H′.
- **Entropy power N1**: “the power in a white noise limited to the same band as the original ensemble and having the same entropy.” N1 = exp(2H′)/(2π e). N1 ≤ actual power, equality iff white.
- **White noise**: i.i.d. Gaussian samples in the cardinal basis; H = W log(2π e N).
- **Theorem 14**: linear filter Y(f) adds (1/W)∫_W log |Y(f)|² df to H′.
- **Theorem 15 (EPI)**: N̄1 + N̄2 ≤ N̄3 ≤ N1 + N2 for a sum of ensembles.

## Continuous channel
- **Rate (integral form)**: R = ∬ P(x,y) log [P(x,y)/(P(x)P(y))] dx dy. Preferred because H(x)−Hy(x) may be ∞−∞.
- **Additive noise (Theorem 16)**: y = x+n independent ⇒ R = H(y) − H(n), C = Max H(y) − H(n).
- **AWGN, average power P (Theorem 17)**: C = W log((P+N)/N).
- **Arbitrary noise (Theorem 18)**: W log((P+N1)/N1) ≤ C ≤ W log((P+N)/N1).
- **Peak power S (Theorem 20)**: C ≥ W log(2S/(π e N)); high-S/N upper bound W log[(2/πe)(S+N)/N (1+ε)]; C ∼ W log(1+S/N) as S/N→0.

## Fidelity and source rate
- **Fidelity functional**: v[P(x,y)]. Any reasonable ergodic evaluation is v = ∬ P(x,y) ρ(x,y) dx dy.
- **Distance ρ(x,y)**: “how undesirable it is to receive y when x is transmitted.” Not necessarily a metric.
- **Rate of a source relative to fidelity v1**: R1 = Min_{Px(y)} R subject to E[ρ]=v1.
- **Theorem 21**: R1 ≤ C ⇒ encode to fidelity arbitrarily near v1; R1 > C impossible.
- **White noise, RMS (Theorem 22)**: R = W1 log(Q/N), N = allowed mean-square error, Q = source power.
- **General RMS (Theorem 23)**: W1 log(Q1/N) ≤ R ≤ W1 log(Q/N).

## Other
- **Bandwidth W**: highest frequency (Hz) in a bandlimited ensemble; 2W degrees of freedom per second.
- **Dimension rate** (Appendix 7): λ = lim_{δ→0} lim_{ε→0} lim_{T→∞} log N(ε,δ,T) / (T log ε). Bandlimited: λ = 2W.
- **Data-processing** (Appendix 7): R(x;v) ≤ R(x;y) for any (even statistical) operation producing v from y.
