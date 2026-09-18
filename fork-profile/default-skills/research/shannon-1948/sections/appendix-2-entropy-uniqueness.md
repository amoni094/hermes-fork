# Appendix 2: Uniqueness of the Entropy Function

## Core Idea
The three axioms of Sec 6 force H(p1,…,pn) = −K ∑ pi log pi.

## Key Concepts
- **A(n)**: H when all n probabilities equal 1/n. Axiom 2: A(n) increasing in n.
- **Grouping axiom**: a choice broken into successive choices has H equal to the weighted sum of the stepwise H’s.

## Key Results
**Theorem 2.** The only H satisfying the three assumptions is H = −K ∑ pi log pi with K > 0.

**Sketch.** From the grouping axiom, A(s^m) = m A(s). Comparing s^m and t^n with s^m ≈ t^n gives A(t)/A(s) = log t / log s, so A(n) = K log n. For rational pi = ni/∑ nj, grouping reduces H to A(∑ ni) minus the weighted A(ni), which is −K ∑ pi log pi. Continuity (axiom 1) extends to all pi.

Shannon’s caveat in Sec 6: the uniqueness theorem is “in no way necessary for the present theory… The real justification of these definitions, however, will reside in their implications.”

## Key Equations
- A(s^m) = m A(s)
- A(n) = K log n
- H = −K ∑ pi log pi

## Significance
This is the axiomatic pedigree of entropy. Later work (Khinchin, Faddeev, etc.) varies the axioms; Shannon already treats coding theorems, not axioms, as the real justification.

## Connects To
- Sec 6: statement and properties 1–6.
- Sec 9, 13: operational meaning via coding.
