# Chapter 10: The Noisy-Channel Coding Theorem

## Core Idea
For every DMC, C = max I(X;Y) is the sharp threshold: rates R<C are achievable with block error → 0 as N→∞ (random coding + jointly typical decoding); rates above the reliability function R(pb) are impossible. The proof is typical-set packing, the channel dual of Ch 4.

## Frameworks Introduced
- **Three-part theorem**
  1. Achievability: ∀ε>0, R<C, ∃ large N, a code of rate ≥R with max block error <ε.
  2. If bit-error pb is tolerated, rates up to R(pb)=C/(1−H2(pb)) (MacKay’s form relating residual entropy) are achievable.
  3. Converse: above those rates, impossible.
- **Joint typicality**: a pair (x,y) is jointly typical if x is typical, y is typical, and (x,y) is typical under P(x,y)=P(x)P(y|x).
- **Random coding**: draw S=2^{NR} codewords i.i.d. from the capacity-achieving P(x). Typical decoder: pick the unique codeword jointly typical with y.

## Key Concepts
- **Notation MacKay insists on**: C capacity; N blocklength; x^{(s)} sth codeword; S=2^K number of codewords; K=log2 S; R=K/N.
- **Maximal vs average error**: the theorem is stated with maximal block error (worst codeword) by expurgating the worst half of a random code.
- **Jointly typical set size**: ~2^{N H(X,Y)} pairs; each y is jointly typical with ~2^{N H(X|Y)} inputs.
- **Why R<C works**: 2^{NR} codewords × 2^{N H(X|Y)} candidates per y vs 2^{N H(X)} possible typical x. Collision probability vanishes if R < I(X;Y) ≤ C.
- **Non-constructive**: existence via averaging; does not exhibit a code. Practical constructions wait until Ch 47–50.

## Key Equations
- C = max_{PX} I(X;Y)
- |T_joint| ≈ 2^{N H(X,Y)}
- Number of x jointly typical with a given typical y ≈ 2^{N H(X|Y)}
- P(two independent x,x' both jointly typical with y) ≈ 2^{−N I(X;Y)}
- Average error ≲ 2^{−N(C−R)}  (exponentially small for R<C)

## Algorithms and Techniques
**Random-coding existence argument (not an implementation)**
1. Choose PX achieving C.
2. Draw S=2^{NR} codewords i.i.d. ~ PX^N.
3. Decoder: given y, list codewords jointly typical with y; if exactly one, output it, else fail.
4. Average over codes and noise: P(fail)→0 for R<C.
5. Expurgate the worst half of codewords; rate loss 1/N bit, max error ≤ 2×average.

**Computing C**: maximize I(X;Y) (Blahut–Arimoto for larger alphabets; one-dimensional calculus for binary input).

## Mental Models
- Picture: each codeword owns a typical noise “sausage” of volume 2^{N H(Y|X)}; the output space of typical y has volume 2^{N H(Y)}; packing number 2^{N I(X;Y)}.
- First-time reader: detour at §10.4 as MacKay advises; skip proof details, keep the packing picture.
- Shannon codes are *random-looking*; algebraic minimum-distance codes (Ch 13) optimize a different objective.

## Worked Example
BSC(f=0.11), H2(0.11)≈0.5, C≈0.5. Want R=0.4, N=10_000.
- S=2^{4000} codewords.
- H(X|Y)=H2(0.11)≈0.5 so each y is jointly typical with ~2^{5000} possible x.
- Probability a wrong codeword lands in that set ~ 2^{5000}/2^{10000}=2^{−5000}, times 2^{4000} rivals → 2^{−1000} — negligible.
- At R=0.6>C the same calculation explodes: 2^{6000}×2^{−5000}=2^{1000} expected impostors.

Cable-labelling exercise (end of chapter): identifying a permutation of N wires by joining them into partitions — a Shannon-style random partition beats naive pairing; Knowlton–Graham partitions for special N.

## Anti-patterns
- **Waiting for an explicit Shannon code**: the proof will not give you one.
- **Using minimum distance as a proxy for being close to C** (Ch 13: tenuous link).
- **Forgetting expurgation** when claiming *maximal* error bounds.
- **Applying the DMC theorem to channels with memory** without extending the definition (capacity still exists but is more delicate).

## Key Takeaways
1. C is achievable and tight for DMCs.
2. Joint typicality is the decoder the proof uses; practical decoders (MAP, BP) approximate it.
3. Error decays exponentially in N below capacity.
4. Random codes are good; the problem is decoding them (which sparse-graph codes later solve).
5. Skip §10.4 proofs on a first read; do not skip the statement.

## Connects To
- **Ch 4**: typicality / AEP.
- **Ch 9**: I(X;Y) and C defined.
- **Ch 13–14**: why sphere-packing / perfect codes miss Shannon’s point; yet good linear codes exist.
- **Ch 47**: LDPC as the constructive random-like codes you can actually decode.
