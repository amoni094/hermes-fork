# Theorems — A Mathematical Theory of Communication (Shannon, 1948)

Numbering follows Shannon. Proofs are sketches of *his* arguments. He does not name “source coding theorem,” “noisy channel coding theorem,” or “rate-distortion”; those names are supplied in brackets.

---

## Theorem 1 — Discrete noiseless capacity
**Statement.** For a discrete channel with (possibly state-constrained) allowed sequences, C = lim_{T→∞} (log N(T))/T exists and equals log W, W the largest real root of |∑_s W^{−b_{ij}^{(s)}} − δ_{ij}| = 0 (or ∑_i W^{−t_i} = 1 with no states).

**Guarantees.** The exponential growth rate of the number of distinguishable noiseless signals is a well-defined bits/s.

**Proof sketch.** N(t) obeys a linear delay equation; the dominant exponential is the largest characteristic root (Appendix 1).

**Significance.** Capacity is defined *before* entropy, as a combinatorial growth rate. Telegraph (Morse) is the worked example.

---

## Theorem 2 — Uniqueness of entropy
**Statement.** The only H(p1,…,pn) continuous in the pi, increasing in n when pi=1/n, and additive under decomposition of choices, is H = −K ∑ pi log pi, K>0.

**Guarantees.** Axiomatic pedigree only. Shannon: “in no way necessary for the present theory… The real justification of these definitions… will reside in their implications.”

**Proof sketch.** Appendix 2: A(n)=K log n from A(s^m)=m A(s); rationals by grouping; all pi by continuity.

**Significance.** Names the Boltzmann form; coding theorems, not axioms, are the foundation.

---

## Theorems 3–6 — AEP and block/conditional entropy
**Theorem 3.** For any ε,δ>0 and N large, N-sequences split into a set of probability <ε and a remainder with |(log p^{−1})/N − H| < δ.

**Theorem 4.** n(q) = number of most probable N-sequences accumulating probability q. lim (log n(q))/N = H for q≠0,1. “Treat the long sequences as though there were just 2^{HN} of them, each with probability 2^{−HN}.”

**Theorems 5–6.** GN ↓ H; FN ↓ H; FN = N GN − (N−1)G_{N−1}; GN = (1/N)∑ Fn; FN ≤ GN.

**Guarantees.** Entropy is both an internal-state average and the observable bit-rate of typical sequences.

**Proof sketch.** Ergodicity ⇒ empirical transition frequencies → Pi, pi(j); then (1/N) log p^{−1} → H (Appendix 3).

**Significance.** The discrete typical-set geometry of Theorems 9 and 11.

---

## Theorem 8 — Transducers do not increase entropy
**Statement.** A finite-state transducer cannot increase the entropy per symbol (or per second) of an input ergodic source. If the map is invertible (non-singular), entropy is preserved.

**Guarantees.** Encoding cannot create information; the converse of Theorem 9 uses this.

**Significance.** Discrete data-processing for entropy.

---

## Theorem 9 — [Source coding / noiseless coding theorem]
**Statement.** Source entropy H bits/symbol, channel capacity C bits/s: one can encode so as to transmit at average rate (C/H − ε) source symbols/s, ε arbitrarily small. It is not possible to transmit at an average rate greater than C/H.

**Guarantees.** Entropy is operationally the number of channel bits needed per source symbol. Reliable (zero-error, noiseless channel) communication iff source rate ≤ C.

**Proof sketch.**
- *Converse.* Transmitter non-singular ⇒ input entropy/s = H′ ≤ C ⇒ symbols/s ≤ C/H.
- *Direct, typical sets.* Encode ≲ 2^{(H+η)N} typical N-blocks 1-1 into channel sequences of duration T=(H/C+δ)N; atypical blocks get a longer framed code of vanishing probability.
- *Direct, Shannon–Fano.* Order N-blocks by decreasing p_s; encode by the binary expansion of P_s=∑_{i<s} p_i to m_s bits, log2(1/p_s) ≤ m_s < 1+log2(1/p_s). Prefix-free; average length → H. Fano’s split-by-halves is “apart from minor differences… the same thing.”

**Significance.** The noiseless source coding theorem. Shannon–Fano coding; Huffman (1952) later optimizes finite-N.

---

## Theorem 10 — Equivocation as correction-channel capacity
**Statement.** If a correction channel has capacity Hy(x), one can encode correction data to fix all but an arbitrarily small fraction of errors. Impossible if capacity < Hy(x).

**Guarantees.** Equivocation is the extra bits/s that must be supplied at the receiver to make the message certain.

**Proof sketch.** ~2^{T Hy(x)} plausible causes for a received block; identifying which takes T Hy(x) bits. Converse: Hy(x,z) ≥ Hy(x), so if H(z)<Hy(x) residual uncertainty remains.

---

## Theorem 11 — [Noisy channel coding theorem]
**Statement.** Discrete channel capacity C, source entropy per second H.
- If H ≤ C there exists a coding system such that the source output can be transmitted with an arbitrarily small frequency of errors (or an arbitrarily small equivocation).
- If H > C it is possible to encode so that the equivocation is less than H − C + ε.
- There is no method of encoding which gives an equivocation less than H − C.

**Guarantees.** A noisy channel has a single number C: below C, error → 0 with blocklength; above C, equivocation is at least the excess. Redundancy need not → ∞ as error → 0.

**Proof sketch.** Random coding. Capacity-achieving input S0. For duration T: ~2^{T H(x)} typical inputs, ~2^{T H(y)} typical outputs, each output fan has ~2^{T Hy(x)} causes. Assign 2^{TR} source messages at random to S0 inputs. Collision probability in a fan → 0 if R < H(x)−Hy(x) ≤ C. Converse: H(x)−Hy(x) ≤ C by definition of C. If H=C+a, send C bits and discard a: equivocation a.

**Significance.** The central theorem of the paper. Non-constructive (“almost all codes are good”). Founds error-correcting codes. Sec 14: explicit constructions generally impractical, “related to the difficulty of giving an explicit construction for a good approximation to a random sequence.”

---

## Theorem 12 — Operational capacity as packing rate
**Statement.** N(T,q) = max number of duration-T signals, used equally often, decoded as most probable cause in the subset, with P(error)≤q. Then lim (log N(T,q))/T = C for q ≠ 0 or 1.

**Guarantees.** Same C as Max[H(x)−Hy(x)], matching the noiseless definition of Theorem 1 with a reliability constraint.

---

## Theorem 13 — [Sampling theorem]
**Statement.** If f(t) contains no frequencies over W, then
f(t) = ∑_{n=−∞}^{∞} Xn [sin π(2Wt−n)]/[π(2Wt−n)],  Xn = f(n/(2W)).

**Guarantees.** Band W, time T ⇒ 2TW degrees of freedom. Continuous problems become finite-dimensional geometry.

**Proof sketch.** Deferred to “Communication in the Presence of Noise,” Proc. IRE 37(1), 1949.

**Significance.** Nyquist–Shannon sampling; PCM, digital audio, sphere-packing proofs of capacity.

---

## Theorem 14 — Entropy loss in linear filters
**Statement.** Ensemble entropy H1 per degree of freedom in band W, filter Y(f):
H2 = H1 + (1/W) ∫_W log |Y(f)|² df.

**Proof sketch.** Sine/cosine coordinates; Jacobian ∏ |Y(fi)|²; Sec 20 coordinate-change formula.

---

## Theorem 15 — [Entropy-power inequality]
**Statement.** Powers N1,N2, entropy powers N̄1,N̄2, sum entropy power N̄3:
N̄1 + N̄2 ≤ N̄3 ≤ N1 + N2.

**Guarantees.** White noise maximizes entropy for given power; proportional Gaussians minimize entropy of a sum given the summands’ entropies.

**Proof sketch.** Appendix 6. Upper: maxent is white of power N1+N2. Lower: variational; Gaussians with aij = K bij.

**Significance.** Engine of Theorems 18–19, 23 and small-signal absorption.

---

## Theorem 16 — Additive continuous channel
**Statement.** If received = independent signal + noise, Px(y)=Q(y−x), then R = H(y)−H(n) and C = Max H(y) − H(n).

**Proof sketch.** H(x,y)=H(x,n)=H(x)+H(n); also H(x,y)=H(y)+Hy(x); rearrange.

---

## Theorem 17 — [Shannon–Hartley / AWGN capacity]
**Statement.** Band W, white thermal noise power N, average transmitter power ≤ P:
C = W log((P+N)/N).

“By sufficiently involved encoding systems we can transmit binary digits at the rate W log2((P+N)/N) bits per second, with arbitrarily small frequency of errors. It is not possible to transmit at a higher rate by any encoding system without a definite positive frequency of errors.”

**Proof sketch.** Max H(y) when received is white of power P+N, achieved by sending white of power P. H(y)=W log(2πe(P+N)), H(n)=W log(2πe N). Random white-noise codebook of M=2^{s} samples, duration T; decode least RMS discrepancy; almost all selections achieve the limit.

**Significance.** SNR–bandwidth tradeoff. Independent similar formulas: Wiener, Tuller, Sullivan (Shannon notes different interpretations). Geometric packing in the 1949 IRE paper.

---

## Theorems 18–19 — Arbitrary perturbing noise
**Theorem 18.** W log((P+N1)/N1) ≤ C ≤ W log((P+N)/N1), N1 = noise entropy power.

**Theorem 19.** Write C = W log((P+N−η)/N1). Then η ↓ in P and η→0 as P→∞.

**Proof sketch.** Upper: H(y)≤W log(2πe(P+N)). Lower: send white P; EPI ⇒ entropy power of sum ≥ P+N1. Large P makes received nearly white.

---

## Theorem 20 — Peak power limitation
**Statement.** White noise N, peak transmitter power S, band W:
C ≥ W log(2S/(π e N));
for large S/N, C ≤ W log[(2/πe)((S+N)/N)(1+ε)];
as S/N→0 (band from 0), C / [W log(1+S/N)] → 1.

**Proof sketch.** Upper: relax to sample peaks; uniform [−√S,√S] samples, entropy W log 4S. Lower: triangular filter, factor e^{−2}, peak preserved. Small SNR: block ±√S, absorption (Theorem 15).

---

## Theorem 21 — [Rate-distortion / source coding with a fidelity criterion]
**Statement.** If a source has rate R1 for valuation v1, one can encode and transmit over a channel of capacity C with fidelity as near v1 as desired provided R1 ≤ C. Impossible if R1 > C.

R1 = Min_{Px(y)} ∬ P(x,y) log[P(x,y)/(P(x)P(y))] dx dy  s.t.  ∬ ρ P = v1.

**Guarantees.** Necessary and sufficient bits/s to meet a fidelity. Distortion can be chosen at the transmitter (“general quantizing… analogous to the quantizing noise in PCM”).

**Proof sketch.** Discretize (x,y); random covering of typical x by 2^{(R1+ε)T} typical y’s (Fig. 10 fans); send the y-index over the channel.

**Significance.** 1948 form of the rate-distortion theorem; 1959 paper develops it.

---

## Theorems 22–23 — Rates for RMS fidelity
**Theorem 22.** White noise source, power Q, band W1, allowed MSE N:
R = W1 log(Q/N).

**Theorem 23.** Any source of band W1, power Q, entropy power Q1:
W1 log(Q1/N) ≤ R ≤ W1 log(Q/N).

**Proof sketch.** 22: Max Hy(x) when error is white of power N. 23: lower by maxent of the error; upper by random packing in a sphere of radius √(Q−N).

---

## Unnumbered results often cited as theorems
- **Capacity formula (definition):** C = Max [H(x)−Hy(x)] (Sec 12); continuous integral form (Sec 24, Appendix 7).
- **Symmetric discrete channel:** C = log m + ∑ pi log pi (Sec 16).
- **Isolated groups:** C = log ∑ 2^{C_n} (Sec 16).
- **Hamming (7,4):** C = 4/7 on the 7-bit single-error block channel; the code meets C (Sec 17).
- **Data-processing (Appendix 7):** R(x;v) ≤ R(x;y).
