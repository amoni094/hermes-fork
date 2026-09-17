# Chapter 3: Discrete Random Variables

## Core Idea
Discrete r.v.s take countable values. Expectation, indicators, and conditional expectation have clean combinatorial formulas. The simple random walk is the prototype for Markov chains and martingales.

## Key Concepts
- **PMF** p(x) = P(X=x); Σp(x)=1
- **Expectation** E(X) = Σ x·p(x); E(g(X)) = Σ g(x)·p(x) (law of unconscious statistician)
- **Indicator** I_A: E(I_A) = P(A). Used to turn combinatorial sums into expectations.
- **Conditional expectation** E(X|Y=y) = Σ x P(X=x|Y=y)
- **Tower property** E(X) = E[E(X|Y)]
- **Bernoulli(p)** — P(X=1)=p; Binomial(n,p) = sum of n Bernoulli
- **Poisson(λ)** — P(X=k) = e^{-λ}λk/k!; limit of Binomial(n,p) with np=λ
- **Geometric(p)** — P(X=k) = p(1-p)^{k-1}; memoryless (P(X>m+n|X>n) = P(X>m))
- **Simple random walk** Sn = X₁+…+Xn, Xi = ±1; reflection principle for path counting

## Key Takeaways
1. Indicators turn combinatorial arguments into expectation calculations — use I_A, E(I_A)=P(A).
2. Memoryless property of geometric = discrete analog of exponential in renewal theory.
3. Poisson is the natural model for rare events; arrivals in disjoint intervals are independent.
4. Random walk: E(Sn)=0 (fair), var(Sn)=n → √n spread; reflection principle counts paths.

## Connects To
- **Ch06**: Random walk is a Markov chain; reflection principle → hitting probabilities.
- **Ch12**: Gambler's ruin solved by De Moivre's martingale + OST.
