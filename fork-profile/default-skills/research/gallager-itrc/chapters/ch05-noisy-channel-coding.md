# Chapter 5: The Noisy-Channel Coding Theorem

## Core Idea
For any DMC, randomly chosen block codes of length N and rate R < C have ensemble error probability P_e ≤ exp(−N E_r(R)) with E_r(R) > 0. Expurgation improves the exponent at low rates. The hard engineering problem is decoding, not finding codes.

## Key Concepts
- (N, R) block code: M = ⌈e^{NR}⌉ words of length N (R in nats).
- Maximum-likelihood decoding: choose m maximizing P_N(y | x_m) (ties may be errors).
- Ensemble average: each word drawn independently with Q_N(x), typically i.i.d. letters ~ Q.
- Gallager function: E_0(ρ, Q) = −ln ∑_j [∑_k Q(k) P(j|k)^{1/(1+ρ)}]^{1+ρ}, for ρ ≥ 0.
- Random-coding exponent: E_r(R) = max_{0≤ρ≤1} max_Q [E_0(ρ, Q) − ρ R].
- Critical rate R_cr: rate where the optimizing ρ hits 1; for R ≤ R_cr the bound is linear, E_r(R) = max_Q E_0(1,Q) − R.
- Cutoff rate R_0: R_0 = max_Q E_0(1, Q). Sequential decoding (Ch 6.9) works reliably for R < R_0; R_0 is the zero-rate intercept of the ρ = 1 tangent.
- Expurgated exponent E_ex(R) (Gallager’s E_x): at low rates, delete bad words; E_ex(R') = sup_{ρ≥1} max_Q [E_x(ρ, Q) − ρ R'] with E_x(1,Q) = E_0(1,Q).
- Chernoff / Gallager lemma: a ρ-softened union bound, P(∪ A_m) ≤ (∑ P(A_m))^ρ for 0 ≤ ρ ≤ 1, interpolates union bound and the trivial bound 1.

## Frameworks and Methods
- Two-word analysis first (§5.3): pairwise error is a Chernoff bound on likelihood ratios. Many-word bound is that pairwise bound plus the ρ-union lemma (Theorem 5.6.1).
- Random coding: average P_e over the ensemble; at least one code is as good as the average. Chebyshev: most codes are not much worse.
- Uniform error: start with 2M words, expurgate the M worst so every remaining word has P_{e,m} ≤ 4 exp(−N E_r(R)) (Corollary 2).
- Parametric geometry: E_r(R, Q) is the upper envelope of lines E_0(ρ,Q) − ρ R, slope −ρ. ρ is |dE_r/dR|.
- Optimization order: maximize E_0(ρ,Q) over Q first (convex in the F = e^{−E_0} sense), then over ρ.

## Key Results and Theorems
- Theorem 5.6.1 (general discrete channel): for any 0 ≤ ρ ≤ 1,
  P̄_{e,m} ≤ (M−1)^ρ ∑_y [∑_x Q(x) P(y|x)^{1/(1+ρ)}]^{1+ρ}.
- Theorem 5.6.2 (DMC, i.i.d. ensemble): P̄_{e,m} ≤ exp{−N [E_0(ρ,Q) − ρ R]}.
- Corollary: P_e ≤ exp(−N E_r(R)). Hence some code achieves this.
- Theorem 5.6.3: E_0(0,Q) = 0, ∂E_0/∂ρ|_{ρ=0} = I(Q;P) > 0, ∂²E_0/∂ρ² ≤ 0. So E_r(R) > 0 for R < I(Q;P), hence for R < C.
- Theorem 5.6.4 (noisy-channel coding theorem): E_r(R) is convex ∪, decreasing, and positive on 0 ≤ R < C. Thus P_e → 0 exponentially for all R < C.
- Theorem 5.6.5: F(ρ,Q) = exp(−E_0(ρ,Q)) is convex in Q; KT conditions for the maximizing Q analogous to capacity.
- BSC: Q = (1/2,1/2) maximizes E_0; E_0(ρ,Q) = ρ ln 2 − (1+ρ) ln[ε^{1/(1+ρ)} + (1−ε)^{1/(1+ρ)}].
- Theorem 5.7.1 (expurgated): there exist codes with P_{e,m} ≤ exp(−N E_ex(R + (ln 4)/N)) for all m. E_ex(R) ≥ E_r(R), strictly better at low R (except very noisy channels).
- Lower bounds (§5.8): sphere-packing / sphere-packing-like exponents show E_r is tight above R_cr; at low rates expurgation is the right upper bound on the true exponent.
- Finite-state channels (§5.9): the same random-coding method extends when state is suitably mixing or known at the receiver.

## Algorithms and Techniques
Random-coding bound for a DMC:
1. Fix rate R < C and block length N.
2. For ρ ∈ [0,1], maximize E_0(ρ,Q) over Q (uniform if symmetric).
3. Compute E_r(R) = max_ρ [E_0(ρ,Q*) − ρ R].
4. Conclude existence of a code with P_e ≤ e^{−N E_r(R)}.

Expurgation (low rate):
1. Draw 2M − 1 random words.
2. Bound P_{e,m}^s via pairwise Bhattacharyya-type sums (s ∈ (0,1], ρ = 1/s ≥ 1).
3. Keep M words with typical (not catastrophic) P_{e,m}.

ML decoding (conceptual):
1. For received y, compute P(y | x_m) for each m (or additive metric ∑ ln P(y_n|x_{m,n})).
2. Pick the maximizer. Complexity is exponential in N unless the code has structure (Ch 6).

## Anti-patterns
- Using only the union bound (ρ = 1) near capacity: it is loose; optimize ρ down toward 0 as R → C.
- Quoting C without E_r(R): finite-N reliability is the exponent.
- Searching for a “best” long unstructured code. Gallager: a random code is fine; instrument the decoder.
- Applying E_r with a poor Q. Always maximize over Q, or at least use the capacity-achieving Q (not always optimal for E_0 at ρ > 0, but often close).
- Expecting E_r to be tight at low R. Expurgate; the two-word atypical codes dominate the ensemble average.
- Confusing E_ex’s ρ ≥ 1 with E_r’s ρ ≤ 1. Same E_0-like algebra, different range and pairwise vs union origin.

## Key Takeaways
1. Random coding plus a ρ-union bound is the entire existence theory for reliable communication on a DMC.
2. E_r(R) > 0 iff R < C; the slope −ρ interpolates cutoff-rate behavior (ρ = 1) and capacity (ρ → 0).
3. Expurgation is how one removes a vanishing fraction of terrible words that spoil the low-rate average.
4. Existence is easy; Ch 6 is about codes whose encoding/decoding grow polynomially, not exponentially.

## Connects To
- Ch 4: C is the R-axis intercept of E_r; converse matches the theorem.
- Ch 6.2: random parity-check / coset ensembles achieve the same E_r on the BSC (pairwise independence suffices).
- Ch 6.9: sequential decoding computation blows up for R > R_0 = max E_0(1,Q).
- Ch 7: Theorem 5.6.1 extends to nondiscrete channels with integrals replacing sums.
- Ch 8: orthogonal signals and AWGN error exponents are the continuous analog of two-word Chernoff.
