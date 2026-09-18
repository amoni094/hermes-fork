# Chapter 8: Majority-Logic Decodable and Finite Geometry Codes

## Core Idea
If each code bit is checked by J orthogonal parity-check sums, a majority vote on those sums estimates that bit (and can be iterated). Finite Euclidean and projective geometries over GF(2^s) manufacture large families of cyclic codes with this orthogonal structure — the same geometries later yield EG/PG-LDPC codes (Ch 17).

Note: this chapter is missing from the OCR merge; content follows ToC 8.1–8.9 and Lin & Costello 2nd ed.

## Key Concepts
- **Orthogonal parity checks on bit i**: a set of rows of H, each containing position i, that pairwise share no other 1. Then each other bit appears in at most one check.
- **One-step majority-logic (MLG) decoding**: compute J check sums on bit i; if more than J/2 of them are 1, flip bit i. Corrects t_ML = ⌊J/2⌋ errors. Hence d_min ≥ J+1.
- **One-step majority-logic decodable codes**: J = d_min − 1 orthogonal checks exist for every position (e.g. RM, difference-set, some cyclic).
- **Multiple-step (L-step) MLG**: votes estimate *checks* at the next geometry incidence level, then the bits. RM(r,m) is (r+1)-step majority-logic decodable.
- **Euclidean geometry EG(m, 2^s)**: points = m-tuples over GF(2^s); μ-flats are cosets of μ-dimensional subspaces. Incidence vectors of flats → rows of H.
- **EG codes**: cyclic (generally) codes whose dual contains incidence vectors of a chosen flat dimension. Type-0 / type-1, and *twofold* EG codes.
- **Projective geometry PG(m, 2^s)**: points are 1-dimensional subspaces of GF(2^s)^{m+1}. PG codes analogous to EG, often slightly different rates/distances.
- **Difference-set codes**: cyclic codes from projective planes (Singer difference sets); one-step MLG; e.g. (21,11), (73,45), (273,191).

## Frameworks and Methods
- **When MLG is the right decoder**: moderate d_min, very simple hardware (XOR trees + majority gates), hard decisions, no GF(2^m) inversion. Used historically in deep space (RM) and as the ancestor of bit-flipping LDPC decoders.
- **One-step algorithm (every bit, possibly in parallel)**:
  1. For each position i, form the J orthogonal sums A_{i,1} … A_{i,J} from the received word.
  2. If Σ A_{i,j} > J/2, set e_i=1 else 0.
  3. Output r + e. (Can iterate: recompute checks after flips — Gallager bit-flip is the LDPC analogue.)
- **Geometry construction**:
  1. Pick EG(m,q) or PG(m,q), q=2^s.
  2. Take as rows of H the incidence vectors of all μ-flats of a fixed dimension (or a cyclic orbit of one flat).
  3. The null space is the EG/PG code. Length = number of points (q^m for EG, (q^{m+1}−1)/(q−1) for PG).
  4. Orthogonal checks on a point = flats through that point not sharing another point — counted by geometry.

## Key Results
- One-step MLG corrects ⌊J/2⌋ errors; d_min ≥ J+1. If the geometry gives J = q μ-flat count, plug in q=2^s.
- Reed–Muller RM(r,m) is majority-logic decodable in r+1 steps with J = 2^{m−r}−1 at the first step; d_min = 2^{m−r} matches.
- Difference-set cyclic codes from PG(2,2^s): n = 2^{2s} + 2^s + 1, n−k = 3^s + 1, J = 2^s + 1, d_min ≥ 2^s + 2.
- EG Type-1 cyclic codes: n = 2^{ms} − 1, often high rate with J = 2^s, good for MLG but not capacity-approaching.
- Twofold EG: extra orthogonality, used as structured LDPC later (Ch 17).
- MLG is *suboptimal* vs MLD; the loss vs soft MLD is large on AWGN, but complexity is O(n J).

## Algorithms and Techniques
**Worked one-step picture** (simplex / dual Hamming, J=n):
Each pair of positions is covered by a unique weight-3 dual codeword. Majority of n checks recovers every bit even at high noise — but rate is tiny (simplex k=m, n=2^m−1).

**RM(1,m) first-order decode** (Green machine / Hadamard):
Equivalent to correlating against all 2^{m+1} codewords, or to a fast Walsh–Hadamard transform. This is MLG and also MLD for RM(1,m).

**L-step RM decode**:
1. For each r-flat, majority-vote the (r−1)-flat checks to estimate the r-flat parity.
2. Recurse down to 0-flats (points) = code bits.
3. Complexity linear in n times a small geometry factor.

**Threshold variants**: replace hard majority by a weighted threshold when reliabilities are available (Ch 10 weighted MLG; APP bit-flip).

## Anti-patterns
- **Using MLG on codes without orthogonality**: overlapping checks bias the vote; t_ML collapses.
- **Stopping at one step for high-order RM**: you need r+1 steps; one-step J is too small.
- **Expecting Shannon-limit performance**: MLG is a 1960s hard decoder. On AWGN, use RM trellis/Reed decoding or polar-like successive cancellation, not majority.
- **Confusing EG length 2^{ms} vs 2^{ms}−1**: puncturing the all-zero-location point yields the cyclic version of length 2^{ms}−1.
- **Ignoring 4-cycles when recycling geometry H as LDPC**: Ch 8’s λ≤1 column condition is exactly “girth ≥6,” which is why these H matrices reappear in Ch 17.

## Key Takeaways
1. Orthogonal checks ⇒ majority vote ⇒ t_ML = ⌊J/2⌋, d_min ≥ J+1.
2. Finite geometries are a factory for cyclic MLG codes and, later, structured LDPC.
3. RM codes are the Boolean-function special case; first-order RM is Hadamard/ML.
4. Hardware: XOR + majority, no inversions — cheap, not near-capacity.
5. Bit-flipping LDPC (Ch 17) is iterative weighted MLG on a sparse H.

## Connects To
- **Ch 4**: RM parameters and squaring construction.
- **Ch 5**: many EG/PG codes are cyclic.
- **Ch 10**: weighted majority-logic and iterative reliability-based MLG.
- **Ch 13**: convolutional majority-logic (self-orthogonal codes).
- **Ch 17**: EG-LDPC and PG-LDPC reuse these incidence matrices.
