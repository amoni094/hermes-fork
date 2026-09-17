# Chapter 8: Dependent Random Variables

## Core Idea
When variables are dependent, joint entropy is less than the sum of marginal entropies; the difference is mutual information. This is the language of both dependent sources (compression) and noisy channels (communication): a channel is useful only because input X and output Y are dependent.

## Frameworks Introduced
- **Entropy toolkit for joints**
  - H(X,Y) = −sum P(x,y) log P(x,y)
  - H(X|Y) = H(X,Y)−H(Y)  leftover uncertainty
  - I(X;Y) = H(X)−H(X|Y) = H(X)+H(Y)−H(X,Y)
- **Chain rules**: h(x,y)=h(x)+h(y|x); H(X1..XN)=sum_k H(Xk | X_<k)
- **Independence tests**: H(X,Y)=H(X)+H(Y) iff P(x,y)=P(x)P(y) iff I(X;Y)=0

## Key Concepts
- **Marginal entropy**: H(X), contrasted with conditionals.
- **Conditional entropy H(X|y=bk)**: entropy of one slice; H(X|Y) averages slices.
- **Symmetry of I(X;Y)**: I(X;Y)=I(Y;X) even if the channel is not symmetric.
- **Data processing inequality** (used throughout later chapters): processing Y cannot increase information about X.
- **Renaming in v7.2**: chapter title changed from “Correlated” to “Dependent” — uncorrelated ≠ independent.

## Key Equations
- H(X,Y) = H(X)+H(Y|X) = H(Y)+H(X|Y)
- I(X;Y) = DKL(P(x,y) || P(x)P(y))
- 0 ≤ H(X|Y) ≤ H(X) ≤ H(X,Y) ≤ H(X)+H(Y)
- 0 ≤ I(X;Y) ≤ min(H(X),H(Y))
- H(X1..XN) ≤ sum H(Xi) with equality iff independent

## Algorithms and Techniques
**Compute the information diagram for a joint P(x,y)**
1. Fill the 2×2 (or I×J) table of P(x,y).
2. Marginals by summing.
3. H(X), H(Y), H(X,Y) from definition.
4. I, H(X|Y), H(Y|X) by subtraction. Check non-negativity as a bug check.

## Mental Models
- Venn diagram: two circles H(X), H(Y); overlap I(X;Y); union H(X,Y); crescents are conditionals. (Mnemonic only — I is not a set.)
- Use I(X;Y) as “how useful is Y as a measurement of X”.
- For compression of dependent sources, the target is H(X1..XN)/N, not H(X1).

## Worked Example
Binary X with P(x=1)=1/2, BSC-like Y: Y=X with prob 1−f, flipped with f.
- H(X)=1, H(Y|X)=H2(f), so I(X;Y)=1−H2(f).
- This quantity will be the capacity of the BSC once we maximize over P(x) (already optimal at 1/2 by symmetry).
- If f=1/2, I=0: received bits are independent of sent bits — MacKay’s warning in Ch 9 that “1000 bits/s minus 500 errors ≠ 500 bits of information”.

## Anti-patterns
- **Subtracting expected errors from bitrate** to estimate information rate.
- **Saying “correlated” when you mean dependent** (title change exists for a reason).
- **Negative I from numerical error**: you computed with mixed log bases or unnormalized P.
- **Assuming H(X|Y=y) ≤ H(X) always**: it can increase for a particular y; only the *average* H(X|Y) ≤ H(X).

## Key Takeaways
1. Dependence is measured by I(X;Y) ≥ 0.
2. Chain rule turns joint modelling into a sequence of conditionals (and thus into arithmetic coding).
3. A noisy channel is a specified family of P(y|x); information conveyed is I(X;Y).
4. Always bound-check: 0 ≤ H(X|Y) ≤ H(X) ≤ H(X,Y) ≤ H(X)+H(Y).

## Connects To
- **Ch 2**: definitions first appeared; this chapter drills dependence.
- **Ch 6**: sequential conditionals for compression.
- **Ch 9–10**: I(X;Y) maximized is capacity.
- **Ch 24–26**: computing conditionals/marginals in structured joints.
