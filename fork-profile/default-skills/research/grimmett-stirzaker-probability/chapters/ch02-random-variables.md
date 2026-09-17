# Chapter 2: Random Variables and Their Distributions

## Core Idea
A random variable X is a measurable function from (Ω,F,P) to ℝ. Its distribution (law) is the induced probability measure on ℝ. The law of averages and Monte Carlo simulation flow directly from this framework.

## Key Concepts
- **Random variable** — Borel-measurable function X: Ω → ℝ
- **Distribution function (CDF)** — F(x) = P(X ≤ x); right-continuous, non-decreasing, F(−∞)=0, F(∞)=1
- **Law/distribution of X** — the probability measure μX on ℝ induced by X
- **Expectation** — E(X) = ∫ X dP = ∫ x dF(x)
- **Variance** — var(X) = E[(X−E(X))²] = E(X²) − (E(X))²
- **Monte Carlo** — estimate E(f(X)) by averaging f(Xi) over iid samples Xi ~ F

## Key Takeaways
1. A random variable is a function; its distribution is the push-forward measure.
2. Two r.v.s can be equal in distribution (same CDF) but live on different probability spaces.
3. Monte Carlo: E[f(X)] ≈ (1/n)Σf(Xi) with error O(1/√n) by CLT — distribution-free.
4. Expectation is linear; E[X+Y] = E[X]+E[Y] always, even without independence.

## Connects To
- **Ch03/04**: Discrete/continuous specializations of this general framework.
- **Ch07**: Convergence theorems for expectations and distributions.
