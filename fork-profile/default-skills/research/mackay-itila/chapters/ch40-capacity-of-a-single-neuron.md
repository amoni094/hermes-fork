# Chapter 40: Capacity of a Single Neuron

## Core Idea
View learning as communication: data D_N are encoded into weights w, then read out by evaluating the neuron at the same N points. A binary threshold neuron with K inputs has capacity **2 bits per weight** (2K bits). Real-valued weights do not give infinite capacity once the receiver may only query the training locations.

## Key Concepts
- **Learning as a channel**: sender sees {t_n} at fixed {x_n}, runs a learner, ships w; receiver evaluates ŷ_n = f(w, x_n). Capacity ≈ how large N can be with tiny error probability.
- **Why not ∞**: you cannot inspect real w at infinite precision, nor query arbitrary x. Only the labelling of the given N points matters.
- **Threshold function**: y = f(∑_k w_k x_k) with f the sign/step. Bias: treat as K+1 by clamping one input to 1.
- **General position**: every subset of size ≤K is linearly independent; no K+1 on a hyperplane through the origin (or affine, with bias). Random points satisfy this.
- **T(N,K)**: number of distinct dichotomies of N points in general position in K dimensions realizable by a linear threshold.
- **Capacity N_max**: largest N such that essentially all 2^N labellings are realizable (error → 0). Result: N = 2K.

## Frameworks and Methods
- **Count, then compare to 2^N**: if T(N,K)/2^N → 1, the neuron can convey N bits; if T/2^N → 0, typical labellings are impossible (the channel cannot be reliable).
- **Recursion for T(N,K)**: adding a point splits some cells of weight space. Closed form is a partial sum of binomials:
  T(N,K) = 2 ∑_{i=0}^{K−1} C(N−1, i)
  (Cover’s counting; MacKay walks small (N,K) by hand first.)
- **Transition at N=2K**: for N < 2K almost all labellings work; for N > 2K a vanishing fraction do. Same flavour as a channel capacity threshold (Ch 9–10), slightly different definition.
- **Memory vs generalization**: using the neuron to *store* the training labels is the communication problem; *generalization* is predicting t_{N+1} at a new x.

## Key Equations
- y = f(∑_{k=1}^K w_k x_k),  f(a) = 1_{a>0} (or ±1)
- T(N,1) = 2
- T(N,K) = 2 ∑_{i=0}^{K−1} binom(N−1,i)
- Fraction realizable: T(N,K)/2^N
- Capacity: N_crit = 2K  (2 bits per weight)
- With bias: replace K by K+1
- VC-style intuition: linear threshold shattering number is K (or K+1 with bias); capacity as *communication* still 2K because typical, not worst-case, labellings matter

## Algorithms and Techniques
**Hand count (MacKay’s pedagogy)**
1. K=1: points on a line through origin; only 2 threshold functions.
2. One point: both labels possible → T(1,K)=2.
3. Recurse by adding a point in general position; hyperplanes through it split half the previous regions.

**Use in design**
1. To memorize N random binary labels, need K ≳ N/2 weights (threshold unit, general position).
2. Do not claim “infinite information in real weights”.
3. For generalization, N ≫ 2K is the interpolation regime — you *cannot* fit arbitrary labels, which is good.

## Anti-patterns
- **Infinite capacity because w ∈ ℝ^K**.
- **Probing the net at arbitrary x** when stating this theorem — that is a different channel.
- **Confusing 2 bits/weight with VC dimension = K**.
- **Expecting a real learner to find w whenever T says a separator exists** — existence ≠ efficient optimization (but linear threshold *is* linear programming).

## Key Takeaways
1. Weights are a communication channel about the training set.
2. Linear threshold capacity is 2 bits per weight.
3. General-position counting, not floating-point bits, sets the limit.
4. Below 2K, random labels are typically linearly separable; above, typically not.
5. This is Shannon thinking applied to a neuron; Hopfield capacity (Ch 42) is the recurrent analogue.

## Connects To
- **Ch 9–10**: capacity as a sharp threshold in N.
- **Ch 12**: hash codes — another “how many bits in a representation”.
- **Ch 39**: the neuron being counted.
- **Ch 42**: Hopfield capacity ~0.14 bits per synapse with Hebb, better with other rules.
- **Ch 44**: MLPs have much larger function classes; counting is harder.
