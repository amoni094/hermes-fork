# Glossary — Understanding Machine Learning

## Core Terms

**Agnostic PAC learning**: PAC learning without the realizability assumption. The learner competes against the best h ∈ H rather than assuming perfect separability.

**ERM (Empirical Risk Minimization)**: Choose h = argmin_{h∈H} L_S(h). Fundamental algorithm; PAC-learns all finite classes and all finite-VCdim classes.

**FTRL (Follow the Regularized Leader)**: Online learning rule: w_{t+1} = argmin_w [∑ℓ_s(w) + R(w)]. Generalizes OGD. Achieves O(√T) regret.

**Inductive bias**: Prior knowledge built into the learning algorithm via the hypothesis class H. No-Free-Lunch theorem says bias is necessary.

**Lipschitz function**: |f(w) - f(u)| ≤ ρ·‖w-u‖ for all w,u. Lipschitz losses have bounded gradients: ‖∇f‖ ≤ ρ.

**Littlestone dimension (Ldim)**: Analog of VC dimension for online learning. H is online-learnable iff Ldim(H) < ∞. Ldim(halfspaces in R^d) = ∞.

**No-Free-Lunch Theorem**: For any learning algorithm, there exists a distribution D such that L_D(A(S)) ≥ ½ for m ≤ |X|/2. All learners must have inductive bias.

**OCO (Online Convex Optimization)**: General framework: at each round, pick w^(t) ∈ H (convex set), suffer convex loss f_t(w^(t)), update. Regret = ∑f_t(w^t) - min_w ∑f_t(w).

**OGD (Online Gradient Descent)**: w^{t+1} = Π_H(w^t - η·v_t) where v_t ∈ ∂f_t(w^t). Achieves O(√T) regret with optimal step size.

**PAC (Probably Approximately Correct)**: Framework: learner outputs h with L_D(h) ≤ ε with probability ≥ 1-δ, given m ≥ m(ε,δ) samples.

**Realizability**: Assumption that ∃ h* ∈ H with L_D(h*) = 0. Relaxed to agnostic PAC for real-world use.

**Regret**: Cumulative excess loss of online algorithm vs. best fixed comparator in hindsight. O(√T) is optimal for convex-Lipschitz online learning.

**RLM (Regularized Loss Minimization)**: argmin_w [L_S(w) + R(w)]. R stabilizes the learner.

**Sauer's Lemma**: The growth function Π_H(m) ≤ ∑_{i=0}^d C(m,i) ≤ (em/d)^d. Limits effective hypothesis count.

**Stability (on-average-replace-one)**: E_{S,i}[ℓ(A(S^(i)), z_i) - ℓ(A(S), z_i)] ≤ β(m). Stable algorithms don't overfit (Theorem 13.2).

**Strong convexity**: f(αu+(1-α)v) ≤ αf(u)+(1-α)f(v) - (μ/2)·α(1-α)·‖u-v‖². Makes optimization landscape strongly bowl-shaped.

**VC dimension**: VCdim(H) = largest m s.t. H shatters some set of size m. H PAC-learnable iff VCdim finite (Fundamental Theorem of PAC learning, Ch 6).

**Weighted Majority**: Online algorithm using multiplicative weight updates on experts. Achieves O(√(log|H|·T)) regret for finite expert classes.

## Symbol Table

| Symbol | Meaning |
|--------|---------|
| H | Hypothesis class |
| ε | Accuracy parameter |
| δ | Confidence parameter (failure prob) |
| m | Sample size / number of examples |
| d | VC dimension |
| D | Unknown data distribution |
| L_D(h) | True risk of h under D |
| L_S(h) | Empirical risk of h on sample S |
| η | Learning rate / step size |
| λ | Regularization strength |
| ρ | Lipschitz constant of loss |
| B | Bound on ‖w*‖ |
| T | Number of online rounds |
| R(w) | Regularizer function |
| R_A | Regret of algorithm A |
| Ldim | Littlestone dimension |
| γ | Margin |
