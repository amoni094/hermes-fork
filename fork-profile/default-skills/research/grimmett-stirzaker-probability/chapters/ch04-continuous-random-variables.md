# Chapter 4: Continuous Random Variables

## Core Idea
Continuous r.v.s are described by PDFs. Joint distributions and conditional distributions require care with densities. The multivariate normal is the key distribution for theoretical results. Coupling provides a powerful technique for proving distributional inequalities.

## Key Concepts
- **PDF** f(x) ≥ 0, ∫f(x)dx=1; F(x) = ∫_{-∞}^x f(t)dt
- **Expectation** E(X) = ∫ x·f(x)dx; E(g(X)) = ∫ g(x)f(x)dx
- **Joint PDF** f_{X,Y}(x,y); marginal f_X(x) = ∫ f_{X,Y}(x,y)dy
- **Conditional density** f_{X|Y}(x|y) = f_{X,Y}(x,y)/f_Y(y)
- **Multivariate normal** N(μ,Σ): uncorrelated ↔ independent; characterized by mean vector and covariance matrix
- **Exponential(λ)**: memoryless; inter-arrival times for Poisson process
- **Coupling**: joint distribution (X,Y) on same space; if X=Y a.s., then P(X∈A)=P(Y∈A) — proves distributional bounds
- **Poisson approximation**: sum of dependent Bernoullis ≈ Poisson when each P(Xi=1) small

## Key Takeaways
1. Multivariate normal: uncorrelated ⟺ independent (unique among distributions).
2. Conditional expectations for jointly normal (X,Y): E(Y|X=x) = μY + ρ(σY/σX)(x−μX) — linear in x.
3. Coupling: construct X,Y jointly to make P(X≠Y) ≤ ε; proves ||μ−ν||_TV ≤ ε.
4. Change of variables: if Y=g(X), then f_Y(y) = f_X(g⁻¹(y))/|g'(g⁻¹(y))|.

## Connects To
- **Ch09**: Gaussian processes generalize multivariate normal to infinite-dimensional case.
- **Ch06**: Coupling technique used to prove Markov chain convergence to stationarity.
