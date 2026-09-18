# Chapter 6: Binary BCH Codes

## Core Idea
Binary BCH codes are cyclic codes whose generator has 2t consecutive powers of a primitive element as roots. That designed consecutive-root property forces d_min ≥ 2t+1 (the BCH bound) and yields an algebraic decoder: syndromes → error-locator polynomial → Chien search → bit flips.

## Key Concepts
- **Primitive binary BCH**: for m ≥ 3 and t < 2^{m−1}, there exists a code with n = 2^m − 1, n−k ≤ mt, d_min ≥ 2t+1. t-error-correcting by design.
- **Generator**: let α primitive in GF(2^m). g(X) = LCM{φ1(X), φ3(X), …, φ_{2t−1}(X)} where φ_i is the minimal polynomial of α^i. Even powers share minimal polynomials with earlier odd powers, so only odd conjugates are needed.
- **Designed distance δ = 2t+1**: the number of guaranteed consecutive roots plus one. True d_min may be larger.
- **Narrow-sense**: roots start at α^1 (not α^0). Primitive: n = 2^m − 1 (α is primitive, not just an nth root).
- **t=1 BCH = Hamming**: g(X) = φ1(X), a primitive polynomial of degree m.
- **Error-locator polynomial σ(X) = ∏_{ℓ=1}^ν (1 − Z_ℓ X)** where Z_ℓ = α^{j_ℓ} are error-location numbers.
- **Peterson–Gorenstein–Zierler (PGZ)**: invert a t × t syndrome matrix to get σ(X); feasible for small t.
- **Berlekamp (binary iterative) algorithm**: builds σ(X) in t iterations without matrix inversion; Massey’s LFSR-synthesis view is equivalent (BMA).
- **Chien search**: test whether σ(α^{−j}) = 0 to see if position j is in error.
- **Erasure**: known-location uncertainty; a BCH code corrects ν errors and e erasures if 2ν + e ≤ d_min − 1.

## Frameworks and Methods
- **Construction recipe**:
  1. Choose m (length n=2^m−1) and t.
  2. Build GF(2^m) from a primitive polynomial (Ch 2 tables).
  3. Compute minimal polynomials of α, α^3, …, α^{2t−1}.
  4. g = LCM of those; k = n − deg(g).
  5. Encode as any cyclic code (Ch 5 LFSR).
- **Decode pipeline (hard decision)**:
  1. Compute syndromes S_i = r(α^i) for i=1…2t (binary: S_{2i} = S_i^2, so only odd S_i need work).
  2. If all S_i=0, no error.
  3. Run Berlekamp (or PGZ) to get σ(X) of degree ν ≤ t.
  4. Chien-search the n locations; if ν roots found, flip those bits. Else fail.
- **Binary simplification**: the discrepancy in Berlekamp’s iteration uses only odd syndromes; inversion-free variants exist for hardware.
- **Implementation**: GF(2^m) adders = m-bit XOR; multipliers = log/antilog ROM or Massey–Omura/composite-field circuits. Chien search is n parallel or serial evaluations — the throughput bottleneck for long n.

## Key Results
- BCH bound: if g has δ−1 consecutive roots α^b, α^{b+1}, …, α^{b+δ−2}, then d_min ≥ δ.
- For small t, n−k = mt exactly; for large t, n−k < mt (some φ_i coincide more).
- Table 6.1 (book): all primitive binary BCH with m ≤ 10, e.g.
  - (7,4,3) t=1 Hamming
  - (15,7,5) t=2; (15,5,7) t=3
  - (31,21,5), (31,16,7), (31,11,11)
  - (63,45,7), (127,113,5), (255,239,5), …
- Worked (15,7) t=2: φ1=1+X+X^4, φ3=1+X+X^2+X^3+X^4, g=1+X^4+X^6+X^7+X^8, wt(g)=5 so d_min=5 exactly.
- Weight distribution of primitive BCH is known in many small cases; used for undetected-error analysis (CRC-like detection with BCH).
- Peterson’s original decoder is O(t^3) linear algebra; Berlekamp is O(t^2).

## Algorithms and Techniques
**Binary Berlekamp iteration (find σ(X)) — conceptual steps**:
1. Initialize σ^{(0)}(X)=1, auxiliary τ(X)=1, k=0.
2. For μ = 0, 1, …, t−1:
   - Compute discrepancy Δ_μ from current σ and syndromes S_1…S_{2μ+1}.
   - If Δ_μ=0, set τ(X) ← X τ(X).
   - If Δ_μ ≠ 0, update σ ← σ + Δ_μ X τ; then if 2k ≤ μ, swap roles and set k ← μ+1−k, τ ← Δ_μ^{−1} σ_old; else τ ← X τ.
3. Output σ of degree ν. If deg σ ≠ number of Chien roots, decoding failure.

**Chien search**:
For j=0…n−1, evaluate σ(α^{−j}). A zero ⇒ error at location j. In hardware, a register holds (σ_i α^{i j}) and multiplies by α^i each cycle.

**Errors-and-erasures**:
1. Form erasure-locator Γ(X) from known erasure positions.
2. Modify syndromes (Forney) to an error-only key equation of reduced degree.
3. Solve for remaining errors; Forney formula degenerates to bit flips in binary.

## Anti-patterns
- **Trusting designed distance as exact**: some BCH codes have d_min > 2t+1 (e.g. some length-31). Decoder still only guaranteed for t.
- **Running Chien and accepting ν mismatches**: if σ has degree 3 but only 1 root in the field, the error is uncorrectable — fail, do not flip the one root.
- **Ignoring binary syndrome squaring**: computing even S_{2i} independently wastes GF multiplies.
- **PGZ for large t**: t×t inversion at every word is slower and less stable in finite-field arithmetic than BMA.
- **Using primitive BCH when n is not 2^m−1**: need nonprimitive BCH (gcd(n, 2^m−1)=n) or shortening; blindly using α of the wrong order breaks the consecutive-root proof.

## Key Takeaways
1. Consecutive roots ⇒ BCH bound ⇒ designed t.
2. Decoder is syndrome → Berlekamp σ(X) → Chien locations → flip.
3. t=1 BCH is Hamming; t=2,3 of length 15,31,63 are the workhorses of classical algebraic ECC (disk, older wireless, CCSDS).
4. Hardware cost is GF(2^m) arithmetic plus an n-cycle Chien search.
5. Nonbinary BCH and RS (Ch 7) use the same skeleton with a Forney error-value step.

## Connects To
- **Ch 2**: GF(2^m), minimal polynomials, primitive elements.
- **Ch 5**: cyclic encoding / LFSR; BCH is a cyclic subclass.
- **Ch 7**: q-ary BCH, RS as MDS special case, Euclidean and frequency-domain decoders.
- **Ch 17**: some cyclic EG-LDPC / BCH-like parity-check structures.
