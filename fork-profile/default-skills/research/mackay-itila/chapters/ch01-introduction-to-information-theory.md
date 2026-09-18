# Chapter 1: Introduction to Information Theory

## Core Idea
Perfect communication over a noisy channel is possible: for any rate R below the channel capacity C, there exist codes whose block-error probability can be driven arbitrarily close to zero. Engineering intuition that “noise forces residual error” is false; the right object is a *rate vs reliability* trade-off, not an SNR vs residual-error trade-off.

## Frameworks Introduced
- **The fundamental problem of communication** (Shannon): reproduce at one point a message selected at another point, exactly or approximately, over an imperfect medium.
  - When to use: any storage or transmission problem (modems, deep-space, DNA replication, disk drives).
  - How: separate *source coding* (remove redundancy) from *channel coding* (add designed redundancy).
  - Why it works: typical-set geometry makes most noise patterns distinguishable if you do not pack codewords too densely.
- **Rate–reliability picture**: plot block error probability pB vs rate R = K/N for families of codes (repetition, Hamming, BCH) against the Shannon limit R = C.
  - When to use: evaluating a code, not just its minimum distance.
  - How: fix the channel (e.g. BSC(f)), vary blocklength N, read pB.

## Key Concepts
- **Binary symmetric channel (BSC)**: each transmitted bit is flipped independently with probability f.
- **Block code**: K information bits encoded into N transmitted bits; rate R = K/N.
- **Repetition code RN**: send each bit N times; decode by majority vote. Rate → 0 as N grows.
- **Hamming (7,4) code**: 4 information bits, 3 parity bits, corrects any single error.
- **Decoder**: maps received y ∈ {0,1}^N to a guessed codeword (or to “error detected”).
- **Channel capacity C**: the highest rate at which arbitrarily reliable communication is possible. For BSC(f), C = 1 − H2(f).
- **Binary entropy H2(f)**: H2(f) = f log2(1/f) + (1−f) log2(1/(1−f)).
- **Shannon limit**: the vertical line R = C on the rate–pB plot; no code can sit to the right of it with pB → 0.

## Key Equations
- P(r | f, N) = C(N,r) f^r (1−f)^{N−r}  -- binomial (number of flips)
- E[r] = N f,  var[r] = N f(1−f)
- ln n! ≃ n ln n − n + (1/2) ln(2πn)  -- Stirling
- log2 C(N, r) ≃ N H2(r/N)
- C_BSC(f) = 1 − H2(f)
- R = K/N

## Algorithms and Techniques
**Majority-vote decoding of RN**
1. Receive N copies of a bit.
2. Output 1 if more than N/2 ones, else 0.
3. For BSC(f), P(error) = sum_{r>(N/2)} C(N,r) f^r (1−f)^{N−r} → 0 only as N→∞, and R→0.

**Hamming (7,4) syndrome decoding**
1. Compute 3 parity-check bits of the received 7-tuple.
2. The 3-bit syndrome indexes the flipped bit (000 = no error).
3. Flip that bit. Fails on 2-or-more errors.

## Mental Models
- Think of a code as a sparse subset of {0,1}^N: decoding succeeds if noise does not carry you into another codeword’s Voronoi cell.
- Think of capacity as a *budget of distinguishable typical noise balls*, not as “signal stronger than noise”.
- Use repetition only as a teaching code; it burns rate to buy reliability.

## Worked Example
BSC with f = 0.1. Capacity C = 1 − H2(0.1) ≈ 0.53 bits per use.

- R3 (rate 1/3 ≈ 0.33 < C): majority vote fails only if 2 or 3 bits flip. P(block error per info bit) = 3f^2(1−f)+f^3 ≈ 0.028. Better than uncoded f=0.1, but far from capacity and rate is low.
- Hamming (7,4) (rate 4/7 ≈ 0.57 > C for f=0.1): it *cannot* achieve vanishing error on this channel no matter how you decode, because it sits above capacity. For smaller f (e.g. f=0.01, C≈0.92) the same code is below capacity and is useful.
- MacKay’s plots of BCH(15,7), BCH(31,16), BCH(511,76) show algebraic codes improving pB at modest rates but remaining far from the Shannon limit — the gap that Parts II and VI close with sparse-graph codes.

## Anti-patterns
- **“Add SNR until BER is small enough”**: ignores that coding can give reliability at fixed SNR if R < C.
- **Equating “redundancy” with “repetition”**: designed parity (Hamming, LDPC) buys far more reliability per wasted bit.
- **Optimizing minimum distance alone**: the Shannon picture is typical-set packing, not worst-case distance.
- **Reading capacity as a code you can use**: C is an existence bound; practical codes (Ch 47–50) approximate it.

## Key Takeaways
1. Noise does not forbid perfect communication; rates above C do.
2. Always compute C for the channel before choosing a code family.
3. Plot codes in the (R, pB) plane; distance tables are secondary.
4. Stirling + binomial → binary entropy: this is the calculator for typical-set sizes.
5. The rest of the book is how to *construct* codes and *infer* messages that approach these bounds.

## Connects To
- **Ch 4**: source coding / entropy as compression limit (the dual of capacity).
- **Ch 9–10**: formal noisy-channel coding theorem, jointly typical sets.
- **Ch 11**: Hamming, convolutional, and real (Gaussian) channels.
- **Ch 47–50**: practical codes that approach C (LDPC, turbo, RA, fountain).
