# Bandit Algorithms Glossary (Lattimore & Szepesvári)

## Core Terms

**Arm / Action**: A choice available to the learner each round. In Hermes: a memory source (hindsight, graphiti, l1).

**Bandit feedback**: Learner observes reward ONLY for the chosen arm (not all arms). Contrast: full-information (see all rewards).

**Bernoulli bandit**: Each arm has reward X_{t,i} ~ Bernoulli(μ_i). Simplest case; useful for binary signals.

**Context**: Side information x_t available before choosing arm each round. Enables generalisation across arms.

**Exploration**: Pulling arms to gather information about their true mean. Necessary but costly.

**Exploitation**: Pulling the arm believed to be best based on current information.

**Exploration-exploitation trade-off**: The central tension in bandits. Explore too much → waste reward. Exploit too early → miss better arms.

**Gap (Δ_i)**: μ* - μ_i. The suboptimality of arm i. Larger gap → arm easier to eliminate. Δ* = 0 for the optimal arm.

**Horizon (T or n)**: Total number of rounds. UCB1 is anytime (no T needed); EXP3 requires T for γ.

**Instance-dependent bound**: Regret bound in terms of gaps Δ_i (tight, problem-specific). E.g. O(Σ ln n / Δ_i).

**Minimax bound**: Worst-case regret bound over all problem instances. E.g. O(sqrt(KT ln T)).

**Pseudo-regret**: E[R_n] = n·μ* - Σ_t E[μ_{A_t}]. Most theoretical bounds are on pseudo-regret (easier to analyse than regret itself).

**Regret (R_n)**: n·μ* - Σ_t X_{A_t}. Difference between always-optimal reward and achieved reward.

## Algorithm Terms

**Cold start**: State when n_i = 0 (arm never pulled). UCB1 bonus = ∞; use large finite explore bonus (1.5) in practice.

**Confidence interval / UCB index**: Upper bound on μ_i, valid with high probability. UCB1 uses μ̂_i + sqrt(2 ln t / n_i).

**Empirical mean (μ̂_i)**: Σ_{rounds t: A_t=i} X_t / n_i.

**EXP3**: Exponential weights for Exploration and Exploitation (+ Experts). Adversarial algorithm.

**Importance weighting**: EXP3 trick. Estimate x̃_{t,i} = r_t/p_{t,i} if A_t=i else 0. Unbiased: E[x̃]=r.

**LinUCB**: UCB extended to linear function approximation. Uncertainty = x^T A^{-1} x (elliptical confidence set).

**OLS (Ordinary Least Squares)**: θ̂ = A^{-1} b where A = Σ x_t x_t^T, b = Σ r_t x_t. Core estimator for LinUCB.

**Optimism under uncertainty**: Core principle of UCB algorithms. Act as if each arm is as good as its confidence interval allows.

**Thompson Sampling**: Bayesian bandit algorithm. Sample θ_i from posterior, pull arm with highest sample.

**UCB1**: Upper Confidence Bound 1. Index = μ̂_i + sqrt(2 ln t / n_i). Achieves instance-optimal regret.

## Probability / Concentration Terms

**Hoeffding's inequality**: P(μ̂ - μ > ε) ≤ exp(-2nε²) for bounded random variables in [a,b]. Basis of UCB1 bound.

**KL divergence / Pinsker's inequality**: KL(p||q) ≥ 2(p-q)². Used in lower bound proofs.

**Sub-Gaussian**: Random variable X is σ-sub-Gaussian if E[exp(λ(X-μ))] ≤ exp(λ²σ²/2). Generalises bounded case.

**Union bound**: P(∪_i E_i) ≤ Σ_i P(E_i). Used to control failure probability across all rounds and arms simultaneously.

## Linear Bandit Terms

**Design matrix (A)**: A = Σ_t x_{t,A_t} x_{t,A_t}^T + I. Gram matrix of pulled feature vectors. A^{-1} gives uncertainty.

**Feature vector (x_{t,a})**: d-dimensional representation of arm a in round t.

**Information gain**: x^T A^{-1} x — measures how much pulling arm with feature x reduces uncertainty. LinUCB exploration bonus.

**Parameter (θ*)**: True linear reward parameter. θ̂ = A^{-1}b is the OLS estimator.

**Regularisation (I term)**: A = X^T X + I avoids singularity at cold start. λI with λ>0 controls bias-variance.
