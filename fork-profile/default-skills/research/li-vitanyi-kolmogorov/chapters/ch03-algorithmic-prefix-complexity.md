# Chapter 3: Algorithmic Prefix Complexity

## Core Idea

Prefix (self-delimiting) Kolmogorov complexity K(x) is C computed on prefix Turing machines: the domain of programs is a prefix-free set. Programs can be concatenated without end-markers, so K is subadditive and supports an exact symmetry-of-information theorem. Li–Vitányi present K as the version “tweaked to have just the right quantitative properties”; most theorems for C transfer with the same proofs, but the log-penalty phenomena disappear.

## Key Concepts

- Prefix function / prefix machine: a partial computable ψ such that if ψ(p) is defined, then ψ(q) is undefined for every proper extension q of p. Equivalently, a self-delimiting machine that never reads past the end of its program (halting = implicit end-marker).
- K(x|y) = C_{ψ0}(x|y) for a fixed additively optimal prefix function ψ0; K(x) = K(x|ε).
- Self-delimiting program p for x: U(p) = x and U does not read beyond p. The same p may be a valid program for many different auxiliaries y; the union over y of domains need not be prefix-free (Example 3.1.2).
- K(x, y) := K(⟨x, y⟩). Subadditive: K(x, y) ≤ K(x) + K(y) + O(1), and K(xy) ≤ K(x) + K(y) + O(1).
- Relation to C: K(x) ≤ C(x) + K(C(x)) + O(1); also C(xy) ≤ K(x) + C(y) + O(1). Typically K(x) = C(x) + C(C(x)) + O(1) up to small terms; K(x) = C(x) + O(log C(x)).
- Complexity of complexity: K(K(x) | x) is unbounded (Thm 3.7.1); this blocks exact analogues of Shannon’s chain rule with only K(y|x).
- Chaitin’s Ω: Ω = sum_{U(p)↓} 2^{−l(p)}, the halting probability of the reference prefix machine. Ω is Martin-Löf random, encodes the halting problem in its bits, and has K(Ω_{1:n}) ≥ n − O(1).
- Algorithmic mutual information: I(x : y) = K(y) − K(y|x). A second form I(x ; y) = K(x) + K(y) − K(x, y).

## Frameworks and Methods

- Prefix restriction as coding hygiene: Kraft’s inequality applies directly to programs, so sum_x 2^{−K(x)} ≤ 1. This is why K has a coding theorem (Ch 4) and C does not (sum 2^{−C(x)} diverges).
- Exact additivity via shortest programs: replace the condition x by ⟨x, K(x)⟩ (equivalently, by a shortest program x* for x).
- Oscillation picture for infinite sequences: a Martin-Löf random ω satisfies K(ω_{1:n}) ≥ n + K(n) − O(1) (or ≥ n − O(1) depending on the exact criterion; Table 3.1 lists equivalent K-criteria). Ω itself has characteristic oscillations around the lower bound.

## Key Results and Theorems

- Invariance theorem (Thm 3.1.1): there is an additively optimal universal partial computable prefix function ψ0. K is well-defined up to O(1).
- Trivial bounds: K(x) ≤ l(x) + 2 log l(x) + O(1); K(x | l(x)) ≤ l(x) + O(1). The extra 2 log n vs C’s n + O(1) is the self-delimiting overhead of encoding length.
- Subadditivity (Example 3.1.3): K(x, y) ≤ K(x) + K(y) + O(1). Proof: run the prefix machine on x* then on y*; no length prefix needed.
- Incompressibility: the number of x with K(x) < n is less than 2^n; most n-bit strings have K(x) ≥ n. More sharply K(x) ≥ n + K(n) − O(1) for most x of length n.
- Complexity of complexity (Thm 3.7.1): K(K(x)|x) is unbounded; in fact there is no computable upper bound independent of x. Consequence: |K(x, y) − K(x) − K(y|x)| can be Ω(log K(x)), so the naive chain rule is only logarithmic-close.
- Symmetry of algorithmic information (Thm 3.8.1): K(x, y) = K(x) + K(y | x, K(x)) up to O(1). This is the exact analogue of Shannon’s H(X, Y) = H(X) + H(Y|X).
- Corollary 3.8.1: K(⟨x, K(x)⟩, y) = K(⟨x, K(x)⟩) + K(y | ⟨x, K(x)⟩) + O(1).
- Symmetry of mutual information (Thm 3.8.2, typical form): I(x : y) = I(y : x) up to O(1) when information is defined with the shortest-program condition, i.e. K(x) − K(x | y*) = K(y) − K(y | x*) + O(1). Also I(x ; y) = I(y ; x) + O(1).
- Information inequality: I(x : y) ≥ 0 up to O(1) fails in the same way C did unless the condition includes K(x); with the right definition, deficiency of randomness and mutual information behave.
- Sizes of constants (§3.9): with a carefully chosen reference machine one can take concrete small constants (e.g. C(x) ≤ n + 8). A 425-bit universal combinator is exhibited as an existence proof that constants can be made modest.
- Ω is incompressible and Turing-complete for the halting problem: the first n bits of Ω decide the halting of all programs of length ≤ n.

## Algorithms and Techniques

1. Prefix TM implementation: input tape is one-way; the machine is not allowed to look past the last symbol it “accepts.” Halting converts a plain machine into a self-delimiting one only after adding a length header.
2. Concatenation of shortest programs: x* y* is a legal program for ⟨x, y⟩ on a modified prefix U.
3. Kraft–Chaitin theorem (used constantly): a r.e. sequence of lengths n_i with sum 2^{−n_i} ≤ 1 yields a prefix-free set of programs of those lengths; used to build machines from weight requirements.
4. Relating K and C: encode C(x) with a prefix code of length K(C(x)), then dump the plain shortest program.
5. Ω approximation: dovetail all programs; add 2^{−l(p)} whenever p halts. After enough time the first n bits stabilize iff you have solved all haltings of programs ≤ n bits (you never know when).

## Anti-patterns

- Treating K(x|y) programs as a global prefix code: for each fixed y the domain is prefix-free, but the union over y is not (Example 3.1.2). Kraft does not apply to {K(x|y)} indiscriminately.
- Writing K(x, y) = K(x) + K(y|x) + O(1): false; you need K(y | x, K(x)) or y | x*. The error is Θ(log K(x)) infinitely often.
- Using K(x) ≤ n + O(1) as the trivial bound: without knowing n in a self-delimiting way you pay 2 log n. K(x | n) ≤ n + O(1) is the right statement.
- Defining infinite randomness by K(ω_{1:n}) ≥ n − O(1) without the K(n) term: Table 3.1 distinguishes the criteria; the robust one includes K(n).
- Assuming time-bounded prefix and self-delimiting machines coincide: without time bounds they do; with time bounds it is open (pointer to Ch 7).

## Key Takeaways

1. Prefix-free programs are the coding-theoretic repair of C: Kraft applies, concatenation is free, chain rule becomes exact if you condition on x*.
2. K(x) = C(x) + Θ(log C(x)) typically; they are interchangeable for incompressibility applications at leading order.
3. Symmetry of information is the algorithmic analogue of Shannon’s chain rule and is the workhorse of later information-distance results (Ch 8).
4. Ω is the concrete random real: a single number that is incompressible and encodes all of computability theory.
5. Complexity of complexity is the obstruction to every “too exact” identity; expect O(log n) slop unless the theorem explicitly absorbs K(x) into the condition.

## Connects To

- Ch 2: K is C on a restricted machine class; subadditivity is the problem C failed.
- Ch 4: coding theorem −log m(x) = K(x) + O(1) needs prefix-freeness so 2^{−K} is a semimeasure.
- Ch 5: Solomonoff mixture is sum of 2^{−K(μ)} μ; uses K as the prior weight.
- Ch 8: information distance E(x, y) = max{K(x|y), K(y|x)} uses symmetry of information.
