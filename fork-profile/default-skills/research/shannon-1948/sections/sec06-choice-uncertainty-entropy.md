# Section 6: Choice, Uncertainty and Entropy

## Core Idea
Given probabilities p1,…,pn of possible events, Shannon asks for a measure H(p1,…,pn) of how much “choice” is involved in the selection, or how uncertain we are of the outcome. The unique function satisfying three axioms is H = −K ∑ pi log pi, which he names entropy by analogy with statistical mechanics.

## Key Concepts
- **Three requirements on H:**
  1. H continuous in the pi.
  2. If pi = 1/n, H is monotonic increasing in n (more equally likely events ⇒ more choice).
  3. If a choice is broken into two successive choices, original H is the weighted sum of the individual H values. Fig. 6: H(1/2, 1/3, 1/6) = H(1/2, 1/2) + (1/2) H(2/3, 1/3).
- **Entropy of a set of probabilities**: H = −∑ pi log pi (K absorbed in the unit). “If x is a chance variable we will write H(x) for its entropy; thus x is not an argument of a function but a label for a number.”
- **Boltzmann connection**: the form is that of entropy in statistical mechanics, “the H in Boltzmann’s famous H theorem” (Tolman).
- **Binary entropy**: two possibilities p and q = 1−p: H = −(p log p + q log q), plotted in Fig. 7; max 1 bit at p = 1/2.

## Key Results
**Theorem 2.** The only H satisfying the three assumptions is H = −K ∑_{i=1}^n pi log pi, K > 0. Proof: Appendix 2. Shannon immediately cautions: “This theorem, and the assumptions required for its proof, are in no way necessary for the present theory. It is given chiefly to lend a certain plausibility to some of our later definitions. The real justification of these definitions, however, will reside in their implications.”

**Properties that “further substantiate it as a reasonable measure of choice or information”:**
1. H = 0 iff one pi = 1 and the rest 0. Otherwise H > 0. Certainty ⇒ vanishing entropy.
2. For given n, H is maximum and equal to log n when all pi = 1/n — “intuitively the most uncertain situation.”
3. Joint entropy H(x,y) = −∑_{i,j} p(i,j) log p(i,j). Then H(x,y) ≤ H(x) + H(y) with equality iff x,y independent (p(i,j) = p(i)p(j)).
4. Any change toward equalization of the pi increases H. Averaging p'_i = ∑_j a_{ij} p_j with ∑_i a_{ij} = ∑_j a_{ij} = 1, a_{ij} ≥ 0, increases H except for permutations.
5. Conditional entropy Hx(y) := −∑_{i,j} p(i,j) log p_i(j), with p_i(j) = p(i,j)/∑_j p(i,j). “This quantity measures how uncertain we are of y on the average when we know x.” Chain rule: H(x,y) = H(x) + Hx(y).
6. Therefore H(y) ≥ Hx(y): “The uncertainty of y is never increased by knowledge of x. It will be decreased unless x and y are independent events, in which case it is not changed.”

## Key Equations
- H = −K ∑ pi log pi
- H(x,y) = −∑ p(i,j) log p(i,j)
- Hx(y) = −∑ p(i,j) log p_i(j)
- H(x,y) = H(x) + Hx(y) = H(y) + Hy(x)
- H(x,y) ≤ H(x) + H(y)
- H(y) ≥ Hx(y)

## Significance
This is the definition of information-theoretic entropy. Shannon’s notation Hx(y) (not H(Y|X)) and the label convention H(x) are distinctive. Mutual information is not yet named; it appears in Sec 12 as the rate R = H(x) − Hy(x) = H(x) + H(y) − H(x,y). The axiomatic uniqueness is presented as plausibility, not as the foundation — the coding theorems are.

## Connects To
- Appendix 2: uniqueness proof via A(n) = K log n then rational pi then continuity.
- Sec 7: entropy of a Markoff source as average state entropy.
- Sec 12: R = H(x) − Hy(x); C = Max R.
- Sec 20: continuous analogue H = −∫ p(x) log p(x) dx, with the Jacobian caveat.
