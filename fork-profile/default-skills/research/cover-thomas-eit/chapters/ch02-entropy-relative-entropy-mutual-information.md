# Chapter 2: Entropy, Relative Entropy, and Mutual Information

## Core Idea
Entropy, relative entropy (KL), and mutual information are three tightly related functionals of probability mass functions. Their algebra — chain rules, nonnegativity, data-processing, Fano — is the entire formal language of the book.

## Key Concepts
- **Entropy**: H(X) = −∑_{x} p(x) log p(x). Convention: 0 log 0 = 0. Units: bits (log2) or nats (ln).
- **Joint entropy**: H(X,Y) = −∑∑ p(x,y) log p(x,y).
- **Conditional entropy**: H(Y|X) = ∑_x p(x) H(Y|X=x) = −∑∑ p(x,y) log p(y|x).
- **Relative entropy / KL**: D(p||q) = ∑ p(x) log(p(x)/q(x)) ∈ [0, ∞]. Not a metric: not symmetric, no triangle inequality.
- **Mutual information**: I(X;Y) = D(p(x,y) || p(x)p(y)) = ∑∑ p(x,y) log(p(x,y)/(p(x)p(y))).
- **Conditional mutual information**: I(X;Y|Z) = H(X|Z) − H(X|Y,Z).
- **Markov chain** X → Y → Z: p(x,y,z) = p(x)p(y|x)p(z|y); equivalently X ⟂ Z | Y.
- **Sufficient statistic**: T(X) is sufficient for θ if θ → T(X) → X; equivalently I(θ; X) = I(θ; T(X)).
- **Convex / concave**: f convex iff f(λx1+(1−λ)x2) ≤ λ f(x1)+(1−λ)f(x2). Entropy is concave in p; D(p||q) is convex in the pair (p,q).

## Frameworks and Methods
- **Venn diagram of information**: H(X,Y) = H(X)+H(Y)−I(X;Y); I(X;Y) = H(X)−H(X|Y) = H(Y)−H(Y|X). Use only as bookkeeping — it fails for n≥4 variables without care.
- **Information inequality first**: D(p||q) ≥ 0 (Gibbs / Jensen on −log) is the master inequality; almost every later inequality is a corollary.
- **Chain-rule expansions**: expand H(X^n), I(X^n;Y), D(p(x,y)||q(x,y)) by successive conditioning.
- **Data-processing**: no (possibly random) function of Y can increase I(X; ·).
- **Fano for converses**: turn “small error” into “small H(X|Y)”, hence an upper bound on rate.

## Key Results and Theorems

**Lemma 2.1.1.** H(X) ≥ 0.

**Lemma 2.1.2.** H_b(X) = (log_b a) H_a(X). Change of base is a constant factor.

**Theorem 2.2.1 (Chain rule).** H(X,Y) = H(X) + H(Y|X). Corollary: H(X,Y|Z) = H(X|Z) + H(Y|X,Z).

**Theorem 2.4.1 (Mutual information and entropy).**
I(X;Y) = H(X) − H(X|Y) = H(Y) − H(Y|X) = H(X)+H(Y)−H(X,Y); I(X;X) = H(X).

**Theorem 2.5.1 (Chain rule for entropy).** H(X1,...,Xn) = ∑_{i=1}^n H(Xi | X^{i−1}).

**Theorem 2.5.2 (Chain rule for information).** I(X1,...,Xn; Y) = ∑_{i=1}^n I(Xi; Y | X^{i−1}).

**Theorem 2.5.3 (Chain rule for relative entropy).** D(p(x,y)||q(x,y)) = D(p(x)||q(x)) + D(p(y|x)||q(y|x)).

**Theorem 2.6.2 (Jensen).** If f is convex, E f(X) ≥ f(E X). Strict convexity ⇒ equality iff X is a.s. constant.

**Theorem 2.6.3 (Information inequality).** D(p||q) ≥ 0 with equality iff p=q. Proof: −log convex ⇒ Jensen, or log-sum. Corollaries: I(X;Y) ≥ 0 iff independence; I(X;Y|Z) ≥ 0 iff conditional independence.

**Theorem 2.6.4.** H(X) ≤ log |X|, equality iff X is uniform. Proof: D(p||u) = log|X| − H(X) ≥ 0.

**Theorem 2.6.5 (Conditioning reduces entropy).** H(X|Y) ≤ H(X), equality iff X ⟂ Y. Caveat: H(X|Y=y) may exceed H(X); the inequality is *average*.

**Theorem 2.6.6 (Independence bound).** H(X1,...,Xn) ≤ ∑ H(Xi), equality iff independent.

**Theorem 2.7.1 (Log-sum inequality).** ∑ a_i log(a_i/b_i) ≥ (∑ a_i) log(∑ a_i / ∑ b_i) for nonnegative a_i, b_i.

**Theorem 2.7.2.** D(p||q) is convex in the pair (p,q).

**Theorem 2.7.3.** H(p) is concave in p.

**Theorem 2.7.4.** I(X;Y) is concave in p(x) for fixed p(y|x), and convex in p(y|x) for fixed p(x). This is why C = max_p I(X;Y) is a concave maximization.

**Theorem 2.8.1 (Data-processing inequality).** If X → Y → Z, then I(X;Y) ≥ I(X;Z). Equality iff X → Z → Y. Corollary: I(X;Y) ≥ I(X; g(Y)).

**Theorem 2.10.1 (Fano’s inequality).** For any estimator X̂ with X → Y → X̂ and P_e = Pr(X ≠ X̂),
H(P_e) + P_e log|X| ≥ H(X|X̂) ≥ H(X|Y).
Weaker: P_e ≥ (H(X|Y) − 1)/log|X|. If H(X|Y)>0 then P_e>0.

## Key Equations
- H(X) = −∑ p log p
- H(X,Y) = H(X)+H(Y|X)
- I(X;Y) = D(p(x,y)||p(x)p(y)) = H(X)−H(X|Y)
- D(p||q) ≥ 0
- Binary entropy: H(p) = −p log p − (1−p) log(1−p), H_2(p) ∈ [0,1], max at p=1/2
- I(X;Y|Z) = H(X|Z) − H(X|Y,Z)

## Worked Example
Joint (X,Y) with p(0,0)=1/2, p(0,1)=1/4, p(1,0)=0, p(1,1)=1/4 (Cover–Thomas table). Then H(X)=0.81 bits, H(Y)=1 bit, H(X,Y)=1.5 bits, H(X|Y)=0.5, H(Y|X)=0.69, I(X;Y)=0.31. Check: 0.81+1−1.5 = 0.31. Conditioning on Y reduces H(X) from 0.81 to 0.5.

Court-case caveat (Thm 2.6.5): H(X)=0.544, H(X|Y=1)=0, H(X|Y=2)=1, average H(X|Y)=0.25 < H(X). One observation increased uncertainty; the average decreased.

## Anti-patterns
- **Treating D(p||q) as a distance**: D(p||q) ≠ D(q||p); infinite if supp(p) ⊈ supp(q).
- **Pointwise conditioning reduces entropy**: false; only in expectation.
- **Processing can extract more information**: DPI forbids it. Feature maps cannot increase I(X; ·).
- **Using I(X;Y|Z) ≥ I(X;Y) always**: false off Markov chains. Classic: X,Y independent bits, Z=X+Y, then I(X;Y)=0 but I(X;Y|Z)=1/2.
- **Forgetting 0 log 0 = 0 and p log(p/0)=∞**.

## Key Takeaways
1. Start every argument from D ≥ 0 or from a chain rule.
2. I is both “reduction in entropy” and “KL from independence”.
3. DPI is the no-free-lunch theorem of inference.
4. Fano converts converse coding arguments into entropy bounds.
5. Concavity of I in the input distribution makes capacity a convex program.

## Connects To
- **Ch 3**: AEP is WLLN applied to −log p(X).
- **Ch 5**: L ≥ H from Kraft + information inequality (wrong-code penalty is D).
- **Ch 7**: C = max I; converse uses Fano + DPI.
- **Ch 8**: same identities with integrals; h can be negative.
- **Ch 11**: D is the large-deviation rate; Fisher information is a local D.
- **Ch 17**: this chapter restated as a catalog of inequalities.
