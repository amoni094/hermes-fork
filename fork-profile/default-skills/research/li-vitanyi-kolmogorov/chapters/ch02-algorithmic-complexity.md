# Chapter 2: Algorithmic Complexity

## Core Idea

Plain Kolmogorov complexity C(x) is the length of a shortest program that makes a fixed universal Turing machine output x. The invariance theorem says any two universal machines yield complexities differing by only an additive constant independent of x, so C is an intrinsic property of the string. Pedagogically Li–Vitányi introduce C first because it is the original Solomonoff–Kolmogorov–Chaitin definition and is intuitively “shortest program,” then show its quantitative defects (failure of subadditivity, complexity oscillations) that motivate prefix complexity K in Chapter 3.

## Key Concepts

- C_f(x) = min { l(p) : f(p) = n(x) }, or ∞ if no such p. Here f is a partial function (a “computer”), p a binary program, n(x) a standard index of object x.
- Additive optimality: f is additively optimal for a class C if f ∈ C and for every g ∈ C there is c_{f,g} with C_f(x) ≤ C_g(x) + c_{f,g} for all x.
- Equivalence of methods: |C_f − C_g| bounded iff each minorizes the other.
- No optimal element among all partial functions: map i ↦ x_i with C_f(x_i) ≥ i, then C_g(x_i) = log i + O(1) (Example 2.0.1). Effectiveness is essential.
- Reference universal TM U: U(⟨n, p⟩) = φ_n(p), with self-delimiting encoding of n. Plain complexity C(x) := C_U(x); conditional C(x|y) := C_U(x|y).
- Notation convention of the book: C = plain (unrestricted programs); K = prefix (self-delimiting programs). Do not mix with authors who write K for plain complexity.
- Incompressible (C-random) string: C(x) ≥ l(x). c-incompressible: C(x) ≥ l(x) − c.
- C as integer function: C : N → N is unbounded, goes to infinity slower than any unbounded computable function, has arbitrarily large “drops.”
- Martin-Löf randomness for infinite sequences: a constructive null set (effective sequential test) covers the non-random sequences. Equivalent (up to details) to C(ω_{1:n}) ≥ n − O(1) failing; oscillations prevent a clean C-characterization, which is why K is preferred for infinite sequences.
- Algorithmic information: I(x : y) analogue is imperfect for C; exact symmetry needs K (Ch 3).

## Frameworks and Methods

- Invariance as foundation: almost every later application uses only “C is shortest program length up to O(1) independent of the object.”
- Upper bounds by exhibition: to prove C(x) ≤ n + O(1), exhibit a TM that prints x from n bits (often the identity TM).
- Lower bounds by counting / incompressibility: at most 2^{n−c+1} strings have C(x) < n − c, so the vast majority of n-bit strings satisfy C(x) ≥ n − c.
- Conditional complexity: extra information y on the auxiliary tape can only help: C(x|y) ≤ C(x) + O(1).
- Pair complexity C(x, y) = C(⟨x, y⟩): joint description of two objects plus a way to tell them apart.

## Key Results and Theorems

- Lemma 2.1.1: there is an additively optimal universal partial computable function.
- Invariance theorem (Thm 2.1.1): there is a universal TM U such that for every partial computable φ, C(x|y) ≤ C_φ(x|y) + c_φ for all x, y. Thus |C_U − C_V| ≤ O(1) for any two universals.
- Trivial upper bound (Thm 2.1.2): C(x) ≤ l(x) + c and C(x|y) ≤ C(x) + c. Constants later computed as 8 and 2 in §3.9.
- Computable bijections preserve C: if φ is total computable injective, |C(φ(x)) − C(x)| = O(1). In particular |C(x) − C(x^R)| = O(1) and C(xx) ≤ C(x) + O(1).
- Failure of subadditivity (Eq. 2.2): C(x, y) ≤ C(x) + C(y) + 2 log min(C(x), C(y)) + O(1). The log term is necessary: there exist x, y of length ≤ n with C(x, y) ≥ C(x) + C(y) + log n − O(1). Conditioning on C(x) removes it: C(x, y | C(x)) ≤ C(x) + C(y) + O(1).
- Incompressibility counting (Thm 2.2.1): the fraction of n-bit strings with C(x) < n − c is less than 2^{−c+1}.
- C(x) as integer function: lim inf C(x)/log x = 1, but C is not computable, not even approximable from above and below. C is upper semicomputable (enumerable from above): dovetail all programs and decrease the current upper bound when a shorter program for x halts.
- Complexity of complexity: C(C(x) | x) can be almost log n; C is far from smooth.
- Statistical properties: incompressible strings satisfy law of large numbers, no long runs of zeros beyond O(log n), pass Martin-Löf tests, look “typical.”
- C(x | l(x)) ≤ n + O(1) for l(x) = n, and most strings achieve ≈ n.
- Information inequality defects: C(x) − C(x|y) is not symmetric in x, y up to O(1).

## Algorithms and Techniques

1. Universal simulation encoding: program for U is 1^{l(n)} 0 n p, so C_U(x) ≤ C_{T_n}(x) + 2 l(n) + 1.
2. Identity machine for C(x) ≤ l(x) + O(1).
3. Parsing two plain programs: send l(p) in self-delimiting form plus p q; this is the origin of the 2 log C(x) penalty.
4. Upper-semicomputation of C: on input x, dovetail; output the length of the shortest program found so far (never increases).
5. Randomness test: reject x if C(x) < l(x) − c for a chosen c (e.g. 20). Type I error ≤ 2^{−c+1}.

## Anti-patterns

- Writing C(x, y) ≤ C(x) + C(y) + O(1): false for plain complexity; the log term is essential. This is the main reason the book moves to K.
- Treating C as computable: if C were computable you could print the first n-bit incompressible string from O(log n) bits.
- Using C(ω_{1:n}) ≥ n − O(1) as a definition of infinite-sequence randomness: complexity oscillations (C of prefixes dips infinitely often by ~ log n) break it. Use Martin-Löf tests or prefix complexity (Ch 3).
- Confusing additive O(1) (machine-dependent, string-independent) with terms that grow with n.
- Claiming a concrete famous constant (π, e) is “complex”: C(π_{1:n}) = K(n) + O(1) = O(log n), extremely compressible.
- Using unmarked concatenation xy as a substitute for the pair ⟨x, y⟩ without length information.

## Key Takeaways

1. Invariance is the entire theoretical foundation for most applications: exhibit any description, then U is at most a constant worse.
2. C is the right first definition and the wrong last definition: concatenation and infinite-sequence randomness force prefix machines.
3. Almost all strings are incompressible; incompressibility is a noneffective but abundant property.
4. Upper bounds are constructive (show a program); lower bounds are counting or “if shorter, then contradiction with incompressibility.”
5. C is upper semicomputable and not computable; this is the same phenomenon as the halting problem.

## Connects To

- Ch 1: makes the informal D0 and Berry/Gödel discussion fully rigorous.
- Ch 3: prefix machines restore subadditivity and exact symmetry of information.
- Ch 4: coding theorem relates 2^{−K(x)} to the universal semimeasure; C has no equally clean coding theorem.
- Ch 6: incompressibility method uses C (or K) counting as the existence engine.
