# Chapter 11: Information Theory and Statistics

## Core Idea
The method of types turns large-deviation, universal coding, and hypothesis testing into finite-alphabet counting: a type class of empirical distribution P has size ≈ 2^{n H(P)} and probability ≈ 2^{−n D(P||Q)} under Q. Sanov, Chernoff–Stein, and Cramér–Rao are the statistical payoffs.

## Key Concepts
- **Type (empirical pmf)** of x^n: P_{x^n}(a) = N(a|x^n)/n. The type class T(P) = {x^n : P_{x^n}=P}.
- **Type class size**: |T(P)| ≐ 2^{n H(P)}; more precisely (n+1)^{−|X|} 2^{nH(P)} ≤ |T(P)| ≤ 2^{nH(P)}.
- **Probability of a type**: Q^n(T(P)) ≐ 2^{−n D(P||Q)}; exactly Q^n(x^n)=2^{−n(D(P||Q)+H(P))} for every x^n of type P.
- **Number of types**: polynomial, ≤ (n+1)^{|X|}.
- **Sanov’s theorem**: P(empirical type falls in a set of distributions E) ≐ 2^{−n inf_{P∈E} D(P||Q)}.
- **Conditional limit / Pythagorean theorem**: the I-projection of Q onto a convex set of distributions.
- **Hypothesis testing**: H1: Q=P1 vs H2: Q=P2; error exponents α_n, β_n.
- **Chernoff–Stein**: best exponent of β_n given α_n→ some ε∈(0,1/2) is D(P1||P2).
- **Chernoff information**: symmetric Bayesian error exponent min_{0≤λ≤1} log ∑ p1^λ p2^{1−λ}.
- **Fisher information**: J(θ) = E[(∂/∂θ log f(X;θ))^2] = −E[∂²/∂θ² log f].
- **Cramér–Rao**: var(T) ≥ 1/J(θ) for unbiased T.

## Frameworks and Methods
- **Replace typical sets by type classes**: every sequence in T(P) has identical probability; counting is multinomial.
- **Universal coding via types**: describe the type (O(|X| log n) bits) then the index in the type class (n H(P̂) bits) ⇒ total n H(P̂)+O(log n), which is optimal for the true p.
- **Sanov by union of types**: polynomially many types, exponentially different probabilities; the inf-D type dominates.
- **Neyman–Pearson as likelihood ratio**: log(P1/P2) = n(D(P̂||P2)−D(P̂||P1)); Stein uses relative-entropy typical sets.
- **Local KL is Fisher**: D(f_θ || f_{θ+Δ}) ≈ (Δ²/2) J(θ).

## Key Results and Theorems

**Method of types (size and probability).**
|T(P)| ≤ 2^{n H(P)},  Q^n(x^n) = 2^{−n(D(P||Q)+H(P))} for x^n∈T(P),
hence Q^n(T(P)) ≤ 2^{−n D(P||Q)}. Matching lower bounds up to poly(n).

**Universal source coding (Section 11.3).** There exist codes with
(1/n) L(x^n) ≤ H(P_{x^n}) + |X| (log(n+1))/n,
hence expected length ≤ H(Q) + O((log n)/n) simultaneously for every i.i.d. Q on a finite alphabet.

**Sanov’s theorem.** For i.i.d. ~ Q and a set E of pmfs,
Q^n(P̂_n ∈ E) ≐ 2^{−n D(P^*||Q)},  P^* = argmin_{P∈E} D(P||Q)
(with closure/interior technicalities).

**Conditional limit theorem.** Given P̂_n ∈ E (convex, closed), the conditional law of X1 given the constraint converges to the I-projection P^* = argmin_{P∈E} D(P||Q). (Pythagorean: D(P||Q) ≥ D(P||P^*)+D(P^*||Q) for P∈E.)

**Chernoff–Stein lemma (Thm 11.8.3).** In testing P1 vs P2, D(P1||P2)<∞,
lim_{n→∞} (1/n) log β_n^ε = −D(P1||P2)
where β_n^ε is the best type-II error given type-I error α_n < ε ∈ (0,1/2).

**Chernoff information.** For equal Bayesian priors/costs, the best error exponent is
C(P1,P2) = max_{0≤λ≤1} −log ∑_x P1(x)^λ P2(x)^{1−λ} = D(P_λ || P1) = D(P_λ||P2)
at the optimizing tilted P_λ.

**Cramér–Rao (Thm 11.10.1 / 17.7.1).** For unbiased T(X) of θ,
var_θ(T) ≥ 1 / J(θ).
n i.i.d. samples: J_n = n J_1, so var ≥ 1/(nJ).

## Key Equations
- |T(P)| ≐ 2^{nH(P)}
- Q^n(T(P)) ≐ 2^{−n D(P||Q)}
- Sanov: P(E) ≐ 2^{−n inf_{P∈E} D(P||Q)}
- Stein: (1/n) log β^* → −D(P1||P2)
- J(θ) = E[(∂_θ log f)^2]
- var(T) ≥ 1/J(θ)
- D(f_θ||f_{θ+Δ}) = (Δ²/2) J(θ) + o(Δ²)

## Worked Example
Fair die Q=uniform on {1..6}, E = {P : E_P[X] ≥ 4}. Sanov rate is D(P^*||U) where P^* is maxent on {1..6} with mean 4, i.e. P^*(k) ∝ e^{λk} (Ch 12). The event “average ≥ 4” is exponentially unlikely at that D.

Testing Bern(0.5) vs Bern(0.6): D(0.5||0.6) ≈ 0.029 bits. With α_n bounded, type-II error decays as 2^{−0.029 n} — slow; you need n~1000 for a factor 10^9.

## Anti-patterns
- **Ignoring the polynomial number of types**: they never beat an exponential gap in D.
- **Using D(P2||P1) in Stein when you needed D(P1||P2)**: the exponent is KL from the *true-under-H1* distribution to H2.
- **Claiming Cramér–Rao for biased estimators without the correction**: biased form is (1+b'(θ))^2 / J(θ).
- **Universal coding without finite alphabet**: types need |X| finite or a sieve; else go to LZ (Ch 13).
- **Treating Fisher as a global distance**: it is the Hessian of D at 0; large deviations need full D.

## Key Takeaways
1. Type class volume 2^{nH} and probability 2^{−nD} are the finite-n AEP.
2. Sanov is the large-deviation principle with rate D(·||Q).
3. Optimal hypothesis-testing exponents are KL / Chernoff information.
4. Universal coding costs only O(|X| log n) extra bits.
5. Fisher/Cramér–Rao is local information theory.

## Connects To
- **Ch 2**: D ≥ 0, chain rules.
- **Ch 3**: AEP is Sanov on a KL ball around p.
- **Ch 12**: the I-projection *is* the maximum-entropy distribution.
- **Ch 13**: minimax redundancy equals a channel capacity (types channel).
- **Ch 17**: Pinsker, Sanov refinements, entropy–Fisher identities.
