# Chapter 4: Important Linear Block Codes

## Core Idea
A handful of explicit linear-code families — Hamming, Hsiao SEC-DED, Reed–Muller, Golay, product, and interleaved — cover most short-block engineering needs: memory protection, simple random-error correction, and turning random-error codes into burst-error codes.

## Key Concepts
- **Hamming code**: n = 2^m − 1, k = 2^m − 1 − m, d_min = 3, t = 1. H’s columns are all nonzero m-tuples. Perfect: every syndrome is either 0 or a unique single-error pattern.
- **Shortened Hamming / d=4**: delete columns of H (especially even-weight columns) to get d_min = 4: correct 1, detect 2 (SEC-DED).
- **Hsiao SEC-DED**: odd-weight-column shortened Hamming with minimum, balanced row weights — fast XOR parity and syndrome in computer memories.
- **Reed–Muller RM(r,m)**: length n = 2^m, dimension k = Σ_{i=0}^r C(m,i), d_min = 2^{m−r}. Recursive Plotkin/squaring structure; majority-logic decodable (Ch 8).
- **Extended Hamming**: add an overall parity bit to (2^m−1, 2^m−1−m) → (2^m, 2^m−1−m), d_min = 4. RM(m−2, m) is the extended Hamming code.
- **Golay (24,12)**: extended quadratic-residue / Golay; d_min = 8, t = 3. The (23,12) cyclic Golay (Ch 5) is perfect, d_min = 7.
- **Product code**: 2-D array, row code (n1,k1), column code (n2,k2); parameters (n1 n2, k1 k2), d = d1 d2. Decode rows then columns (iteratively for turbo-product codes).
- **Interleaved code**: write λ codewords as rows, transmit by columns. A burst of length λ t becomes t errors per row codeword.

## Frameworks and Methods
- **Hamming H in systematic form**: H = [I_m | Q] with Q all weight-≥2 columns. G = [Q^T | I_{n−m}].
- **SEC-DED decode with odd-weight H**:
  1. s = 0 → no error.
  2. s ≠ 0, w(s) odd → single error; flip the column of H equal to s.
  3. s ≠ 0, w(s) even → double (or more) error detected, do not correct.
- **Hsiao construction constraints on H_D**: (1) every column odd weight; (2) minimize total number of 1s; (3) equalize 1s per row. Minimizes gate delay of parity/syndrome XOR trees. Typical widths: (72,64), (39,32), (16,11) for ECC DIMMs.
- **RM encoding**: evaluate Boolean polynomials of degree ≤ r on GF(2)^m, or use the squaring (Plotkin) construction:
  RM(r,m) = {(u, u+v) : u ∈ RM(r,m−1), v ∈ RM(r−1,m−1)}.
- **Product-code decode**: decode all rows with the row decoder; then all columns. Can iterate (Chase/Pyndiah turbo product codes — later soft methods).
- **Interleaving depth λ**: choose λ ≥ expected burst length / t of the inner random-error code.

## Key Results
- Hamming d_min = 3 exactly: some three columns of H sum to 0, but no two do.
- Hamming is perfect: 1 + n = 2^{n−k} = 2^m, spheres of radius 1 fill the space. Only other nontrivial binary perfect code: (23,12) Golay.
- Hamming weight enumerator:
  A(z) = (1/(n+1)) [(1+z)^n + n (1−z)^{(n+1)/2} (1+z)^{(n−1)/2}].
  Dual (simplex): B(z) = 1 + (2^m − 1) z^{2^{m−1}}.
- Hamming undetected error on BSC: P_u(E) = 2^{−m} [1 + (2^m−1)(1−2p)^{2^{m−1}}] − (1−p)^{2^m−1} ≤ 2^{−m} for p ≤ 1/2. Good CRC.
- RM(r,m): d_min = 2^{m−r}. RM(1,m) is the simplex/first-order RM (Hadamard), k = m+1, d = 2^{m−1}.
- Product: d_product = d_row · d_col. Can correct bursts of length (d_col−1)·n_row in row-major transmission, plus random errors.
- (24,12) Golay: unique, d=8, corrects 3 errors and detects 4; used with soft decoding in deep-space / historical NASA links.

## Algorithms and Techniques
**Hamming single-error correction**:
1. Compute m-bit syndrome s.
2. If s=0, done.
3. If s equals column j of H, flip received bit j.
4. Otherwise (shortened/SEC-DED), declare uncorrectable.

**Worked Hamming (7,4)**: H columns = all nonzero 3-tuples. Weight enumerator A(z) = 1 + 7z^3 + 7z^4 + z^7 so A3=A4=7, A7=1.

**RM(1,3) = (8,4,4) extended Hamming**: encode 4 bits as evaluation of affine Boolean functions on the 3-cube; decode by majority on Walsh–Hadamard correlations (or Green machine).

**λ-way interleaver**: encoder writes λ successive codewords into a λ × n array by rows, reads by columns. Deinterleaver inverts. A length-b burst hits at most ⌈b/λ⌉ errors per codeword.

## Anti-patterns
- **Using Hamming for double errors without SEC-DED extension**: a 2-error pattern produces a syndrome equal to some *other* column → silent miscorrection.
- **Unbalanced Hsiao-style H**: uneven row weights stretch the XOR-tree critical path in memory ECC.
- **Product codes without iteration on AWGN**: hard row-column decode leaves residual errors; the distance product is optimistic unless you iterate or use soft decisions.
- **Shallow interleaving on long bursts**: if burst > λ t, every row is uncorrectable.
- **Treating Golay as “just another Hamming”**: d=7/8 and perfect packing are special; decoder is a bounded-distance algebraic or trellis decoder, not a 11-bit syndrome table only.

## Key Takeaways
1. Hamming: the canonical t=1 perfect code; extend/shorten for SEC-DED memory ECC (Hsiao).
2. Reed–Muller: recursive, majority-logic-friendly, nested family used in deep space (Mariner RM(1,5)) and as polar-code ancestors.
3. Product + interleaving convert Hamming-distance into burst length.
4. Golay is the exceptional perfect t=3 code; know it exists, use a dedicated decoder.
5. Weight enumerators of Hamming/simplex give exact undetected-error rates for CRC use.

## Connects To
- **Ch 3**: G, H, d_min, syndrome decoding used throughout.
- **Ch 5**: cyclic Hamming and (23,12) Golay; cyclic product codes.
- **Ch 8**: RM and finite-geometry codes decoded by majority logic.
- **Ch 15**: concatenation is the 1-D analogue of product codes.
- **Ch 20**: Fire and other burst codes vs interleaving.
