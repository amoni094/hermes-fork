# Chapter 4: Algorithmic Probability

## Core Idea

Algorithmic probability identifies three a priori distributions that coincide up to a multiplicative constant: the universal lower-semicomputable discrete semimeasure m(x), the Solomonoff–Levin a priori probability Q_U(x) = sum_{U(p)=x} 2^{−l(p)}, and the algorithmic probability 2^{−K(x)}. The coding theorem says log 1/m(x) = K(x) + O(1). This is the precise bridge from description length to probability, and it is why prefix complexity (not plain C) is the right complexity for induction.

## Key Concepts

- Lower semicomputable (enumerable from below) function: there is a total computable φ(x, k) nondecreasing in k with lim_k φ(x, k) = f(x). Dual: upper semicomputable.
- Discrete semimeasure: P : N → [0, 1] with sum_x P(x) ≤ 1 (not necessarily = 1; leftover mass is “non-halting”).
- Universal discrete semimeasure m: a lower-semicomputable semimeasure that multiplicatively dominates every other: for each lower-semicomputable semimeasure P, m(x) ≥ 2^{−K(P)} P(x) for all x (Eq. 4.2). The book fixes one reference m.
- Mixture construction: m(x) = sum_j 2^{−K(j)} P_j(x), where P_j enumerates all lower-semicomputable discrete semimeasures. Alternative weights 2^{−j} also work but give worse domination constants.
- Conditional m(x|y) = sum_j 2^{−K(j)} P_j(x|y). Same domination: 2^{K(P)} m(x|y) ≥ P(x|y).
- A priori probability Q_U(x): probability that the reference prefix machine U outputs x when the input tape is fair coin tosses (equivalently, sum of 2^{−l(p)} over programs p with U(p) = x).
- Continuous sample space: semimeasures on {0,1}^∞, cylinders Γ_x, universal continuous semimeasure M (Solomonoff’s mixture over measures). M(x) is the a priori probability of a finite string as a prefix of a random infinite sequence.
- No universal computable semimeasure (Lemma 4.3.1): the class of computable discrete semimeasures has no universal element. Lower semicomputability is the maximal effective class that still has a universal element.
- Five complexities (Table 4.1): relations among C, K, −log m, −log M, and process complexity, for l(x) = n.

## Frameworks and Methods

- Universality by mixture: any countable class of semimeasures with r.e. weights has a dominating mixture. Choose weights 2^{−K(j)} to get domination constant equal to the complexity of the dominated object.
- Coding theorem method: one direction 2^{−K(x)} ≤ Q_U(x) = O(m(x)) is immediate (shortest program contributes; Q_U is a lower-semicomputable semimeasure). The converse builds a Shannon–Fano-style prefix code of length log 1/m(x) + O(1) and invokes invariance.
- Universal average-case complexity: the m-average of a complexity measure is determined by the worst case on simple objects; used later for “universal search” (Ch 7).
- Continuous vs discrete: M(x) = m(x) · 2^{O(K(l(x)))} roughly; they differ by the complexity of the length. Do not interchange them for prediction (Ch 5 uses M on sequences).

## Key Results and Theorems

- Existence of universal m (Thm 4.3.1): the mixture of all lower-semicomputable discrete semimeasures is itself one, and dominates each with factor 2^{−K(P)}.
- Conditional domination (Thm 4.3.2): 2^{K(P)} m(x|y) ≥ P(x|y).
- Coding theorem (Thm 4.3.3): log 1/m(x) = log 1/Q_U(x) = K(x), equality up to an additive constant independent of x. Equivalently m(x) = Θ(2^{−K(x)}).
- Conditional coding theorem (Thm 4.3.4): −log m(x|y) = K(x|y) + O(1). This is the missing piece used in the proof of symmetry of information (Thm 3.8.1).
- Shannon–Fano lemma (Lemma 4.3.3): if P is a semimeasure, there is a prefix code with l(E(x)) ≤ log 1/P(x) + 2.
- No computable universal semimeasure (Lemma 4.3.1): from a putative computable universal P0 one constructs a computable Q that P0 fails to dominate.
- Universal average-case: the m-expected running time of algorithms, and m-expected C or K, match the corresponding quantities under any computable distribution up to a constant factor depending on that distribution.
- Continuous coding relations: −log M(x) = K(x) + O(1) is false in general; −log M(x) ≈ K(x | l(x)) or K(x) − K(l(x)) depending on normalization. Table 4.1 is the reference.
- m(x) ≥ c / (x log x log log x ⋯) along the maximal convergent series (Figure 4.1): m puts as much mass as Kraft allows on simple integers.

## Algorithms and Techniques

1. Dovetail to lower-semicompute m or Q_U: run all programs in parallel; whenever U(p) = x, add 2^{−l(p)} to the mass of x. The approximation increases to the true value and never decreases.
2. Shannon–Fano / algorithmic code from m: order the integers, lay intervals of width ≈ m(x) in [0, 1), output a dyadic prefix of that interval. Length log 1/m(x) + 2.
3. Mixture weights: prefer 2^{−K(j)} over 2^{−j} when the dominated semimeasure is itself simple; the domination constant is then 2^{K(P)} not 2^{index(P)}.
4. Conditional version: freeze y and mix over conditional semimeasures P(·|y).
5. Conversion between M and m: M(x) = sum_{y} m(xy) in the discrete-to-continuous embedding; be careful with the leftover mass of non-halting.

## Anti-patterns

- Using C in place of K in the coding theorem: sum_x 2^{−C(x)} = ∞, so 2^{−C} is not a semimeasure and cannot equal m.
- Treating m as a computable prior you can plug into a Bayesian algorithm: m is only lower semicomputable; the denominator for normalization is not computable. Solomonoff induction is a limiting, not an implemented, predictor.
- Assuming the class of computable measures has a universal element: it does not (Lemma 4.3.1). You must enlarge to lower-semicomputable semimeasures.
- Confusing discrete m(x) with continuous M(x): prediction of the next bit uses M(xb)/M(x), not m.
- Dropping the O(1) in −log m(x) = K(x) and then summing or taking exponentials: multiplicative Θ(1) is the true statement.
- Defining conditional probability as m(x)/m(y) for unrelated x, y: the book’s m(x|y) is a mixture of conditionals, not a Kolmogorov-axiom conditional (Exercise 4.3.7).

## Key Takeaways

1. Description length and a priori probability are the same quantity: K(x) ≈ −log m(x).
2. Universality of m is Occam’s razor in measure form: simple distributions get exponentially higher prior weight 2^{−K(P)}.
3. Lower semicomputability is the sweet spot: weaker than computable (so a universal element exists), strong enough to dovetail.
4. The coding theorem is why prefix complexity, not plain C, is the language of induction, MDL, and information distance.
5. Q_U, m, and 2^{−K} coinciding is presented by Li–Vitányi as evidence that the notion is “inherent,” not an artifact of one formalization.

## Connects To

- Ch 3: Kraft + prefix machines make 2^{−K} a semimeasure; symmetry of information uses Thm 4.3.4.
- Ch 5: Solomonoff prediction is M(next | past); MDL is a computable approximation using two-part codes.
- Ch 7: time-bounded universal distributions and Levin’s universal search rest on m-style mixtures with clocks.
- Ch 8: algorithmic entropy and information distance use −log m and K interchangeably via the coding theorem.
