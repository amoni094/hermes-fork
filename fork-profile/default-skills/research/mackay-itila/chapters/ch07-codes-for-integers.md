# Chapter 7: Codes for Integers

## Core Idea
When the alphabet is the positive integers with a decaying distribution (unknown or heavy-tailed), you need a prefix code over ℕ, not a Huffman tree on a finite set. Unary, gamma, and related self-delimiting codes trade a few extra bits for the ability to encode arbitrarily large integers.

## Frameworks Introduced
- **Self-delimiting integer codes**: represent n ∈ {1,2,…} so concatenations remain uniquely decodeable.
- **Unary code**: n ones followed by a zero (or vice versa). Length = n+1. Optimal for P(n) ∝ 2^{−n}.
- **Elias gamma code**: unary-encode ⌊log2 n⌋+1, then the binary payload of n without its leading 1. Length ≈ 2 log2 n.
- **Elias delta / omega**: iterate the length encoding so length is log n + log log n + … for very large n.

## Key Concepts
- **Kraft on ℕ**: sum_n 2^{−l(n)} ≤ 1 still governs existence.
- **Implied prior**: each integer code corresponds to a prior P(n) ∝ 2^{−l(n)}. Using gamma is assuming a roughly 1/n^2 prior.
- **Universal codes for integers**: codes whose expected length is within a constant factor of H for large classes of monotone distributions.
- **Use case**: run-lengths, LZ pointers, document IDs, codeword lengths themselves.

## Key Equations
- Unary: l_U(n) = n
- Gamma: lγ(n) = 2⌊log2 n⌋ + 1
- Delta: lδ(n) = ⌊log2 n⌋ + 2⌊log2(⌊log2 n⌋+1)⌋ + 1
- Implied Pγ(n) ≈ 1/(2 n^2)
- For P(n) ∝ 1/n^α, choose a code whose length ~ α log n

## Algorithms and Techniques
**Encode n with Elias gamma**
1. Let b = ⌊log2 n⌋+1 (bit-length of n).
2. Write b−1 zeros, then a 1 (unary for b).
3. Write the last b−1 bits of n (drop the leading 1).

**Decode gamma**: count leading zeros k; read the next k+1 bits as a binary integer.

## Mental Models
- Think “which prior over integers am I committing to?” whenever you pick unary vs gamma vs delta.
- Use unary for very small n (geometric with mean ~1–2); gamma for n spanning several octaves; delta when n can be huge.
- Integer codes are the missing piece when Huffman’s finite alphabet assumption fails.

## Worked Example
n=13 = 1101₂, bit-length b=4.
- Gamma: unary 4 = 0001, then payload 101 → 0001101. Length 7 = 2·3+1.
- Unary would be 13 ones and a stop — much worse.
- Implied: P(13) under gamma ~ 2^{−7} ≈ 1/128, vs 1/(2·13^2)≈1/338 (order-of-magnitude match).

## Anti-patterns
- **Fixed 32-bit integers for sparse counts** (IDs, run-lengths): wastes bits and is not prefix-free in a stream.
- **Huffman on “integers up to 10^9”**: tree cannot be built; use a parametric code.
- **Using unary for file sizes**.

## Key Takeaways
1. Unbounded alphabets need self-delimiting integer codes.
2. Length ~ c log n is the right scaling for power-law integers.
3. The code *is* a prior; mismatch costs DKL.
4. Gamma is the default practical choice; unary only for tiny geometric n.

## Connects To
- **Ch 5**: Kraft, prefix codes.
- **Ch 6**: LZ pointers are integers; arithmetic coding can replace integer codes if you have P(n).
- **Ch 12**: hashing / retrieval sometimes stores integer pointers.
