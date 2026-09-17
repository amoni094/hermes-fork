# Chapter 4: Entropy Rates of a Stochastic Process

## Core Idea
For a process, the right compression limit is the entropy rate H(X) = lim (1/n) H(X1,...,Xn), which for stationary processes also equals lim H(Xn | X^{n−1}). Markov structure makes this a one-step conditional entropy under the stationary distribution.

## Key Concepts
- **Stationary process**: joint laws invariant under time shift: P(X1^n = x1^n) = P(X_{1+k}^{n+k} = x1^n).
- **Markov chain**: P(X_{n+1}|X^n) = P(X_{n+1}|X_n). Time-invariant if P(X_{n+1}=b|X_n=a) is independent of n.
- **Entropy rate**: H(X) := lim_{n→∞} (1/n) H(X1,...,Xn) when the limit exists.
- **Conditional entropy rate**: H'(X) := lim H(Xn | X^{n−1}) when the limit exists.
- **Doubly stochastic**: P_{ij} has rows *and* columns summing to 1; uniform is stationary.
- **Hidden Markov / function of a Markov chain**: Y_i = φ(X_i); entropy rate exists but usually has no closed form.

## Frameworks and Methods
- **Two limits, one value**: prove H' exists by monotonicity (conditioning reduces entropy + stationarity), then Cesàro to get H = H'.
- **Markov computation**: H(X) = −∑_i μ_i ∑_j P_{ij} log P_{ij} = H(X2|X1) under stationary μ.
- **Second law via relative entropy**: D(μ_n || μ_{n+1}) and D(μ_n || μ) decrease; entropy of the state can increase toward the stationary entropy.
- **Sandwich for functions of Markov chains**: condition on the hidden state X1 to bound H(Y).

## Key Results and Theorems

**Theorem 4.2.2.** For a stationary process, H(Xn | X^{n−1}) is nonincreasing in n and converges to some H'(X).
Proof: H(X_{n+1}|X_1^n) ≤ H(X_{n+1}|X_2^n) = H(Xn | X^{n−1}) by stationarity.

**Theorem 4.2.3 (Cesàro mean).** If a_n → a then b_n = (1/n)∑_{i=1}^n a_i → a.

**Theorem 4.2.1.** For a stationary process both limits exist and
H(X) = H'(X).
Proof: chain rule + Cesàro on the monotone sequence H(Xn|X^{n−1}).

**Theorem 4.2.4.** Stationary Markov chain with stationary μ and transition P:
H(X) = −∑_{i,j} μ_i P_{ij} log P_{ij} = H(X2|X1).

**Second law (Section 4.4).** If μ_n is the distribution at time n:
- D(μ_n || μ'_n) is nonincreasing along any two trajectories of the same chain (data processing on the Markov kernel).
- D(μ_n || μ) ↓ to 0 if μ is stationary (and the chain mixes).
- If P is doubly stochastic, H(μ_n) is nondecreasing (uniform is stationary, entropy increases toward log|X|).

**Theorem 4.5.1 (functions of a Markov chain).** If {Xi} is stationary Markov and Y_i = φ(X_i), then
H(Yn | Y^{n−1}, X1) ≤ H(Y) ≤ H(Yn | Y^{n−1}),
and the gap H(Yn|Y^{n−1}) − H(Yn|Y^{n−1},X1) → 0, giving computable bounds that tighten with n.

**Hidden Markov entropy rate** generally has no closed form; the sandwich is the practical method.

## Key Equations
- H(X) = lim (1/n) H(X^n) = lim H(Xn | X^{n−1})  (stationary)
- Markov: H(X) = ∑_i μ_i H(row i of P)
- i.i.d. special case: H(X) = H(X1)
- Independent but not identical: (1/n)H(X^n) = (1/n)∑ H(X_i) may fail to have a limit

## Worked Example
Two-state Markov chain, P_{01}=P_{10}=α, P_{00}=P_{11}=1−α, stationary μ=(1/2,1/2). Then H(X) = H(α) (binary entropy of the flip probability). If α=1/2 the chain is i.i.d. fair bits, H=1. If α=0 it is stuck, H=0.

Random walk on a weighted graph: entropy rate = ∑_{edges} μ_i P_{ij} log(1/P_{ij}); Cover–Thomas compute it as a weighted average of local branching.

## Anti-patterns
- **Using H(X1) as the rate of a dependent process**: too large; dependence is free compression.
- **Assuming H(X) exists without stationarity**: a switching source can make (1/n)H(X^n) oscillate.
- **Confusing H(Xn) with H(Xn|X^{n−1})**: H(Xn) may stay large while the conditional rate is small (deterministic evolution of a random initial state).
- **Expecting a formula for HMM entropy rate**: use bounds or numerical state-conditioned entropy.

## Key Takeaways
1. Entropy rate, not single-letter entropy, is the compression limit for processes.
2. Stationarity ⇒ the two definitions coincide; Markov ⇒ one-step formula.
3. Relative entropy to the stationary law is a Lyapunov function (second law).
4. Functions of Markov chains need the sandwich; AEP for general stationary ergodic processes waits until Ch 16.

## Connects To
- **Ch 3**: AEP for i.i.d. is the special case H(X)=H(X1).
- **Ch 5**: L_n / n → H(X) for stationary ergodic sources (with universal methods in Ch 13).
- **Ch 6**: gambling on dependent horse races grows at log-odds minus entropy rate.
- **Ch 12**: Burg maxent process is Gauss–Markov; entropy rate via Toeplitz determinants.
- **Ch 16**: Shannon–McMillan–Breiman: −(1/n) log p(X^n) → H(X) a.s. for ergodic processes.
