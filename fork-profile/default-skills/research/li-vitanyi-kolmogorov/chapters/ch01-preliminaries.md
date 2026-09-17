# Chapter 1: Preliminaries

## Core Idea

Kolmogorov complexity is the length of a shortest effective description of an individual object. Restricting descriptions to partial computable functions yields an additively optimal universal method, so complexity is an intrinsic attribute of the object (up to an additive constant independent of the object). The Richard–Berry paradox is tamed by requiring descriptions to be executable; it reappears as a short incompressibility proof of Gödel incompleteness.

## Key Concepts

- Description method D: a function from finite binary descriptions Y into objects X; each description names at most one object.
- Descriptional complexity of x under D: length of a shortest y with D(y) = x; infinite if none exists.
- Effective description: D is a partial computable function. Non-effective methods have no additively optimal element (Example 2.0.1, previewed here).
- Optimal specification D0: minorizes every other partial computable D: descriptions under D0 are shortest up to an additive constant independent of x.
- Invariance (preview): all sufficiently powerful effective description syntaxes are equally succinct up to a fixed additive constant.
- Random (incompressible) finite string: shortest effective description is at least as long as the literal string.
- Prefix-free (self-delimiting) code: no codeword is a prefix of another; Kraft inequality applies.
- Shannon entropy H(P): ensemble uncertainty, not individual-object information. Li–Vitányi treat it as the probabilistic counterpart that Kolmogorov complexity will later match in expectation.
- Prefix codes, Kraft inequality, noiseless coding: coding-theoretic toolkit used throughout later chapters.
- State × symbol complexity: classical descriptional complexity of automata (transition tables), a pre-Kolmogorov notion.
- Roots: Solomonoff (prediction, 1960–64), Kolmogorov (individual randomness, 1965), Chaitin (program-size, 1966–69). Independently Levin, Martin-Löf, Schnorr.

## Frameworks and Methods

- Universal description via computability: restrict to partial computable functions so a universal Turing machine exists and optimality is possible.
- Incompressibility argument (preview of Ch 6): pick a string known to exist by counting (almost all strings of length n are incompressible); if a claimed property failed, the string would compress.
- Gödel via incompressibility (Example 1.1.1): in any sound formal system F of description length f, for all but finitely many random x the sentence “x is random” is unprovable. Searching for a proof of randomness of an n-bit string (n ≫ f) would print a random string from f + log n bits, contradiction.
- Prime-counting lower bound (Example 1.1.2, Chaitin): reconstruct n from the exponent vector of its prime factorization; for incompressible n this forces π(n) ≥ (log n)/(log log n) − o(1). A refined argument gives the classical π(n) = Ω(n / log n) order.
- Coding viewpoint: if sender and receiver share D, the cheapest transmission of x is a shortest D-description.

## Key Results and Theorems

- Four innovations of the theory (Li–Vitányi program): (1) effective descriptions cover every intuitively acceptable description; (2) there is a universal method that minorizes all others; (3) complexity is therefore an intrinsic attribute of the object; (4) Berry’s paradox becomes incompleteness.
- Counting: at most 2^{n+1} − 1 binary descriptions of length ≤ n, so most n-bit strings have C(x) ≥ n (made precise in Ch 2).
- Kraft inequality (Thm 1.11.1): a prefix code with lengths l1, l2, … exists iff sum 2^{−li} ≤ 1.
- Noiseless coding theorem: expected code length L satisfies H(P) ≤ L < H(P) + 1 for optimal prefix codes.
- Turing machines, universal TM, s-m-n theorem, Recursion theorem, halting problem: standard computability toolkit. The halting set is r.e. but not recursive; this later implies C and K are not computable.
- Asymptotic notation: O, o, Ω, Θ, ~ used additively on complexities (constants independent of the string).
- Pairing function ⟨x, y⟩: computable bijection N × N → N; C(x, y) := C(⟨x, y⟩).

## Algorithms and Techniques

1. Self-delimiting encoding of an integer n: 1^{l(n)} 0 n (length 2l(n)+1). Better: 1^{l(l(n))} 0 l(n) n, length l(n) + 2l(l(n)) + 1. Used constantly to concatenate programs.
2. Dovetailing: simulate all machines/programs in stages i = 1, 2, … executing step j of program k when j + k = i. Used to enumerate r.e. sets and lower-semicomputable functions.
3. Prefix-free integer codes: Elias, Shannon–Fano, and simple 1^k 0 encodings; later K(n) ≤ l(n) + 2 log l(n) + O(1).
4. Incompleteness proof template: compress a “first object with property P” if P is r.e. and sparse; contradiction if that object was chosen incompressible.

## Anti-patterns

- Treating “the least number not definable in fewer than twenty words” as a legal definition: descriptions must be effective, else Berry’s paradox.
- Comparing complexities across non-effective description methods: no optimal method exists, so “intrinsic complexity” is meaningless.
- Confusing Shannon information (average over an ensemble, relative to a known distribution) with Kolmogorov information (individual object, no ensemble).
- Ignoring additive constants: C_U and C_V differ by a constant depending on U, V but not on x; inequalities are always up to O(1) unless stated.
- Using unmarked concatenation of plain programs: you cannot parse p q without a length prefix; this is why C is not subadditive (Ch 2) and why prefix complexity is introduced (Ch 3).
- Claiming a specific long string is incompressible: incompressibility is not provable in any fixed sound theory for all but finitely many cases.

## Key Takeaways

1. Effectiveness is not a technical restriction; it is what makes complexity an objective attribute of the object.
2. Almost all strings are random; none of the long ones can be proved random in a given formal system.
3. Incompressibility is already a proof technique (primes, incompleteness) before C is even defined.
4. Prefix codes and Kraft’s inequality are the bridge from Shannon theory to later K-complexity.
5. History: Solomonoff wanted prediction, Kolmogorov wanted individual randomness, Chaitin wanted program-size; the book treats them as one theory with two main variants, C and K.

## Connects To

- Ch 2: formalizes C(x), C(x|y) and the invariance theorem sketched here.
- Ch 3: prefix restriction that removes logarithmic concatenation penalties.
- Ch 4: universal semimeasure as the probabilistic dual of K.
- Ch 5: Solomonoff prediction as the original motivation.
- Ch 6: incompressibility method developed from Examples 1.1.1–1.1.2.
