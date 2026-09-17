# Chapter 3: Linear Block Codes

## Core Idea
A binary linear (n,k) code is a k-dimensional subspace of GF(2)^n. Linearity collapses encoding to a matrix multiply v = u G, detection to a syndrome s = r H^T, and distance to the minimum Hamming weight of nonzero codewords.

## Key Concepts
- **Linear (n,k) code**: 2^k codewords form a k-dimensional subspace; equivalently, the XOR of any two codewords is a codeword.
- **Generator matrix G**: k × n, rank k; rows are a basis. v = u G.
- **Systematic code**: G = [P | I_k] (or [I_k | P]); codeword = (parity bits | message bits). Parity equations: v_j = Σ u_i p_{i j}.
- **Parity-check matrix H**: (n−k) × n, rank n−k, G H^T = 0. v is a codeword ⇔ v H^T = 0. Rows of H generate the dual code C^⊥, an (n, n−k) code.
- **Hamming weight w(v)**: number of nonzero components. Hamming distance d(u,v) = w(u−v).
- **Minimum distance d_min**: min weight of nonzero codewords (linearity). Equals the smallest number of linearly dependent columns of H.
- **Error-correcting capability t = ⌊(d_min−1)/2⌋**; detecting capability d_min−1.
- **Syndrome s = r H^T = e H^T**: depends only on the error pattern e, not on the codeword.
- **Standard array**: partition of GF(2)^n into 2^{n−k} cosets of C; coset leaders = correctable error patterns.
- **Perfect code**: spheres of radius t about codewords pack GF(2)^n with no leftover vectors. Hamming codes and the (23,12) Golay code are the nontrivial binary perfect codes.
- **Undetected-error probability P_u(E)** on a BSC: probability that a nonzero codeword is received, so the syndrome is zero but the word is wrong.

## Frameworks and Methods
- **Encode**: store only k rows of G (not 2^k words). For systematic G, copy k message bits and compute n−k parities by XOR.
- **Distance via H**: d_min is the largest d such that every d−1 columns of H are independent. Corollary: if no 1 or 2 columns of H are zero or equal, d_min ≥ 3.
- **Syndrome decoding**:
  1. Compute s = r H^T.
  2. If s = 0, accept r as a codeword.
  3. Else look up the coset leader e(s) and output r + e(s).
- **Standard-array construction**: first row = codewords; each later row = a minimum-weight unused vector (coset leader) plus the code. Completely decoding ⇔ every vector is in some sphere; incomplete decoding leaves some syndromes as “detect only.”
- **Bounded-distance decoding**: correct all patterns of weight ≤ t; detect (or fail) heavier patterns. Preferable to complete decoding when miscorrection is costly.

## Key Results
- Singleton bound (preview): d_min ≤ n − k + 1. Codes meeting it are MDS (Ch 7 RS).
- Hamming (sphere-packing) bound: 2^k Σ_{i=0}^t C(n,i) ≤ 2^n.
- For a linear code on BSC(p):
  - P_u(E) = Σ_{i=1}^n A_i p^i (1−p)^{n−i} where A_i is the number of weight-i codewords.
  - Dual form (MacWilliams): P_u(E) = 2^{−(n−k)} B(1−2p) − (1−p)^n, with B the dual weight enumerator — often cheaper (Hamming, Ch 4).
- Many linear codes satisfy P_u(E) ≤ 2^{−(n−k)} for p ≤ 1/2, i.e. they are good CRC-style detectors.
- Single-parity-check (n, n−1): d_min = 2, detects odd-weight errors. Repetition (n,1): d_min = n, t = ⌊(n−1)/2⌋. Self-dual: C = C^⊥, so n even and k = n/2.

## Algorithms and Techniques
**Systematic encoding (Example 3.2, (7,4))**:
G rows produce parities
- v6=u3, v5=u2, v4=u1, v3=u0 (message)
- v2 = u1+u3, v1 = u0+u1+u2, v0 = u0+u2+u3.
Message (1011) → codeword (1001011).

**Syndrome table lookup (Hamming-scale)**: 2^{n−k} syndromes. Feasible only for small redundancy (n−k ≲ 16 in RAM; smaller in hardware).

**Error detection only (CRC use of linear codes)**: compute syndrome; if nonzero, flag error / request retransmission (Ch 22). Do not attempt correction unless the code is designed for it.

## Anti-patterns
- **Dictionary encoding of nonlinear or unstructured codes**: 2^k × n storage; linearity is what makes large k practical.
- **Using complete (standard-array) decoding on a weak code**: high-weight coset leaders cause miscorrection; often worse than detect-and-fail.
- **Confusing d_min with t**: correcting t and simultaneously detecting extra errors needs d_min ≥ 2t + d_detect + 1, not just 2t+1.
- **Assuming all weight-t errors are correctable**: only if the code’s packing / standard array includes them (perfect or quasi-perfect).
- **Forgetting the dual**: undetected-error analysis is often easier from C^⊥ than from C.

## Key Takeaways
1. Linear codes = subspaces; encode with G, check with H, distance = min weight.
2. Syndrome converts channel output into an error-pattern index.
3. t = ⌊(d_min−1)/2⌋ is the guaranteed correction radius, not the typical decoder’s operating point.
4. Detection (CRC) and correction are different uses of the same H.
5. Encoding complexity is O(k(n−k)); optimum decoding is not — later chapters supply algebraic and iterative substitutes for MLD.

## Connects To
- **Ch 1**: block-code model and MLD vs algebraic decoding.
- **Ch 4**: Hamming, Reed–Muller, Golay, product, interleaving as concrete linear codes.
- **Ch 5**: cyclic structure → polynomial G and shift-register encoders.
- **Ch 9–10, 14**: trellis and reliability-based *soft* decoding of the same linear codes.
