# Glossary — Probability and Random Processes (G&S 4th ed.)

**Adapted process** — sequence {Yn} is adapted to filtration F if Yn is Fn-measurable for all n (Ch12)

**Aperiodic state** — gcd of return times = 1; required for limit theorem pij(n) → πj (Ch06)

**Autocovariance function c(t)** — cov(X(s+t), X(s)) for a stationary process; non-negative definite (Ch09)

**Backward equation** (Kolmogorov) — ∂u/∂t = Lᵀu, where L is the generator; used for hitting probabilities (Ch13)

**Bernoulli(p)** — P(X=1)=p, P(X=0)=1−p; building block of binomial (Ch03)

**Binomial(n,p)** — sum of n iid Bernoulli(p); E=np, var=np(1−p) (Ch03)

**Bochner's theorem** — φ is a characteristic function iff positive-definite, uniformly continuous, φ(0)=1 (Ch05)

**Borel σ-field** — smallest σ-field containing all open intervals on ℝ; standard event space for ℝ (Ch01)

**Brownian motion** — physical phenomenon modeled by Wiener process (Ch13)

**Chapman-Kolmogorov equations** — P^{m+n} = P^m · P^n; n-step transitions = matrix power (Ch06)

**Characteristic function φ(t) = E(e^{itX})** — always exists; uniquely determines distribution (Ch05)

**CLT (Central Limit Theorem)** — (Sn−nμ)/(σ√n) →D N(0,1) for iid Xi with E(Xi²)<∞ (Ch05)

**Conditional expectation E(X|G)** — G-measurable r.v. satisfying E[(X−E(X|G))·IG]=0 for all G∈G (Ch07)

**Coupling** — joint distribution of (X,Y) on same probability space; ||μ−ν||_TV ≤ P(X≠Y) (Ch04, Ch06)

**Cumulant κn** — n-th derivative of log φ at 0; κ₁=mean, κ₂=variance, κ₃=skewness (Ch05)

**Detailed balance** — πi·pij = πj·pji; sufficient for π to be stationary; implies reversibility (Ch06)

**Diffusion process** — continuous-path Markov process with drift μ(x,t) and diffusion σ²(x,t) (Ch13)

**Distribution function (CDF)** — F(x) = P(X≤x); right-continuous, non-decreasing (Ch02)

**Doob's martingale convergence theorem** — sup_n E(Yn⁺) < ∞ ⟹ Yn → Y∞ a.s. (Ch07)

**Doob's upcrossing inequality** — (b−a)E[Un(a,b)] ≤ E[(Yn−a)⁺]; implies a.s. convergence (Ch07, Ch12)

**Ergodic theorem** — time average → ensemble average for ergodic stationary processes (Ch09)

**Excess lifetime E(t)** — time from t to next renewal; limiting distribution has density (1−F(x))/μ (Ch10)

**Exponential(λ)** — memoryless continuous distribution; inter-arrival times of Poisson process (Ch04)

**Field** — collection of subsets closed under finite unions and complements (Ch01)

**Filtration F = {F0, F1, …}** — increasing sequence of σ-fields; encodes information flow (Ch12)

**First passage time T_B** — min{n: Xn ∈ B}; a stopping time for any closed B (Ch12)

**Forward equation** (Kolmogorov/Fokker-Planck) — ∂p/∂t = L*p; describes density evolution (Ch13)

**Gambler's ruin** — absorption probability for random walk on {0,...,N}; solved by OST (Ch03, Ch12)

**Gaussian process** — all finite-dimensional distributions are multivariate normal (Ch09)

**Generating function** — GX(s) = E(sX) for integer r.v. X; PGF (Ch05)

**Generator L** — lim_{t→0}(E[f(X(t))|X(0)=x] − f(x))/t; characterizes diffusion (Ch13)

**Geometric(p)** — P(X=k) = p(1−p)^{k-1}; memoryless discrete distribution (Ch03)

**Harmonic function ψ** — satisfies Pψ = ψ; yields martingale ψ(Xn) for Markov chain X (Ch12)

**Inspection paradox** — interval containing a fixed time is longer than typical; mean = E(X²)/E(X) (Ch10)

**Irreducible chain** — every state reachable from every state (Ch06)

**Itô's formula** — df(X) = f'(X)dX + ½f''(X)(dX)²; with (dW)²=dt (Ch13)

**Itô integral ∫f(s)dW(s)** — L² limit of adapted integrands; is a martingale (Ch13)

**Key renewal theorem** — ∫h(t−x)dm(x) → (1/μ)∫h(x)dx as t→∞ for non-arithmetic F (Ch10)

**Kolmogorov existence theorem** — consistent family of fdds ⟹ process exists (Ch08)

**Large deviations** — P(Sn/n ≥ a) ≈ exp(−nI(a)); I(a) = sup_t{ta − log M(t)} (Ch05)

**Law of total probability** — P(A) = Σ P(A|Bi)P(Bi) for partition {Bi} (Ch01)

**Lévy continuity theorem** — φXn → φX pointwise + φX continuous at 0 ⟺ Xn →D X (Ch05)

**Lévy process** — stationary independent increments, continuous in probability (Ch08)

**Markov chain** — P(Xn=s|X0,...,Xn-1) = P(Xn=s|Xn-1); "only the present matters" (Ch06)

**Markov property** — future ⊥ past | present (Ch06)

**Martingale (Y,F)** — adapted, E|Yn|<∞, E(Yn+1|Fn)=Yn; zero conditional drift (Ch07, Ch12)

**MCMC** — Markov Chain Monte Carlo; constructs chain with target stationary distribution (Ch06)

**Mean return time μi** — E[first return to state i | start at i]; πi = 1/μi (Ch06)

**Mixing time τmix(ε)** — min n: max_i ||Pⁿ(i,·)−π||_TV ≤ ε (Ch06)

**Moment generating function M(t) = E(e^{tX})** — exists on open interval; M^(k)(0)=E(Xk) (Ch05)

**Non-negative definite** — Σ φ(tj−tk)zjzk ≥ 0; required for valid autocovariances and CFs (Ch05, Ch09)

**Null recurrent state** — certain return but E[return time] = ∞; stationary distribution doesn't exist (Ch06)

**Optional stopping theorem (OST)** — E(YT) = E(Y0) under regularity; T a stopping time (Ch12)

**Ornstein-Uhlenbeck process** — stationary Gaussian Markov process; c(t)=σ²e^{-α|t|} (Ch09, Ch13)

**Poisson process** — Poisson(λ) arrivals in [0,t]; inter-arrivals are Exp(λ); only renewal+Markov (Ch06)

**Positive recurrent state** — certain return and E[return time] < ∞ (Ch06)

**Probability measure P** — σ-additive, P(∅)=0, P(Ω)=1 (Ch01)

**Probability space (Ω, F, P)** — the three-component foundation of probability (Ch01)

**Quadratic variation [W,W]_t = t** — for standard BM; source of Itô correction term (Ch13)

**Rate function I(a)** — I(a) = sup_t{ta−logM(t)}; governs large deviation probabilities (Ch05)

**Recurrent state** — P(return) = 1 (Ch06)

**Renewal equation** — m(t) = F(t) + ∫₀ᵗ m(t−x)dF(x) (Ch10)

**Renewal function m(t) = E[N(t)]** — expected number of renewals by time t (Ch10)

**Renewal process** — point process with iid interarrival times X₁,X₂,… (Ch10)

**Reversible chain** — satisfies detailed balance πi·pij = πj·pji (Ch06)

**σ-field (σ-algebra)** — closed under countable unions and complements; contains ∅ (Ch01)

**Spectral density f(λ)** — Fourier transform of autocovariance; f(λ)≥0 (Ch09)

**Stationary distribution π** — πP=π, Σπi=1; unique for irreducible positive recurrent chains (Ch06)

**Stochastic matrix** — non-negative entries, rows sum to 1; transition matrix of a Markov chain (Ch06)

**Stopping time T** — {T=n}∈Fn for all n; "decide to stop using only current and past information" (Ch12)

**Submartingale** — E(Yn+1|Fn) ≥ Yn; "non-negative drift" (Ch12)

**Supermartingale** — E(Yn+1|Fn) ≤ Yn; "non-positive drift" (Ch12)

**Tower property** — E[E(X|Y₁,Y₂)|Y₁] = E[X|Y₁]; iterated conditioning (Ch07)

**Transient state** — P(return) < 1; pii(n) → 0 (Ch06)

**Uniform integrability (UI)** — sup_i E(|Xi|·I{|Xi|>c}) → 0 as c→∞; needed for L¹ convergence (Ch07)

**Wald's equation** — E(ST) = μ·E(T) for iid Xi with mean μ and stopping time T with E(T)<∞ (Ch12)

**Wald's identity** — E[e^{tST}/M(t)^T] = 1 for appropriate t and stopping T (Ch12)

**Wiener process W** — Gaussian, W(0)=0, independent increments, W(t+s)−W(s)~N(0,σ²t), continuous paths (Ch08, Ch13)

**Wright-Fisher model** — Markov chain model for gene frequency evolution in finite population (Ch06)
