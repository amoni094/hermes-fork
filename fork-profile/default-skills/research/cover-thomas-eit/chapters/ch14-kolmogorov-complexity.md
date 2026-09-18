# Chapter 14: Kolmogorov Complexity

## Core Idea
Kolmogorov complexity K(x) is the length of the shortest program that prints x. It is computer-independent up to an additive constant, incompressible strings pass statistical tests, and for i.i.d. data E K(X^n|n) ≈ nH(X). It is the individual-sequence, probability-free foundation under entropy, Occam, MDL, and universal probability.

## Key Concepts
- **Universal computer U**: a Turing machine that can simulate any other (prefix-free / self-delimiting versions preferred so Kraft applies).
- **K_U(x) = min {l(p) : U(p)=x}**. Conditional K(x|y): shortest program given y on the tape.
- **Invariance**: K_U(x) ≤ K_A(x) + c_A for any other machine A.
- **Algorithmically random**: K(x^n | n) ≥ n. Incompressible infinite x: K(x^n|n)/n → 1.
- **Universal probability**: P_U(x) = ∑_{p: U(p)=x} 2^{−l(p)} = Pr(random program prints x).
- **Coding theorem**: K(x) ≈ −log P_U(x) ≈ −log m(x) (Solomonoff–Levin a priori).
- **Kolmogorov sufficient statistic**: shortest program for a model class that makes x typical.
- **MDL**: two-part code L(model)+L(data|model); Kolmogorov is the ideal MDL.

## Frameworks and Methods
- **Count programs, not sequences**: <2^k programs of length <k ⇒ <2^k strings with K<k.
- **Self-delimiting / prefix complexity**: programs form a prefix code ⇒ ∑ 2^{−K(x)} ≤ 1 (Kraft). Then P_U is a semimeasure.
- **Entropy connection**: a Shannon code is a program (table + index); a short program yields a code. Expectation pins K to H.
- **Occam**: among explanations, the shortest program has the highest P_U, hence is preferred.

## Key Results and Theorems

**Theorem 14.2.1 (Invariance).** For universal U and any computer A, K_U(x) ≤ K_A(x)+c_A. So drop the subscript: K(x).

**Theorem 14.2.2.** K(x|l(x)) ≤ l(x)+c. (Print the bits you are given.)

**Theorem 14.2.3.** K(x) ≤ K(x|l(x)) + 2 log l(x) + c. (Self-delimiting length.) Sharper: + log^* l(x).

**Theorem 14.2.4 (Counting).** |{x : K(x)<k}| < 2^k.

**Theorem 14.2.5.** For x^n ∈ {0,1}^n,
K(x^n|n) ≤ n H(k/n) + (1/2) log n + c
where k=# of ones (describe k, then the type class index).

**Lemma 14.3.1.** ∑_{p: U(p) halts} 2^{−l(p)} ≤ 1 (prefix-free U).

**Theorem 14.3.1 (K and entropy).** For i.i.d. X_i on a finite alphabet with pmf f,
(1/n) E K(X^n | n) → H(X).
Also E K(X^n|n) ≤ nH + o(n); lower bound by Kraft + D≥0.

**Theorem 14.4.2.** K(n) ≤ log^* n + c.

**Theorem 14.4.3.** K(n) > log n for infinitely many n.

**Theorem 14.5.1.** For Bern(1/2), P(K(X^n|n) < n−k) < 2^{−k}. Almost all sequences are incompressible.

**Theorem 14.5.2 (SLLN for incompressible sequences).** If x is incompressible, then (1/n)∑ x_i → 1/2. Martin-Löf: incompressible sequences pass all effective tests.

**Theorem 14.5.3.** X_i i.i.d. Bern(θ) ⇒ (1/n) K(X^n|n) → H(θ) in probability.

**Universal probability / coding theorem.** K(x) = −log P_U(x) + O(1). Hence P_U(x) ≈ 2^{−K(x)}.

**Occam / MDL.** The shortest description of the data is the preferred hypothesis; two-part MDL approximates K.

**Uncomputability.** K is not computable (halting problem). Upper bounds exist (any program you found); no general lower bound algorithm.

## Key Equations
- K_U(x) = min_{U(p)=x} l(p)
- K_U ≤ K_A + c_A
- |{K<k}| < 2^k
- E K(X^n|n) ≈ n H(X)
- P_U(x) ≈ 2^{−K(x)}
- ∑ 2^{−K(x)} ≤ 1
- K(x^n|n) → n H(θ) in probability for Bern(θ)

## Worked Example
n zeros: K(0^n | n) ≤ c (program: “print n zeros”). Highly compressible.

A typical Bern(1/3) string with n/3 ones: K ≈ n H(1/3) ≈ 0.918 n. A Shannon code for Bern(1/3) almost achieves this; Kolmogorov may shave only O(log n) by using regularity if any exists.

Berry paradox / uncomputability: “the shortest number not definable in ten words” is the same obstruction that makes K uncomputable.

## Anti-patterns
- **Treating additive constants as negligible for short strings**: c_A can dwarf l(x) in practice; K is an asymptotic/philosophical tool.
- **Claiming to compute K**: you can only upper-bound it.
- **Using plain (non-prefix) complexity for ∑ 2^{−K}**: Kraft can fail; prefer prefix complexity.
- **Equating K(x) with −log p(x) pathwise**: only in expectation / in probability for stochastic x; a compressible random-looking string can still have tiny p.
- **Ignoring the input of n**: K(x^n) vs K(x^n|n) differ by up to ~2 log n.

## Key Takeaways
1. K is unique up to a machine-dependent constant.
2. Entropy is expected Kolmogorov complexity.
3. Almost all strings are incompressible; those that are not have structure.
4. Universal probability implements Solomonoff induction; MDL is the practical shadow.
5. Uncomputable — use it as a gold standard, not an algorithm.

## Connects To
- **Ch 2–5**: entropy and codes as computable special cases of K.
- **Ch 11–13**: types and LZ are computable approximations to K.
- **Ch 6, 16**: universal gambling / portfolios from P_U.
- **Ch 12**: MDL choice of maxent order p.
