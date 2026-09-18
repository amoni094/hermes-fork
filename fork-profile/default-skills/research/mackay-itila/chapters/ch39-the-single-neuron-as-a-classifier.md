# Chapter 39: The Single Neuron as a Classifier

## Core Idea
A single neuron is already a statistical classifier: y = f(w·x + b) with logistic, tanh, linear, or threshold f. Supervised learning is function minimization in weight space. The logistic neuron is the same object as Gaussian-channel pulse detection (Ch 11) and logistic regression. Regularization (weight decay) is required beyond raw error descent.

## Key Concepts
- **Architecture**: inputs x_i, weights w_i, optional bias w_0 with x_0≡1; one output y.
- **Activation vs activity**: a = w·x (plus bias); y = f(a). Do not confuse the two.
- **Activation functions**: linear y=a; logistic 1/(1+e^{−a}) ∈ (0,1); tanh ∈ (−1,1); threshold Θ(a); stochastic (Bernoulli with logistic probability, or Metropolis flips).
- **Weight space**: each w is a function y(·;w). |w| controls sigmoid gain (steepness); direction of w is the normal to iso-output lines.
- **Error / objective**: sum over examples of how far y(x^{(n)};w) is from target t^{(n)}. Training = minimize G(w) (then M = G + regularizer).
- **Supervised learning**: given pairs (x,t), search for w that fits; hope to generalize.

## Frameworks and Methods
- **Linear logistic as posterior**: for two Gaussians with shared covariance, P(s=1|y) is logistic in a linear function of y (Ch 11). So the neuron *is* that posterior.
- **Gradient training**: backpropagation is trivial for one layer — ∂G/∂w_i from the chain rule. Many minimizers use G and ∇G.
- **Binary cross-entropy**: G(w) = −∑ [t ln y + (1−t) ln(1−y)] is the proper log-loss for y ∈ (0,1) as a probability. Squared error on 0/1 targets is the inferior default.
- **Regularization (Ch 39.4)**: unconstrained |w|→∞ on separable data (infinite-gain threshold). Weight decay α‖w‖² / Gaussian prior stops this and implements Occam.

## Key Equations
- a = ∑_{i=0}^I w_i x_i    (x_0=1)
- logistic: y = 1/(1+e^{−a})
- tanh: y = tanh(a)
- threshold: y = Θ(a)
- stochastic: P(y=1|a) = 1/(1+e^{−a})
- G(w) = −∑_n [ t^{(n)} ln y^{(n)} + (1−t^{(n)}) ln(1−y^{(n)}) ]
- ∂y/∂a = y(1−y)  for logistic
- δ-style gradient: ∂G/∂w_i = ∑_n (y^{(n)}−t^{(n)}) x_i^{(n)}   (logistic + cross-entropy)
- Regularized: M(w) = G(w) + α EW(w),  EW = ½ ∑ w_i²

## Algorithms and Techniques
**Train a logistic neuron**
1. Initialize w small random (or 0).
2. For each example or minibatch: a=w·x, y=σ(a), accumulate (y−t)x.
3. w ← w − η ∇G − η α w  (gradient step + weight decay).
4. Repeat; monitor G on train and a held-out set.

**Geometry in 2-D**
- Lines perpendicular to w have constant y.
- Along w, y ramps from 0 to 1; |w| sets ramp width ~1/|w|.

## Anti-patterns
- **Squared error + sigmoid** without noticing the gradient saturates when you are *wrong* and confident.
- **No regularizer on linearly separable data** — weights explode, “perfect” train, brittle.
- **Threshold units + gradient descent** — gradient is zero almost everywhere.
- **Calling the activation a the “output”**.

## Key Takeaways
1. One neuron + logistic + log-loss = logistic regression = Gaussian posterior odds.
2. Learning is search in function space, parameterized by w.
3. Gain |w| and orientation are different degrees of freedom.
4. Regularize; descent on G alone is not the whole story.
5. This neuron is the brick for MLPs (Ch 44) and the subject of capacity (Ch 40) and Bayesian learning (Ch 41).

## Connects To
- **Ch 11**: Gaussian channel, linear logistic posterior.
- **Ch 22**: another “single unit” statistical model (mixtures).
- **Ch 40**: how many labellings a threshold neuron can realize.
- **Ch 41**: M(w) as −log posterior.
- **Ch 44**: stack these units; backprop.
