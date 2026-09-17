# Patterns — Probability and Random Processes (G&S 4th ed.)

Concrete techniques, algorithms, and stochastic patterns from G&S.

---

## Pattern: Stationary Distribution via Detailed Balance

**When to use**: Verifying a distribution π is stationary for a reversible Markov chain.

**How**:
1. Propose distribution π = (πi).
2. Check detailed balance: πi·pij = πj·pji for all i,j.
3. If it holds: π is stationary. Normalize if Σπi ≠ 1.

**Trade-offs**: Easier than solving πP=π directly. Only works for reversible chains.

**Example**: M/M/1 queue. State i = queue length. π_i = (1−ρ)ρ^i. Check: πi·λ = π_{i+1}·μ → (1−ρ)ρ^i·λ = (1−ρ)ρ^{i+1}·μ → λ/μ = ρ. ✓

---

## Pattern: Gambler's Ruin via Optional Stopping Theorem

**When to use**: Finding absorption probabilities for bounded random walk.

**How**:
1. Find a martingale (Y,F) adapted to the process.
2. Identify stopping time T = first exit from {0,...,N}.
3. Verify OST conditions: P(T<∞)=1, E|YT|<∞, E(Yn·I{T>n})→0.
4. Apply E(YT) = E(Y0); solve for desired probability.

**Example**: Asymmetric walk, p≠q. Martingale Yn = (q/p)^{Sn}. OST gives pk = (ρ^k − ρ^N)/(1−ρ^N) where ρ=q/p.

**Trade-offs**: Requires finding the right martingale. De Moivre's trick (exponential martingale) works broadly.

---

## Pattern: MCMC via Metropolis-Hastings

**When to use**: Sampling from a target distribution π when direct sampling is hard.

**How**:
1. At state x, propose y from proposal q(x,y).
2. Accept with probability α = min(1, π(y)q(y,x)/(π(x)q(x,y))).
3. Move to y if accepted; stay at x otherwise.
4. Resulting chain is reversible with stationary distribution π.

**Why it works**: Detailed balance: π(x)q(x,y)α(x→y) = π(y)q(y,x)α(y→x). ✓

**Trade-offs**: Mixing time depends on proposal; bad proposals → slow convergence.

---

## Pattern: Renewal-Reward Rate Computation

**When to use**: Long-run rate of reward/cost in a regenerative system.

**How**:
1. Identify renewal epochs (times at which the system regenerates).
2. Compute E[reward per cycle] = E(Rn).
3. Compute E[cycle length] = E(Xi) = μ.
4. Long-run rate = E(Rn)/μ (renewal-reward theorem).

**Example**: Cache hit rate. Renewal = each cache miss. Cycle = time between misses. Reward = number of hits per cycle. Long-run hit rate = E(hits per cycle)/E(cycle length).

**Trade-offs**: Requires i.i.d. cycles. For non-i.i.d. cycles, use ergodic theorem directly.

---

## Pattern: Martingale Construction for Markov Chains

**When to use**: Turning a Markov chain problem into a martingale problem.

**How**:
1. Find harmonic function ψ: state space → ℝ satisfying (Pψ)(i) = ψ(i), i.e., Σj pij ψ(j) = ψ(i).
2. Then Yn = ψ(Xn) is a martingale with respect to the natural filtration Fn = σ(X0,...,Xn).
3. Apply OST to extract hitting probabilities or expected times.

**Variants**:
- Right eigenvector Pψ = λψ → λ^{-n}ψ(Xn) is a martingale.
- For expected hitting times: use h(i) = E_i[T] and check (Ph)(i) = h(i) − 1.

---

## Pattern: CLT Confidence Interval

**When to use**: Estimating E(X) from n iid observations.

**How**:
1. Compute x̄ = (1/n)Σxi and s² = (1/(n−1))Σ(xi−x̄)².
2. 95% CI: x̄ ± 1.96·s/√n.
3. For non-normal populations: valid asymptotically by CLT when n≥30 (rule of thumb).

**When it fails**: Heavy-tailed distributions (Cauchy, Pareto α<2) — CLT doesn't apply. Use bootstrap or α-stable limits.

---

## Pattern: Characteristic Function to Identify Distributions

**When to use**: Proving two r.v.s have the same distribution.

**How**:
1. Compute characteristic functions φX(t) and φY(t).
2. If φX(t) = φY(t) for all t → X =^d Y (inversion theorem).

**Common CFs**:
- N(μ,σ²): φ(t) = exp(iμt − σ²t²/2)
- Poisson(λ): φ(t) = exp(λ(e^{it}−1))
- Exp(λ): φ(t) = λ/(λ−it)
- Cauchy(0,1): φ(t) = exp(−|t|)

**For sums of independent r.v.s**: φ_{X+Y}(t) = φX(t)·φY(t). Sum of n iid → CLT by showing φ → exp(−t²/2).

---

## Pattern: Doob's Maximal Inequality for Anomaly Detection

**When to use**: Bounding the probability of a process ever exceeding a threshold.

**How**:
1. Identify a martingale or submartingale (Y,F).
2. Apply: P(max_{0≤m≤n} Ym ≥ x) ≤ E(Yn⁺)/x.
3. For the running maximum over all time: use martingale convergence + UI.

**Why it works**: Stopping time argument; OST applied to T = first crossing of level x.

---

## Pattern: Excess Lifetime Distribution for Cache Scheduling

**When to use**: Computing time-to-next-event in a renewal process at stationarity.

**How**:
1. Let X₁,X₂,… be iid interarrival times with distribution F, mean μ, variance σ².
2. In steady state (t→∞): P(E(t) > x) = (1/μ)∫_x^∞ (1−F(y))dy.
3. Mean excess at stationarity = E(X₁²)/(2μ) = μ/2 + σ²/(2μ).

**Key insight**: If σ²=0 (deterministic renewals), mean excess = μ/2. If σ²>0, excess grows with variance — inspection paradox.

---

## Pattern: Optional Stopping for Expected Absorption Time

**When to use**: Computing E[T] for a stopping time T of a martingale.

**How**:
1. Find a second martingale related to T. Classic: if {Sn} is simple random walk, {Sn²−n} is a martingale.
2. Apply OST to this second martingale.
3. E(ST²−T) = E(S0²) → E(T) = E(ST²) − E(S0²).

**Example**: RW on {−a,...,b}, S0=0. T = first exit. E(ST²) = a²·(b/(a+b)) + b²·(a/(a+b)) = ab. So E(T) = ab.

---

## Pattern: Mixing Time via Spectral Gap

**When to use**: Bounding convergence rate of a Markov chain to stationarity.

**How**:
1. Find the second-largest eigenvalue λ₂ of transition matrix P.
2. Spectral gap = 1 − λ₂.
3. Mixing time τmix(ε) ≤ (1/(1−λ₂)) · log(1/(ε·π_min)).
4. For reversible chains: all eigenvalues real, spectral gap is well-defined.

**Trade-offs**: Spectral gap is tight for lazy chains. For non-reversible chains, use singular values.
