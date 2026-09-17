---
name: hastie-esl
description: "Use when writing ML evaluation, regularization, or CV code."
related_skills:
  - coding-conventions
  - test-driven-development
  - systematic-debugging
  - evaluation-driven-development
  - mackay-itila
---

# Hastie ESL

Hastie, Tibshirani, Friedman, *The Elements of Statistical Learning* (2nd ed.). Knowledge base for ML evaluation, regularization, model complexity, and bias–variance. One thesis: **prediction error is bias² + variance + noise; training error is an optimistic stand-in; complexity must be chosen by a criterion that estimates extra-sample error, not by how well the fit hugs the training points.**

When evaluating or tuning a model, prefer ESL's move: decompose the error (bias vs variance) before touching hyperparameters; match the regularizer to the prior; never reuse the same observations for selection and assessment.

## Core Frameworks

### Bias–variance decomposition (Ch 2, 7.2–7.3)
For Y = f(X) + ε with E(ε)=0, Var(ε)=σε², squared-error prediction at x₀ decomposes as

Err(x₀) = σε² + [E f̂(x₀) − f(x₀)]² + E[f̂(x₀) − E f̂(x₀)]²
        = irreducible noise + bias² + variance.

Training error err always falls with complexity (often to 0). Test error Err has a U-shape: more complexity cuts bias, raises variance. The minimum of Err is the right complexity — not the minimum of err.

**Diagnosis before tuning:**
- High training error → bias problem (model too simple / underfit). Add capacity, features, or relax the penalty.
- Low training error + large train/test gap → variance problem (overfit). Shrink, prune, or get more data.
- Tuning hyperparameters without this diagnosis is guessing.

Two distinct jobs (Ch 7.2): **model selection** (compare models) vs **model assessment** (estimate generalization of the chosen one). If data-rich: train / validation / test, typically ~50/25/25. The test set is a vault — reuse it for selection and it underestimates true error.

### Overfitting (Ch 7.2, 11.5.2)
A model with zero training error is overfit and typically generalizes poorly. Optimism of training error is (2/N) Σ Cov(ŷᵢ, yᵢ): the harder you fit, the more each yᵢ influences its own prediction, the more err underestimates Err. For linear fits with d parameters, optimism ≈ 2(d/N)σε². Adaptive search (best subset of size d from p) has *effective* df > d — AIC formulas that plug in d are too kind.

### Regularization L2 / L1 (Ch 3.4, Ex 3.6–3.7)
Subset selection is discrete and high-variance. Shrinkage is continuous.

- **Ridge (L2):** minimize RSS + λ Σ βⱼ². Equivalent to a Gaussian prior β ~ N(0, τ I) with Gaussian sampling; λ = σ²/τ². Weight decay in neural nets is the same penalty (Ch 11). Standardize inputs; do not penalize the intercept. Effective df(λ) = tr(S_λ) ∈ (0, p], falling as λ grows. Use when many correlated predictors should share the signal (proportional shrinkage).
- **Lasso (L1):** RSS + λ Σ |βⱼ|. Laplace (double-exponential) prior — the L1 ball has corners on the axes, so solutions are sparse (soft-thresholding / continuous subset selection). Use when the domain prior is sparsity, not when L1 is merely fashionable.
- **Match the regularizer to the domain prior, not convention.** Dense correlated effects → L2. Few large effects, rest noise → L1. Mixed → elastic net (not ESL's main object, but the same prior-matching logic).

Choose λ / t by an estimate of prediction error (usually 10-fold CV). ESL's **one-standard-error rule:** pick the most parsimonious model whose CV error is within one SE of the minimum — the CV curve is itself noisy.

### Model selection: AIC / BIC / CV (Ch 7.5–7.10)
In-sample criteria add estimated optimism to err:

- **Cp / AIC:** err + 2 (d/N) σˆε²  (Gaussian; AIC = −2 loglik/N + 2d/N generally). Minimizes estimated test error. As N → ∞ AIC is *not* consistent — it overfits.
- **BIC:** −2 loglik + (log N) d. Same shape as AIC with 2 replaced by log N (heavier for N > e²). Approximates posterior model probability (Laplace evidence). Asymptotically consistent if the true model is in the family; in finite samples often underfits.
- **df for linear smoothers:** df = tr(S) where ŷ = Sy, not the raw parameter count. Neural-net weight decay: df(α) = Σ θ_m/(θ_m+α).

**CV vs analytic criteria:** AIC/BIC need a df and a likelihood. CV and bootstrap estimate extra-sample Err directly, for any loss and any adaptive fitter. Prefer CV when the fitter is nonlinear, searches, or 0–1 loss (AIC's 2d formula does not hold for 0–1).

No universal AIC-vs-BIC winner. Use BIC when you believe a true sparse model exists and N is large; AIC/CV when the goal is prediction on finite N.

### Cross-validation (Ch 7.10)
K-fold CV estimates expected extra-sample error Err = E[L(Y, f̂(X))], *not* the conditional Err_T for this particular training set.

CV(f̂) = (1/N) Σ L(yᵢ, f̂^{-κ(i)}(xᵢ)). Typical K = 5 or 10. K=N is LOO: low bias, high variance, expensive. K=5/10: lower variance; if the learning curve is still steep at N, CV overestimates Err (trains on (K−1)/K of the data).

**Wrong vs right CV (Ch 7.10.2):** screening features on *all* samples, then CV'ing the classifier, is leakage. ESL's genomic toy: N=50, p=5000 noise features, 1-NN on the 100 most correlated — wrong-way CV error ≈ 3% vs true 50%. **All preprocessing, selection, and tuning must sit inside each training fold.** Complexity-parameter selection is part of training; the held-out test set judges the *selected* model only.

GCV ≈ LOO for linear smoothers under squared error: (1/N) Σ [(yᵢ − ŷᵢ)/(1 − S_ii)]², with 1/(1−x)² ≈ 1+2x linking GCV to AIC.

### Bootstrap (Ch 7.11, 8.2)
Draw B samples of size N with replacement from Z; refit; the empirical distribution of S(Z*b) estimates the sampling distribution of S(Z) (variance, percentiles, CIs).

Naive bootstrap error (evaluate bootstrap fits on the original training set) is too optimistic: each observation is in a given bootstrap sample with probability ≈ 0.632, so train/test overlap. Use **leave-one-out bootstrap** (score i only on replicates that omit i) or the **.632 / .632+** corrections.

Like CV, bootstrap estimates Err well, Err_T poorly. Report **bootstrap (or CV-fold) confidence intervals**, not a lone point estimate — the CV curve's SE bands exist because the estimate is noisy. A metric without uncertainty is an incomplete specification.

Bagging (Ch 8.7) is bootstrap aggregation: average high-variance fits to cut variance. Random forests (Ch 15) add de-correlation.

### Curse of dimensionality (Ch 2.5, 12.3.4, 18)
Sampling density scales as N^{1/p}. A dense 1-D sample of N=100 needs N=100^{10} in 10-D for the same density. In a unit cube, capturing 10% of the volume in p=10 requires covering ~80% of each axis. Most points lie closer to the boundary than to each other — prediction becomes extrapolation.

Local methods (kNN, kernels) fail first: neighborhoods empty or huge. Structured models (linearity, additivity, sparsity) are how ESL escapes the curse — not by claiming kernels magically beat it (SVMs do not; Ch 12.3.4). When p ≫ N (Ch 18), prefer explicit regularization (ridge/lasso/shrunken centroids) and never trust univariate screens that saw the test labels.

**Production implication:** a model that looks good on low-p test fixtures can collapse on high-p, sparse production inputs. Dimensionality mismatch is a distribution shift, not a code bug.

## Chapter Index

| Ch | Title | Key topics |
|----|-------|------------|
| 1 | Introduction | supervised learning, examples |
| 2 | Overview of Supervised Learning | LS vs kNN, decision theory, curse of dimensionality, bias–variance |
| 3 | Linear Methods for Regression | Gauss–Markov, subset, ridge, lasso, LARS, PCR/PLS |
| 4 | Linear Methods for Classification | LDA, logistic, L1-logistic, separating hyperplanes |
| 5 | Basis Expansions and Regularization | splines, df, RKHS, wavelets |
| 6 | Kernel Smoothing | local regression, density, naive Bayes |
| 7 | Model Assessment and Selection | bias–variance, AIC/BIC/MDL/VC, CV, bootstrap |
| 8 | Model Inference and Averaging | bootstrap vs ML, Bayes, EM, MCMC, bagging, stacking |
| 9 | Additive Models, Trees, MARS | GAM, CART, PRIM, missing data |
| 10 | Boosting and Additive Trees | AdaBoost, gradient boosting, shrinkage |
| 11 | Neural Networks | PPR, backprop, overfitting, weight decay |
| 12 | SVMs and Flexible Discriminants | kernel SVM, FDA/PDA/MDA, curse |
| 13 | Prototype Methods and Nearest-Neighbors | k-means, LVQ, adaptive metrics |
| 14 | Unsupervised Learning | clustering, PCA, SOM, ICA, PageRank |
| 15 | Random Forests | OOB, variable importance, de-correlation |
| 16 | Ensemble Learning | bet-on-sparsity, regularization paths |
| 17 | Undirected Graphical Models | Markov graphs, RBMs |
| 18 | High-Dimensional Problems p ≫ N | shrunken centroids, L1 classifiers, FDR |

## Coding rules (mined)

1. Decompose error into bias vs variance *before* tuning.
2. Match L2 (Gaussian, dense) vs L1 (Laplace, sparse) to the domain prior.
3. ML test suites need a CV harness; train-set scores are tautological.
4. All selection/preprocessing inside each fold (wrong-way CV).
5. Report bootstrap/CV intervals, not point estimates.
6. Test-vs-prod ML failures: check dimensionality / sparsity mismatch before rewriting the model.
