# Chapter 7: Nonbinary BCH Codes, Reed–Solomon Codes, and Decoding Algorithms

## Core Idea
Reed–Solomon (RS) codes are the MDS nonbinary BCH codes over GF(q): length n = q−1 (primitive), dimension k, distance d = n−k+1. They correct t = ⌊(d−1)/2⌋ symbol errors — hence long bursts in bit channels — and decode by Berlekamp–Massey or Euclid plus Forney’s error-value formula.

Note: this chapter’s body is missing from the OCR merge; content follows the book’s ToC (7.1–7.7) and standard Lin & Costello 2nd ed development.

## Key Concepts
- **q-ary linear block code**: subspace of GF(q)^n. Hamming distance counts differing *symbols*, not bits.
- **Primitive BCH over GF(q)**: n = q^m − 1, g(X) has 2t consecutive powers of a primitive element of GF(q^m) as roots; designed distance 2t+1. Parity symbols ≤ 2t m (not 2t) when m>1.
- **Reed–Solomon**: BCH with m=1, alphabet = GF(q), n = q−1 (or n ≤ q with evaluation/extended RS). Then n−k = 2t = d−1, so d = n−k+1 (MDS).
- **MDS property**: meets Singleton bound d ≤ n−k+1 with equality. Any k symbols determine the codeword; any n−k erasures are correctable.
- **RS as polynomial evaluation**: codeword = (f(α^0), f(α^1), …, f(α^{n−1})) for deg f < k. Zeros of g are α, α^2, …, α^{n−k}.
- **Berlekamp algorithm (q-ary)**: same key equation as binary, but discrepancies do not simplify by squaring; error *values* are a second unknown.
- **Euclidean algorithm decoder**: compute gcd-like remainder sequence of X^{2t} and the syndrome polynomial S(X) until deg r < t; back-substitute to σ(X) and ω(X) (error-evaluator).
- **Frequency-domain (transform) decoding**: syndromes are a window of the DFT of the error; invert after interpolating the missing spectrum (Blahut).
- **Errors and erasures**: 2ν + e ≤ n−k. Erasures are free in the designed-distance budget.

## Frameworks and Methods
- **When to use RS vs binary BCH**:
  - RS: burst errors, storage (CD/DVD/QR), packet erasures, concatenated outer codes, deep space (CCSDS RS(255,223)).
  - Binary BCH: random bit errors, shorter alphabets, simpler bit-level hardware.
- **Bit-burst view**: an RS symbol in GF(2^m) is m bits. A burst of m t consecutive bits is at most t+1 symbol errors (often t), so one RS word swallows a long bit burst.
- **Decode skeleton (time domain)**:
  1. S_i = r(α^i), i=1…2t.
  2. Solve key equation σ(X) S(X) ≡ ω(X) (mod X^{2t}) with deg σ ≤ t, deg ω < deg σ.
  3. Chien: roots of σ = error locations X_ℓ.
  4. Forney: error value Y_ℓ = ω(X_ℓ^{-1}) / σ'(X_ℓ^{-1}) (char ≠ 2 formula; binary Forney is just “1”).
  5. Subtract Y_ℓ at those symbols.
- **Extended / shortened RS**: add 1 or 2 evaluation points (n=q or q+1) keeping MDS; shorten by freezing information symbols (QR codes, CCSDS).

## Key Results
- Singleton: d ≤ n−k+1. RS achieves equality ⇒ MDS.
- Primitive RS: n=q−1, k arbitrary, d=n−k+1 over GF(q). Common: GF(256), RS(255,k).
- RS(255,223): t=16 bytes; NASA/CCSDS standard concatenated with a convolutional inner code.
- Error-erasure capacity: ν errors + e erasures correctable if 2ν+e ≤ n−k.
- Dual of RS is RS (up to equivalent evaluation points). Weight distribution is known (MDS formula):
  A_d = C(n,d) (q−1) Σ_{j=0}^{d−d_min} (−1)^j C(d−1,j) q^{d−d_min−j} with d_min=n−k+1.
- Euclid and BM are mathematically equivalent; Euclid is easier to prove, BM is typically cheaper in software for moderate t.

## Algorithms and Techniques
**Euclidean algorithm (Sugiyama et al.)**:
1. S(X) = S_1 + S_2 X + … + S_{2t} X^{2t−1}.
2. Run extended Euclid on a(X)=X^{2t} and b(X)=S(X).
3. Stop when remainder r_i has deg < t. Then σ ∝ t_i, ω ∝ r_i (normalize σ(0)=1).
4. Proceed with Chien + Forney.

**Forney error values**:
Y_ℓ = − ω(X_ℓ^{-1}) / σ'(X_ℓ^{-1}) at each error locator X_ℓ.
In characteristic 2 the minus vanishes. σ' is the formal derivative (odd-index coefficients).

**Erasure handling**:
1. Γ(X) = ∏ (1 − Z_j X) over erasure locators.
2. Forney syndromes T(X) = Γ(X) S(X) mod X^{2t}.
3. Solve a shorter key equation for the unknown errors; combine locators σ_total = σ_err Γ.

**Frequency-domain sketch**:
DFT of length n=q−1 over GF(q). A codeword has 2t consecutive spectral zeros. Fill the unknown spectrum using the linear recurrence given by σ, then inverse DFT.

## Anti-patterns
- **Treating RS distance in bits**: d = n−k+1 *symbols*. A 1-bit error in 16 different symbols is 16 symbol errors, not 16 bit errors — RS may fail while a binary code would not.
- **Skipping Forney**: locations without values do not decode q-ary codes.
- **BM without a failure check**: if Chien finds fewer roots than deg σ, or Forney divides by zero, declare failure (important in concatenated systems).
- **Using n not dividing q^m−1** without switching to evaluation-on-arbitrary-points (generalized RS).
- **Deep Euclid remainder**: stopping too late/early yields the wrong (σ,ω) pair.

## Key Takeaways
1. RS = MDS = evaluation codes = nonbinary BCH with m=1.
2. Decoder: syndromes → BM or Euclid (σ,ω) → Chien locations → Forney values.
3. Burst-friendly: m-bit symbols turn bit bursts into few symbol errors.
4. Erasures are half-price (each erasure costs one parity, each error two).
5. Workhorse parameters: RS(255,223) t=16; RS(255,239) t=8; shortened RS in QR/barcodes.

## Connects To
- **Ch 6**: binary BCH is the m>1, q=2 specialization (no Forney values).
- **Ch 5**: cyclic encoding still applies.
- **Ch 15**: RS as outer code in concatenated NASA/CCSDS schemes.
- **Ch 20**: burst correction via RS vs Fire codes vs interleaving.
- **Ch 17**: RS-based LDPC constructions (shortened RS with two information symbols).
