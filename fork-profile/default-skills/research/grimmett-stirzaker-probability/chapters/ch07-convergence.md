# Chapter 7: Convergence of Random Variables

## Core Idea
There are multiple modes of convergence for random variables, ordered by strength. The law of large numbers, CLT, and martingale convergence theorem each use different modes for different purposes. Knowing which mode applies — and what conditions guarantee it — is essential for asymptotic arguments.

## Frameworks Introduced

- **Hierarchy of convergence modes**:
  - a.s. (almost sure) → convergence in probability → convergence in distribution
  - L^r (r-th mean) → convergence in probability
  - a.s. + bounded → L^r (by bounded convergence)

- **Weak Law of Large Numbers**: n⁻¹Sn →P μ. Sufficient: iid with finite mean (or weaker via char. functions).
- **Strong Law of Large Numbers (Thm 7.4.3)**: n⁻¹Sn → μ a.s. iff E|X₁| < ∞ (for iid). The L²-proof uses variance ∝ 1/n → 0.
- **Martingale Convergence Theorem (Thm 7.8)**: If (Y,F) is a submartingale with sup_n E(Yn⁺) < ∞, then Y∞ = lim Yn exists a.s. and E|Y∞| < ∞.
- **Conditional Expectation E(X|G)**: The G-measurable random variable minimizing E[(X - Z)²] over all G-measurable Z. Key properties: tower (E[E(X|Y₁,Y₂)|Y₁] = E[X|Y₁]), linearity, E[Xg(Y)|Y] = g(Y)E[X|Y].
- **Uniform Integrability (§7.10)**: Family {Xi} is UI if sup_i E(|Xi|·I{|Xi|>c}) → 0 as c→∞. UI + convergence in probability → L¹ convergence.

## Key Concepts

- **a.s. convergence** — Xn → X on an event of probability 1
- **L^r convergence** — E|Xn - X|^r → 0
- **Convergence in probability** — P(|Xn - X| > ε) → 0 for all ε
- **Convergence in distribution** — FXn(x) → FX(x) at continuity points
- **Doob's upcrossing inequality** — (b-a)E[Un(a,b)] ≤ E[(Yn - a)⁺]; used to prove martingale convergence
- **Uniform integrability** — condition bridging convergence in probability and L¹ convergence
- **Tower property** — E[E(X|Y₁,Y₂)|Y₁] = E[X|Y₁]; fundamental for iterated conditioning
- **Fatou's lemma** — E[lim inf Xn] ≤ lim inf E[Xn] for non-negative sequences
- **Dominated convergence** — Xn → X a.s. + |Xn| ≤ Z with E(Z)<∞ → E(Xn) → E(X)

## Mental Models

- "Doob's upcrossing argument": If a process fluctuates infinitely often between a and b, the expected number of crossings would be infinite — but the martingale condition bounds this, forcing eventual convergence.
- Strong LLN vs. Weak: Strong says one null set covers all n simultaneously; weak says for each ε the probability of large deviation → 0.
- Conditional expectation as projection: E(X|G) is the orthogonal projection of X onto the space of G-measurable random variables (in L² sense).

## Anti-patterns

- **Confusing modes**: Convergence in distribution does NOT imply convergence in probability (CLT example: Sn/√n is not close to N(0,1) as a number, only distributionally).
- **Forgetting uniform integrability**: Martingale convergence a.s. does NOT give L¹ convergence without UI.
- **Applying strong LLN without finite mean**: If E|X₁| = ∞, Sn/n may diverge a.s. (Cauchy example).

## Worked Example

**Strong LLN proof sketch** (§7.4.3): For L² case: E[(Sn/n − μ)²] = var(X₁)/n → 0 by independence. For a.s., find subsequence nk = k² where Borel-Cantelli applies via Chebyshev: P(|Snk/nk − μ| > ε) ≤ var(X₁)/(nk²ε²) = summable. Then fill gaps by monotonicity (for non-negative Xi) and generalize.

## Key Takeaways

1. a.s. convergence is the strongest common mode; implies convergence in probability and in distribution.
2. Strong LLN: E|X₁| < ∞ is necessary and sufficient for iid sequences.
3. Martingale convergence theorem: bounded (in expectation) submartingales converge a.s.
4. Uniform integrability is the bridge from a.s./probability convergence to L¹ convergence.
5. Tower property of conditional expectation is used everywhere in martingale theory.

## Connects To

- **Ch12**: Doob's upcrossing inequality here is the tool proving martingale convergence in Ch12.
- **Ch05**: CLT proved via characteristic functions in Ch05; this chapter gives the LLN in depth.
- **Ch06**: Ergodic theorem for Markov chains is a strengthening of LLN.
