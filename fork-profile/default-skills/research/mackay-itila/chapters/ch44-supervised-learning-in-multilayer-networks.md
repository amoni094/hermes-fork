# Chapter 44: Supervised Learning in Multilayer Networks

## Core Idea
Multilayer perceptrons (backprop nets) are feedforward maps y(x; w, A) with nonlinear hidden units. Traditional training minimizes a squared-error (regression) or log-loss (classification). Bayesian reading: the net + a prior on w defines a prior on *functions*; learning is posterior inference. In the large-hidden-unit limit that prior *is* a Gaussian process (Ch 45). Complexity is controlled by weight magnitudes (hyperparameters), not by H once H is large.

## Key Concepts
- **Two-layer net** (MacKay’s counting: layers of *computational* units, inputs not counted): hidden a_j = ∑_l w_{jl} x_l + θ_j,  h_j = tanh(a_j); output a_i = ∑_j w_{ij} h_j + θ_i,  y_i = f^{(2)}(a_i) (linear for regression).
- **Architecture A**: functional form; w = all weights and biases.
- **Traditional training**: minimize ∑_n ‖t^{(n)} − y(x^{(n)};w)‖² by gradient descent / conjugate gradients; gradients via backpropagation.
- **Hyperparameters**: σ_bias, σ_in, σ_out set typical function amplitude ~ √H σ_out, horizontal scale ~ σ_bias/σ_in, shortest scale ~ 1/σ_in.
- **Neal’s limit**: H→∞, iid random weights ⇒ prior on y(·) independent of H; a Gaussian process. Adding hidden units does not automatically overfit if weights stay prior-typical.

## Frameworks and Methods
- **Weight-space exploration**: sample random w from Gaussians with those σ’s and *plot y(x)* — this is how you understand the prior, same as Ch 39’s 2-D weight space.
- **Learning as inference**: P(w|D) ∝ P(D|w) P(w|α); predict by integrating (Ch 41). Benefits: error bars, automatic complexity control via evidence, model comparison of architectures.
- **Why Bayes helps here**: MLPs are hugely identifiable (many w give the same function); MAP+evidence/MC averages in function space rather than trusting one w*.
- **Regularization**: separate weight decay groups (input weights vs output weights) correspond to different σ_in, σ_out — MacKay’s automatic relevance determination (ARD) lives here.

## Key Equations
- h_j = tanh(∑_l w_{jl} x_l + θ_j)
- y_i = f^{(2)}(∑_j w_{ij} h_j + θ_i)
- Regression likelihood: P(t|x,w,β) = N(y(x;w), β^{−1} I)
- G(w) = (β/2) ∑_n ‖t^{(n)}−y^{(n)}‖²   (−log likelihood, up to const)
- M(w) = G(w) + ∑_g (α_g/2) ‖w_g‖²
- Typical scales:  |y| ~ √H σ_out ;  length ~ 1/σ_in ;  envelope ~ σ_bias/σ_in
- Posterior predictive as in Ch 41: ∫ y(x;w) P(w|D) dw

## Algorithms and Techniques
**Traditional backprop regression**
1. Forward: compute h, y.
2. Backward: δ_output = (y−t) f^{(2)′}, δ_hidden = (W_out^T δ_out) f^{(1)′}.
3. Gradient = outer products of δ with lower-layer activities.
4. Update w; optionally add weight decay.

**Bayesian MLP (MacKay)**
1. Put Gaussian priors with groupwise α_g.
2. Find w_MP; Laplace evidence for α, β; or HMC on w (Neal).
3. Predict with error bars from the posterior, not from a single net.

## Anti-patterns
- **More hidden units ⇒ more complexity** without looking at |w|. In the GP limit, H is irrelevant.
- **One global weight decay** when input scales differ (no ARD).
- **Reporting only y(x; w_MP)** as if it had error bars.
- **Squared error for classification**.

## Key Takeaways
1. MLPs are nonlinear parametric maps trained by gradient descent on a loss.
2. Random-weight plots teach the prior: scales live in σ_in, σ_bias, σ_out.
3. Large H + reasonable priors → GP-like functions; complexity ≠ parameter count.
4. Bayesian MLPs give moderation, evidence, ARD.
5. If you only need the GP limit, skip the parameters (Ch 45).

## Connects To
- **Ch 39–41**: one neuron, then inference.
- **Ch 27–28**: Laplace evidence for α.
- **Ch 30**: HMC on network weights.
- **Ch 45**: discard w and use C(x,x′) directly.
- **Ch 46**: nets as inverse maps (deconvolution) vs proper image priors.
