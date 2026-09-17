# Chapter 13: Universal Source Coding

## Core Idea
When the source law is unknown (only a class is known), the extra description length — redundancy — has a minimax value equal to the capacity of a channel from the unknown parameter to the data. Arithmetic coding lets you use a sequential estimate of p; Lempel–Ziv compresses individual sequences to the entropy rate of any stationary ergodic source without knowing it.

## Key Concepts
- **Redundancy**: r_n(q,p) = E_p[−log q(X^n)] − n H(p) = D(p^n || q). Minimax redundancy R_n = min_q max_p D(p^n||q).
- **Information radius**: R_n = min_q max_θ D(P_θ^n || q) = capacity of the channel θ → X^n.
- **Arithmetic coding**: sequential assignment of intervals of length q(x^n); implements −log q without Huffman trees; works with adaptive q.
- **LZ77 (sliding window)**: parse by longest match in a window; transmit pointer + length.
- **LZ78 (tree / incremental)**: distinct parsing into phrases, each a previous phrase plus one bit/symbol; transmit index + new symbol.
- **Individual-sequence / individual redundancy**: compress every sequence as well as the best compressor in a class.

## Frameworks and Methods
- **Minimax = capacity**: by Sion/von Neumann, min_q max_θ D(P_θ||q) = max_π min_q ∑ π_θ D(P_θ||q) = C(θ;X). Code using the capacity-achieving output distribution q^*.
- **Mixture / Krichevsky–Trofimov**: q(x^n) = ∫ p_θ(x^n) w(dθ); redundancy ≈ (k/2) log n for k-parameter models (Jeffreys prior).
- **Arithmetic coding**: maintain [low,high) with width p̂(x^n); emit bits as the interval nests into a dyadic cell. Precision issues are implementable (Pasco, Rissanen).
- **LZ78 optimality**: c(n) phrases, description ~ c log c bits; Ziv’s inequality + ergodic theorem ⇒ c log c / n → H(X).

## Key Results and Theorems

**Minimax redundancy = capacity (Section 13.1).**
C = max_π I(θ; X) = min_q max_θ D(p_θ || q) = min_q max_θ (E_{p_θ}[−log q(X)] − H(p_θ)).
The extra bits of universality equal the amount of information the sample gives about which source you are in.

**Example 13.1.1.** Two ternary sources p1=(1−α,α,0), p2=(0,α,1−α): minimax redundancy 1−α bits, equal to BEC(α) capacity.

**Binary universal coding.** For Bern(θ), θ∈[0,1], mixture with Dirichlet/Jeffreys yields redundancy (1/2)log n + O(1). Finite types (Ch 11) give |X| log n.

**Arithmetic coding.** If q is a sequential probability assignment, arithmetic coding produces a prefix code of length −log q(x^n)+O(1). Combined with KT/Laplace estimators, this is a practical universal code.

**Lemma 13.5.3 (Lempel–Ziv).** Distinct parsing of an n-bit string has c(n) ≤ n / ((1−ε_n) log n).

**Ziv’s inequality (Lemma 13.5.5).** For any distinct parsing, log Q(x^n|s) is bounded by a weighted entropy of phrase counts — the key to LZ for Markov.

**Theorem 13.5.2.** For binary stationary ergodic {X_n} with entropy rate H,
lim sup c(n) log c(n) / n ≤ H  a.s. (phrase-count bound).

**Theorem 13.5.3 (LZ78 optimality).** For binary stationary ergodic processes,
lim sup (1/n) l_{LZ78}(X^n) = H(X)  a.s.
(Sliding-window LZ77 similarly, Wyner–Ziv.)

**Redundancy of LZ78.** Typically O(1/log n), slower than the (k/2)(log n)/n parametric optimum; LZ is universal over *all* ergodic sources, so it cannot match parametric rates uniformly (Shields).

## Key Equations
- R_n = min_q max_p D(p^n||q) = C(θ; X^n)
- Mixture: q(x^n)=∫ p_θ(x^n) w(dθ)
- Parametric redundancy ~ (k/2) log n
- Arithmetic length ≈ −log q(x^n)
- LZ78: l(x^n) ≈ c(n) log c(n),  c log c / n → H

## Worked Example
Unknown Bern(θ). After seeing n bits with k ones, KT probability of next 1 is (k+1/2)/(n+1). Arithmetic coding with this assignment has expected redundancy (1/2)log n + O(1) relative to the true θ — you pay for learning θ.

LZ78 on 000...0: phrases 0, 00, 000, ... — only about √n phrases, l ≈ √n log n, rate → 0 = H. On incompressible bits, c ~ n/log n, l ~ n.

## Anti-patterns
- **Huffman with an estimated p after seeing the data, without encoding the model**: decoder does not have p. Either send the model (two-part MDL) or use sequential mixtures.
- **Expecting LZ to be optimal at moderate n**: redundancy 1/log n is slow; use context mixtures / PPM / CTW for parametric sources.
- **Claiming universal codes beat H**: they meet H, they do not undercut it on average.
- **Forgetting decoder synchronization in arithmetic coding**: must encode EOF or length.
- **Applying LZ optimality outside stationary ergodic**: individual-sequence guarantees need the finite-state compressibility formulation.

## Key Takeaways
1. Cost of not knowing the source = channel capacity from parameter to data.
2. Mixtures + arithmetic coding achieve the parametric minimax.
3. LZ78/LZ77 achieve entropy rate for every stationary ergodic source, with slow redundancy.
4. Universality class determines the extra-rate exponent (log n vs 1/log n).

## Connects To
- **Ch 5**: known-p Huffman/Shannon.
- **Ch 7**: the capacity appearing in minimax redundancy is literally channel capacity.
- **Ch 11**: types give an explicit finite-alphabet universal code.
- **Ch 14**: Kolmogorov complexity is the ultimate individual-sequence universal code; MDL.
- **Ch 16**: universal portfolios are the investment analog.
