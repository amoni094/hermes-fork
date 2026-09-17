# Chapter 17: Inequalities in Information Theory

## Core Idea
A reorganization of the book’s inequalities plus new ones: subset entropy rates, L^p–entropy, Fisher–entropy (de Bruijn), the entropy power inequality (EPI) and its Brunn–Minkowski cousin, and determinant inequalities (Hadamard, Minkowski). The technical engine is convexity plus Gaussian extremals.

## Key Concepts
- **Entropy power**: N(X) = (1/(2πe)) 2^{2h(X)} for a real random variable (nats); N(X)=σ^2 if X is Gaussian.
- **EPI**: N(X+Y) ≥ N(X)+N(Y) for independent reals X,Y.
- **Brunn–Minkowski**: Vol(A+B)^{1/n} ≥ Vol(A)^{1/n}+Vol(B)^{1/n}; EPI is the information analog.
- **Fisher information** J(X) of a location family / of a density: ∫ (f')^2 / f.
- **de Bruijn**: d/dt h(X+√t Z) = (1/2) J(X+√t Z), Z~N(0,1) independent.
- **Subset entropy rates**: averages of H(X_A)/|A| over subsets; Han’s inequality.
- **Hadamard**: |K| ≤ ∏ K_{ii} for K ≽ 0.

## Frameworks and Methods
- **Catalog first**: restates Jensen, log-sum, D≥0, conditioning reduces entropy, chain rules, Fano, from Ch 2 and 8.
- **Gaussian extremals**: many inequalities become equalities iff Gaussians (or uniforms, or independents).
- **EPI via Fisher**: prove Stam’s inequality J(X)^{-1}+J(Y)^{-1} ≤ J(X+Y)^{-1}, integrate de Bruijn from t=0 to ∞ (Gaussians appear as the heat-flow limit).
- **Types combinatorial bounds**: |T(P)| ≤ 2^{nH(P)}; entropy vs counting.
- **Determinants as Gaussian entropies**: h(N(0,K))=(1/2)log((2πe)^n|K|), so entropy inequalities ⇒ matrix inequalities.

## Key Results and Theorems

**Restatements (Section 17.1–17.3).**
- Jensen: f convex ⇒ f(EX)≤E f(X).
- Log-sum inequality.
- 0 ≤ H(X) ≤ log|X|.
- H(X|Y)≤H(X); chain rule; independence bound.
- D(p||q)≥0; I≥0; D convex in (p,q); H concave in p.
- Fano: H(P_e)+P_e log|X| ≥ H(X|Y).
- Pr(X=X') ≥ 2^{−H(X)} for i.i.d. copies.

**Han’s inequality / subset entropy (Section 17.6).** For a random vector X^n,
(1/n) H(X^n) ≤ (1/(n−1)) (1/n) ∑_i H(X^{n\i}) ≤ ⋯ ≤ (1/n) ∑ H(X_i),
i.e. average entropy rates of k-subsets decrease in k. (Useful for converse proofs and combinatorics.)

**Cramér–Rao (Thm 17.7.1).** var(T) ≥ 1/J(θ) for unbiased T.

**de Bruijn (Thm 17.7.2).**
∂/∂t h_e(X+√t Z) = (1/2) J(X+√t Z).
Entropy increases under Gaussian smoothing at a rate given by Fisher information.

**Entropy power inequality (Section 17.8).** For independent real X,Y with densities,
2^{2h(X+Y)} ≥ 2^{2h(X)} + 2^{2h(Y)}
(nats version: e^{2h(X+Y)/ln 2} accordingly). Equality iff X,Y Gaussian. Vector form: N(X+Y)≥N(X)+N(Y) with N(X)=(1/(2πe)) exp(2h(X)/n) in n dimensions.

**Brunn–Minkowski.** Vol(A⊕B)^{1/n} ≥ Vol(A)^{1/n}+Vol(B)^{1/n}. Costa, Dembo, Cover, Thomas: EPI and BM are analogs; uniform-on-set entropy power ↔ volume.

**Hadamard inequality.** For K ≽ 0, |K| ≤ ∏_i K_{ii}, equality iff K diagonal. Information proof: h(X)≤∑ h(X_i) for Gaussian X~N(0,K).

**Minkowski inequality for determinants.** |K1+K2|^{1/n} ≥ |K1|^{1/n}+|K2|^{1/n} for K_i ≽ 0. Information proof: EPI for Gaussians.

**Ky Fan / other ratio inequalities (Section 17.10).** Ratios of principal-minor determinants are monotone — again Gaussian entropy rates of subsets.

**Pinsker / L1 bound.** D(p||q) ≥ (1/(2 ln 2)) ||p−q||_1^2  (bits). Types: empirical D concentrates.

## Key Equations
- 0 ≤ H ≤ log|X|,  I≥0,  H(X|Y)≤H(X)
- Fano: P_e ≥ (H(X|Y)−1)/log|X|
- de Bruijn: ∂_t h(X+√t Z) = J/2
- EPI: 2^{2h(X+Y)} ≥ 2^{2h(X)}+2^{2h(Y)}
- N(X)=(1/(2πe)) 2^{2h(X)}
- |K| ≤ ∏ K_{ii}
- |K1+K2|^{1/n} ≥ |K1|^{1/n}+|K2|^{1/n}
- Pinsker: D ≥ (1/(2 ln 2)) ||p−q||_1^2

## Worked Example
X,Y i.i.d. N(0,σ^2): h=½ log(2πe σ^2), 2^{2h}=2πe σ^2, sum 2·2πe σ^2, and X+Y~N(0,2σ^2) has 2^{2h}=2πe·2σ^2 — equality in EPI.

X uniform on an interval of length a, Y independent uniform on length b: X+Y has trapezoid density on length a+b; EPI is strict unless degeneracy. Brunn–Minkowski on the intervals: lengths add, equality.

Hadamard: covariance with 1’s on diagonal and ρ off-diagonal, |K|=(1−ρ)^{n−1}(1+(n−1)ρ) ≤ 1, with slack unless ρ=0.

## Anti-patterns
- **Using EPI for dependent X,Y**: independence is required (or use conditional EPI carefully).
- **Mixing bits and nats in 2^{2h}**: h must be in bits for 2^{2h}, nats for e^{2h}.
- **Applying H(X)≤log|X| to differential entropy**.
- **Forgetting equality conditions**: they diagnose when a Gaussian assumption is w.l.o.g.
- **Using Fano with infinite alphabets** without replacing log|X| by a tail bound.

## Key Takeaways
1. Almost every information inequality is Jensen + Gaussian (or uniform) extremal.
2. EPI is the dynamical cousin of Brunn–Minkowski; Fisher information is the derivative of entropy.
3. Matrix inequalities are Gaussian entropy inequalities in disguise.
4. Han’s subset inequalities are the combinatorial chain-rule refinement used in network converses.

## Connects To
- **Ch 2, 8**: sources of the catalog.
- **Ch 9–10**: EPI alternative proofs of Gaussian C and R(D).
- **Ch 11**: Pinsker, types.
- **Ch 12**: maxent = equality cases.
- **Ch 15**: Han inequalities in network converses.
