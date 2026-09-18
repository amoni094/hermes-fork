# Chapter 4: The Source Coding Theorem

## Core Idea
The entropy H(X) is the number of bits needed per symbol to describe i.i.d. samples from X, both as a lossless compression limit (asymptotically) and as the size of the typical set. Shannon information content h(x)=log 1/P(x) is the right measure because it is additive for independent events and matches the geometry of typical sequences.

## Frameworks Introduced
- **Shannon information content** h(x)=log2 1/P(x); **entropy** H(X)=E[h(x)].
  - When to use: any discrete source. Additive for independent variables: h(x,y)=h(x)+h(y).
- **Asymptotic equipartition (typicality)**: for i.i.d. x1..xN, (1/N) log 1/P(x) → H(X) in probability. Almost all probability mass sits on a typical set T of size ≈ 2^{N H(X)}, each member having probability ≈ 2^{−N H}.
- **Source coding theorem**: you can represent typical sequences with N H + o(N) bits and have failure probability → 0. You cannot compress below N H bits with vanishing error (lossy version: cannot map into fewer than 2^{N H} bins losslessly for typical set).
- **Weighing-problem calibration**: 12 balls, 3-way balance, 24 hypotheses (12 balls × heavy/light). Information needed: log2 24 ≈ 4.58 bits. Each weighing gives at most log2 3 ≈ 1.585 bits, so ≥3 weighings. First weighing should split hypotheses as evenly as possible (4 vs 4, not 6 vs 6).

## Key Concepts
- **Essential bit content** of X: the smallest expected number of binary questions to determine x.
- **δ-typical set** T_{Nδ}: sequences with |−(1/N) log P(x) − H| < δ.
- **Asymptotic equipartition property (AEP)**: typical sequences are nearly equally likely.
- **Block compression**: encode N-tuples, not single symbols; this is why entropy, not ⌈log 1/pi⌉ rounded per symbol, is achievable.
- **Lossy vs lossless**: MacKay first motivates H via *lossy* compression that preserves typical set membership (tiny total variation error), then lossless codes in Ch 5–6.

## Key Equations
- h(x) = log2 1/P(x)
- H(X) = sum_i pi log2 1/pi
- H2(p) = p log2 1/p + (1−p) log2 1/(1−p)
- If independent: H(X,Y)=H(X)+H(Y)
- |T_{Nδ}| ≤ 2^{N(H+δ)}
- P(X^N ∉ T_{Nδ}) → 0 as N→∞ (law of large numbers on −log P(xi))
- Compression length N(H+δ) bits suffices; N(H−δ) bits fails

## Algorithms and Techniques
**Typical-set compressor (existence proof, not a practical codec)**
1. Draw N i.i.d. symbols.
2. If the sequence is typical, emit a ⌈N(H+δ)⌉-bit index into T.
3. If atypical, emit a failure flag / raw sequence (probability of this → 0).
4. Decoder has the same enumeration of T.

**Design a weighing strategy (ternary questions)**
1. Count remaining hypotheses Ω; remaining information log2 Ω.
2. Choose a weighing whose three outcome-sets have sizes as equal as possible.
3. Stop when Ω=1.

## Mental Models
- Think of compression as *naming the typical set element*, not encoding each symbol’s surprise separately.
- Think of 2^{N H} as the “effective number of outcomes”.
- Use 4-vs-4 first weighing: 6-vs-6 leaves the “balance” outcome with 0 information about which ball is odd (all equal balls are on the scale).
- First-time reader: skip the formal proofs in §4.5; trust AEP and go to Ch 5.

## Worked Example
Bent coin, P(heads)=0.1, N=100 tosses.
- H2(0.1)≈0.469 bits/toss, so typical sequences have about 47 bits of content, not 100.
- Mean number of heads = 10; typical r is near 10, not 50. log2 C(100,10) ≈ 100 H2(0.1) ≈ 47 bits: the number of typical binary strings of length 100 with ~10 ones is ~2^{47}, not 2^{100}.
- A compressor that encodes the *positions of the ~10 ones* (or arithmetic-codes the Bernoulli process) approaches 0.469 N bits. A naive 1-bit-per-toss code wastes factor ~2.

12-ball problem: 24 hypotheses, 3 weighings of a ternary balance: 3^3=27 ≥ 24, so it is information-theoretically possible; 2 weighings give only 9 < 24, impossible. The first weighing must not use 6 vs 6.

## Anti-patterns
- **Encoding each symbol with ⌈log2 1/pi⌉ bits independently**: may exceed H by almost 1 bit/symbol; use blocks or arithmetic coding.
- **Treating all 2^N binary strings as typical** for a biased source.
- **Skipping the weighing exercise**: it is the intuition pump for “information = log of hypothesis count”.
- **Claiming lossless compression below entropy for i.i.d. sources** (except on a vanishing-probability set).

## Key Takeaways
1. H(X) is the compression limit, in bits per symbol, for i.i.d. sources.
2. Typical sequences all have probability ~2^{−NH} and there are ~2^{NH} of them.
3. Additivity of h(x) for independent events selects the logarithm (not some other function of p).
4. Design questions (weighings, codes) to split remaining probability as evenly as possible.
5. Blocklength N is the friend of compression; single-symbol integer codes are not.

## Connects To
- **Ch 1**: Stirling already produced H2(r/N) as log of binomial coefficients.
- **Ch 5–6**: constructive codes (Huffman, arithmetic) that approach H.
- **Ch 10**: jointly typical sets — the channel-coding twin of this chapter.
- **Ch 28**: Occam / evidence as compression of the data (MML/MDL kinship).
