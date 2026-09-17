# Chapter 41: Learning as Inference

## Core Idea
The regularized training objective M(w) = G(w) + α E_W(w) *is* −log posterior. The product of learning is not a point w* but an ensemble P(w|D). Predictions average y(x;w) over that ensemble. Implement by Monte Carlo or by a Gaussian (Laplace) approximation around w_MP.

## Key Concepts
- **Likelihood**: y(x;w) ≡ P(t=1|x,w);  P(D|w) = exp[−G(w)] with G the cross-entropy.
- **Prior**: P(w|α) ∝ exp(−α E_W); quadratic E_W ⇒ Gaussian prior, variance 1/α.
- **Posterior**: P(w|D,α) ∝ exp(−M(w)); w_MP is a mode, not “the answer”.
- **Why logs**: errors add, probabilities multiply; log keeps the correspondence.
- **Predictive distribution**: P(t_new|x_new,D) = ∫ P(t|x,w) P(w|D) dw, *not* P(t|x,w_MP).
- **Occam / error bars**: far from data, averaging over w flattens y toward 0.5; a point estimate stays overconfident.

## Frameworks and Methods
- **Two-weight cartoon**: plot likelihood as a function of w, multiply by a broad Gaussian prior, watch the blob shrink with N. Traditional learning reports the mode; Bayes keeps the blob.
- **Monte Carlo neuron**: Metropolis or HMC on M(w); each sample is a classifier; average their y’s. This is the implementation MacKay wants you to see is *easy* in 2–10-D.
- **Gaussian / Laplace implementation**: at w_MP, Hessian A = ∇∇M; approximate P(w|D) ≈ Normal(w_MP, A^{−1}). Predictive y is a sigmoid of a *weakened* activation (MacKay–Spiegelhalter–Qazaz trick: extra variance in a shrinks the logistic toward ½).
- **Hyperparameter α**: can be optimized by evidence P(D|α) (Ch 28) or given a hyperprior.

## Key Equations
- M(w) = G(w) + α E_W(w)
- G(w) = −∑ [t ln y + (1−t) ln(1−y)]
- E_W = ½ ∑ w_i²
- P(t|w,x) = y^t (1−y)^{1−t}
- P(w|D,α) = e^{−M(w)} / Z_M
- Predictive: P(t=1|x,D) = ∫ y(x;w) P(w|D) dw
- Laplace: A_{ij} = ∂²M/∂w_i ∂w_j |_{w_MP},  P(w|D) ≈ N(w_MP, A^{−1})
- Evidence: ln P(D|α) ≈ −M(w_MP) − ½ ln det A + const
- Moderated logistic: if a ~ N(μ, σ_a²),  E[σ(a)] ≈ σ(μ / √(1+π σ_a²/8))  (schematic)

## Algorithms and Techniques
**Bayesian prediction with one neuron**
1. Define G, E_W, α.
2. Find w_MP by minimizing M (as in Ch 39).
3. Either:
   - **MC**: sample w^{(t)} ~ exp(−M), average y(x; w^{(t)});
   - **Laplace**: compute Hessian, average by quadrature or the σ_a correction.
4. Optional: maximize P(D|α) w.r.t. α (evidence procedure).

**What you should see in the 2-D plots**
- Few data: posterior ≈ prior, predictions uncertain.
- More data: cigar in w-space aligns with the separating direction; gain remains uncertain longer than orientation.

## Anti-patterns
- **Using y(x; w_MP) as P(t=1|x,D)** especially far from the data cloud.
- **Calling MAP “Bayesian”** without error bars or evidence.
- **Ignoring α** or setting it by train error alone (overfitting control belongs in the evidence / CV).
- **Laplace on a multimodal M** — use MC (Ch 29–30).

## Key Takeaways
1. Regularized error is a log posterior; own that interpretation.
2. Learn ensembles, predict by averaging.
3. Point estimates are overconfident between clusters and outside the data.
4. MC and Laplace are the two practical computers of this posterior.
5. This is the Bayesian story that MLPs (Ch 44) and GPs (Ch 45) inherit.

## Connects To
- **Ch 27–28**: Laplace and Occam / evidence.
- **Ch 29–30**: Monte Carlo on w.
- **Ch 33**: variational alternative to Laplace/MC.
- **Ch 39**: the likelihood and regularizer being interpreted.
- **Ch 44–45**: same story in multilayer nets and in function space.
