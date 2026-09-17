# Chapter 5: Cyclic Codes

## Core Idea
A linear code is cyclic if every cyclic shift of a codeword is a codeword. That extra symmetry makes the code a principal ideal in GF(2)[X]/(X^n−1), so encoding, syndrome, and detection collapse to polynomial division implemented by linear-feedback shift registers.

## Key Concepts
- **Cyclic code**: C linear and closed under cyclic shifts. Codeword v ↔ polynomial v(X) = v0 + v1 X + … + v_{n−1} X^{n−1}.
- **Generator polynomial g(X)**: the unique monic polynomial of degree n−k that divides every code polynomial. C = { u(X) g(X) : deg u < k }, with multiplication mod X^n−1.
- **Constraint**: g(X) must divide X^n−1. Factor X^n−1 = g(X) h(X); h(X) is the parity-check polynomial (degree k).
- **Generator matrix**: rows are g(X), X g(X), …, X^{k−1} g(X) (possibly put in systematic form by long division).
- **Parity-check matrix**: can be built from h(X) or from roots of g. For cyclic Hamming, columns are successive powers of a primitive element.
- **Systematic cyclic encoding**: divide X^{n−k} u(X) by g(X); remainder p(X) is the parity. Codeword X^{n−k} u(X) + p(X).
- **Syndrome polynomial s(X) = r(X) mod g(X)**. s(X)=0 ⇔ r is a codeword. For errors, s(X) = e(X) mod g(X).
- **Error-trapping decoder**: Meggitt-style: cycle the syndrome until a correctable error pattern (weight ≤ t in n−k consecutive positions) falls into the parity window, then subtract.
- **Cyclic Hamming**: g(X) = primitive polynomial of degree m; n=2^m−1, t=1.
- **Cyclic Golay (23,12)**: g(X) = 1+X+X^5+X^6+X^7+X^9+X^{11} (or the reciprocal); d_min=7, perfect t=3.
- **Shortened cyclic**: delete information bits (used as CRC). Still LFSR-encodable; not strictly cyclic but “shortened cyclic.”
- **Quasi-cyclic**: cyclic shift by ℓ positions (ℓ>1) stays in the code; basis of many modern QC-LDPC constructions (Ch 17).

## Frameworks and Methods
- **Existence**: every divisor g of X^n−1 of degree n−k generates an (n,k) cyclic code. Different irreducible factors give BCH, Hamming, QR, Fire, …
- **CRC (error detection)**: shortened cyclic codes. Transmit remainder of X^{n−k} u(X) / g(X). Receiver recomputes; nonzero remainder ⇒ error. Standard generators: CRC-16, CRC-32, CRC-CCITT.
- **Meggitt decoder** (general cyclic):
  1. Load r into a buffer; compute s(X) = r(X) mod g.
  2. For each of n shifts: if the syndrome matches a correctable pattern with an error in the last position, flip that bit and update syndrome.
  3. Cycle buffer and syndrome together (LFSR).
- **Error-trapping** (Kasami): works well when errors are confined to n−k consecutive positions (bursts, or random errors for high-rate short codes). If after n shifts the syndrome weight is ≤ t, those 1s *are* the error pattern.
- **Encoding hardware**: (n−k)-stage LFSR with taps of g(X). k clocks to shift in data (feedback on), then n−k clocks to dump parity (feedback off).

## Key Results
- Theorem: C cyclic ⇔ C is an ideal in GF(2)[X]/(X^n−1) ⇔ C = (g(X)) with g | X^n−1.
- A cyclic code with generator g of zeros α^{j1}, … corrects based on the consecutive-root BCH bound (Ch 6): if g has 2t consecutive powers of a primitive nth root as zeros, d_min ≥ 2t+1.
- Cyclic Hamming is perfect t=1; syndrome is the field element identifying the error location.
- Shortened cyclic codes keep the detection capability of the parent; P_u(E) ≈ 2^{−(n−k)} for well-chosen g (no factor of small degree, not dividing a sparse polynomial).
- Cyclic product codes: if both row and column codes are cyclic of coprime lengths, the product is cyclic.

## Algorithms and Techniques
**Systematic encode**:
1. Form X^{n−k} u(X) (append n−k zeros).
2. Divide by g(X); remainder p(X), deg < n−k.
3. Transmit v(X) = X^{n−k} u(X) + p(X).

**Worked (7,4) cyclic Hamming**: g(X)=1+X+X^3. Messages in Table 5.1; e.g. u=(1000) → v(X)=g(X)=1+X+X^3 → (1101000). Any cyclic shift is a codeword.

**Syndrome detection**: clock r(X) into the g(X)-LFSR; if the register is not all-zero after n bits, flag error. Cost: n−k XORs of fan-in = weight(g).

**Error-trapping decode (single burst / cyclic Hamming)**:
1. Compute n−k syndrome bits.
2. For i = 0 … n−1: if w(syndrome) ≤ t, add those bits into the corresponding window of the buffer; done.
3. Else cyclically shift received buffer and update syndrome (equivalent to multiplying s by X mod g).
4. If no window traps, fail (detect-only).

## Anti-patterns
- **Picking g that does not divide X^n−1**: the set {u g} is not closed mod X^n−1; not cyclic, and wrap-around bursts misbehave.
- **Error-trapping on random errors in long low-rate codes**: errors are not confined to n−k consecutive positions; trapping fails even when wt(e) ≤ t. Use BCH algebraic decoding (Ch 6) instead.
- **CRC polynomial with obvious factors**: undetected bursts matching a factor of g. Use standard, well-analyzed CRC polynomials.
- **Forgetting shortening breaks cyclicity**: Meggitt cycling needs care; CRCs usually detect-only, which still works.
- **Implementing polynomial multiply as integer multiply**: all arithmetic is mod 2.

## Key Takeaways
1. Cyclic ⇔ polynomial multiple of g(X) | X^n−1.
2. LFSRs give cheap encoders and CRC detectors — the reason cyclic codes dominate detection (Ethernet, ZIP, disks).
3. Syndrome = remainder; correction is “invert the remainder to an error polynomial.”
4. Error-trapping is the simple decoder; algebraic (BCH/RS) or Meggitt is needed when errors are not trapped.
5. Shortened cyclic = CRC; quasi-cyclic = modern LDPC/turbo-product structure.

## Connects To
- **Ch 2**: polynomial rings and GF(2^m) roots of g(X).
- **Ch 6–7**: BCH and RS are cyclic (or shortened/extended cyclic) with designed consecutive roots.
- **Ch 8**: many finite-geometry codes are cyclic.
- **Ch 20**: Fire codes — cyclic burst-error codes built from (X^{2t−1}−1) p(X).
